"""
Neo4j Storage Backend - Graph data storage via LeakNetworkMapper.

Thin wrapper implementing the ``StorageBackend`` interface over the
``LeakNetworkMapper`` graph engine.

Config keys: same as ``LeakNetworkMapper`` (neo4j_uri, neo4j_user, neo4j_password).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from aimon.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class Neo4jStorage(StorageBackend):
    """
    Neo4j-backed storage for graph/network data.

    Implements the generic ``StorageBackend`` interface by translating
    key-value operations to graph node operations via ``LeakNetworkMapper``.

    Keys are used as node IDs.  Values must be dicts with a ``_type`` key
    matching one of the recognised node type labels.
    """

    def __init__(
        self, name: str = "neo4j", config: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(name, config)
        self._mapper: Optional[Any] = None

    async def initialize(self) -> None:
        """Initialise the underlying LeakNetworkMapper."""
        from aimon.intelligence.leak_network_mapper import LeakNetworkMapper

        self._mapper = LeakNetworkMapper(self.config)
        await self._mapper.initialize()
        await super().initialize()
        await logger.ainfo("neo4j_storage_initialized")

    async def save(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Add or update a graph node with *key* as identifier."""
        if not self._mapper or not isinstance(data, dict):
            return False
        try:
            node_type = data.get("_type", "Brand")
            props = {k: v for k, v in data.items() if k != "_type"}
            props.setdefault("_id", key)
            await self._mapper.add_node(node_type, props)
            return True
        except Exception as exc:
            await logger.aerror("neo4j_save_failed", key=key, error=str(exc))
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve node properties by *key*."""
        if not self._mapper:
            return None
        try:
            return self._mapper._node_index.get(key)
        except Exception as exc:
            await logger.aerror("neo4j_get_failed", key=key, error=str(exc))
            return None

    async def delete(self, key: str) -> bool:
        """Remove a node (best-effort; not supported by all backends)."""
        if not self._mapper:
            return False
        try:
            # Remove from in-memory index
            self._mapper._node_index.pop(key, None)
            if self._mapper._graph is not None:
                if self._mapper._graph.has_node(key):
                    self._mapper._graph.remove_node(key)
            return True
        except Exception as exc:
            await logger.aerror("neo4j_delete_failed", key=key, error=str(exc))
            return False

    async def query(self, query_filter: Dict[str, Any]) -> List[Any]:
        """Return nodes matching the given filter properties."""
        if not self._mapper:
            return []
        try:
            results = []
            for node_id, props in self._mapper._node_index.items():
                match = all(props.get(k) == v for k, v in query_filter.items())
                if match:
                    results.append(props)
            return results
        except Exception as exc:
            await logger.aerror("neo4j_query_failed", error=str(exc))
            return []

    async def count(self) -> int:
        """Return total node count."""
        if not self._mapper:
            return 0
        try:
            stats = await self._mapper.get_network_stats()
            return stats.get("nodes", 0)
        except Exception as exc:
            await logger.aerror("neo4j_count_failed", error=str(exc))
            return 0

    async def shutdown(self) -> None:
        """Close Neo4j connection."""
        if self._mapper:
            await self._mapper.shutdown()
        await super().shutdown()
