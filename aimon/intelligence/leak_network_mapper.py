"""
Leak Network Mapper - Graph-based piracy ecosystem relationship tracking.

Uses Neo4j as the primary graph backend with an in-memory networkx.DiGraph
as a fallback when Neo4j is not available.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# Node type labels
NODE_TYPES = {
    "TelegramChannel",
    "InviteLink",
    "DriveLink",
    "TorrentLink",
    "RedditPost",
    "Brand",
}

# Edge (relationship) types
EDGE_TYPES = {
    "SHARED_BY",
    "MIRRORED_TO",
    "LINKED_FROM",
    "TARGETS",
}


class LeakNetworkMapper:
    """
    Builds and queries a graph of piracy ecosystem relationships.

    Tries to connect to Neo4j on initialization.  Falls back to an
    in-memory ``networkx.DiGraph`` automatically, with a warning logged.

    Config keys:
        neo4j_uri       Bolt URI (default: ``bolt://localhost:7687``)
        neo4j_user      Neo4j username
        neo4j_password  Neo4j password
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}
        self._driver: Any = None
        self._graph: Any = None  # networkx fallback
        self._node_index: Dict[str, Dict[str, Any]] = {}  # id → properties
        self._use_neo4j = False

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Connect to Neo4j or fall back to networkx."""
        uri = self._config.get("neo4j_uri", "bolt://localhost:7687")
        user = self._config.get("neo4j_user", "")
        password = self._config.get("neo4j_password", "")

        if user and password:
            try:
                from neo4j import AsyncGraphDatabase  # type: ignore

                self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
                await self._driver.verify_connectivity()
                self._use_neo4j = True
                await logger.ainfo("neo4j_connected", uri=uri)
                return
            except ImportError:
                await logger.awarning("neo4j_driver_not_installed_falling_back")
            except Exception as exc:
                await logger.awarning("neo4j_unavailable_falling_back", error=str(exc))

        # Fallback: networkx
        try:
            import networkx as nx

            self._graph = nx.DiGraph()
            await logger.awarning(
                "leak_network_mapper_using_memory_fallback",
                reason="Neo4j not available; using networkx DiGraph",
            )
        except ImportError as exc:
            raise RuntimeError(
                "Neither neo4j nor networkx is installed.  "
                "Install one of them: pip install networkx  OR  pip install neo4j"
            ) from exc

    async def shutdown(self) -> None:
        """Close Neo4j connection if open."""
        if self._driver:
            try:
                await self._driver.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # graph operations (all async)
    # ------------------------------------------------------------------

    async def add_node(self, node_type: str, properties: Dict[str, Any]) -> str:
        """
        Add a node to the graph.

        Args:
            node_type: One of the recognised node type labels.
            properties: Node property dictionary.

        Returns:
            Stable node ID string.
        """
        node_id = _node_id(node_type, properties)
        props = {"_id": node_id, "_type": node_type, **properties}

        if self._use_neo4j and self._driver:
            await self._neo4j_merge_node(node_type, node_id, props)
        else:
            if not self._graph.has_node(node_id):
                self._graph.add_node(node_id, **props)
            else:
                self._graph.nodes[node_id].update(props)

        self._node_index[node_id] = props
        return node_id

    async def add_relationship(
        self, from_node_id: str, to_node_id: str, rel_type: str
    ) -> None:
        """
        Add a directed edge between two nodes.

        Args:
            from_node_id: Source node ID.
            to_node_id: Target node ID.
            rel_type: Relationship type string.
        """
        if self._use_neo4j and self._driver:
            await self._neo4j_merge_rel(from_node_id, to_node_id, rel_type)
        else:
            if not self._graph.has_edge(from_node_id, to_node_id):
                self._graph.add_edge(from_node_id, to_node_id, rel_type=rel_type)

    async def get_network(self, brand: str) -> Dict[str, Any]:
        """
        Return a serialisable snapshot of the graph for *brand*.

        Args:
            brand: Brand name to filter by.

        Returns:
            Dict with ``nodes`` and ``edges`` lists.
        """
        if self._use_neo4j and self._driver:
            return await self._neo4j_get_network(brand)

        # networkx path
        nodes = []
        edges = []
        brand_nodes = {
            nid
            for nid, data in self._graph.nodes(data=True)
            if brand.lower() in str(data).lower()
        }

        # BFS to collect connected nodes within depth 3
        visited: set = set()
        frontier = set(brand_nodes)
        for _ in range(3):
            next_frontier: set = set()
            for nid in frontier:
                if nid in visited:
                    continue
                visited.add(nid)
                nodes.append(dict(self._graph.nodes[nid]))
                for successor in self._graph.successors(nid):
                    edge_data = self._graph[nid][successor]
                    edges.append(
                        {
                            "from": nid,
                            "to": successor,
                            "type": edge_data.get("rel_type", "RELATED"),
                        }
                    )
                    next_frontier.add(successor)
                for predecessor in self._graph.predecessors(nid):
                    edge_data = self._graph[predecessor][nid]
                    edges.append(
                        {
                            "from": predecessor,
                            "to": nid,
                            "type": edge_data.get("rel_type", "RELATED"),
                        }
                    )
                    next_frontier.add(predecessor)
            frontier = next_frontier - visited

        return {"nodes": nodes, "edges": edges}

    async def find_connected_nodes(
        self, node_id: str, depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Return all nodes reachable from *node_id* within *depth* hops.

        Args:
            node_id: Starting node ID.
            depth: Maximum traversal depth.

        Returns:
            List of node property dicts.
        """
        if self._use_neo4j and self._driver:
            return await self._neo4j_connected(node_id, depth)

        import networkx as nx

        try:
            subgraph = nx.ego_graph(self._graph, node_id, radius=depth, undirected=True)
            return [dict(data) for _, data in subgraph.nodes(data=True)]
        except Exception:
            return []

    async def get_network_stats(self) -> Dict[str, Any]:
        """
        Return summary statistics for the entire graph.

        Returns:
            Dict with ``nodes``, ``edges``, and ``node_types`` counts.
        """
        if self._use_neo4j and self._driver:
            return await self._neo4j_stats()

        node_types: Dict[str, int] = {}
        for _, data in self._graph.nodes(data=True):
            nt = data.get("_type", "unknown")
            node_types[nt] = node_types.get(nt, 0) + 1

        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
            "node_types": node_types,
        }

    # ------------------------------------------------------------------
    # Neo4j helpers
    # ------------------------------------------------------------------

    async def _neo4j_merge_node(
        self, node_type: str, node_id: str, props: Dict[str, Any]
    ) -> None:
        async with self._driver.session() as session:
            await session.run(
                f"MERGE (n:{node_type} {{_id: $id}}) SET n += $props",
                id=node_id,
                props=props,
            )

    async def _neo4j_merge_rel(
        self, from_id: str, to_id: str, rel_type: str
    ) -> None:
        async with self._driver.session() as session:
            await session.run(
                f"""
                MATCH (a {{_id: $from_id}}), (b {{_id: $to_id}})
                MERGE (a)-[:{rel_type}]->(b)
                """,
                from_id=from_id,
                to_id=to_id,
            )

    async def _neo4j_get_network(self, brand: str) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (n) WHERE toLower(toString(n)) CONTAINS toLower($brand) "
                "OPTIONAL MATCH (n)-[r]-(m) "
                "RETURN n, r, m LIMIT 200",
                brand=brand,
            )
            async for record in result:
                if record["n"]:
                    nodes.append(dict(record["n"]))
                if record["r"]:
                    edges.append(
                        {
                            "from": record["r"].start_node["_id"],
                            "to": record["r"].end_node["_id"],
                            "type": type(record["r"]).__name__,
                        }
                    )
        return {"nodes": nodes, "edges": edges}

    async def _neo4j_connected(self, node_id: str, depth: int) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []
        async with self._driver.session() as session:
            result = await session.run(
                f"MATCH (n {{_id: $nid}})-[*1..{depth}]-(m) RETURN DISTINCT m",
                nid=node_id,
            )
            async for record in result:
                nodes.append(dict(record["m"]))
        return nodes

    async def _neo4j_stats(self) -> Dict[str, Any]:
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt"
            )
            node_types = {}
            async for record in result:
                node_types[record["label"]] = record["cnt"]

            edge_result = await session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
            edge_count = 0
            async for record in edge_result:
                edge_count = record["cnt"]

        total_nodes = sum(node_types.values())
        return {
            "nodes": total_nodes,
            "edges": edge_count,
            "node_types": node_types,
        }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _node_id(node_type: str, properties: Dict[str, Any]) -> str:
    """Generate a stable ID for a node from its type and primary property."""
    primary = (
        properties.get("url")
        or properties.get("name")
        or properties.get("magnet")
        or str(sorted(properties.items()))
    )
    return f"{node_type}:{uuid.uuid5(uuid.NAMESPACE_URL, str(primary))}"
