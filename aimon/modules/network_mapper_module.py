"""
Network Mapper Module - Builds piracy network graph from leak signals.

Subscribes to: leak_signal_detected
Emits: leak_network_detected
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from aimon.core.base_module import BaseModule
from aimon.intelligence.leak_network_mapper import LeakNetworkMapper
from aimon.intelligence.relationship_builder import RelationshipBuilder

logger = structlog.get_logger(__name__)


class NetworkMapperModule(BaseModule):
    """
    Persists leak signal data to a graph and emits network snapshots.

    Uses ``RelationshipBuilder`` to derive graph nodes/edges from a
    ``leak_signal_detected`` payload, then persists them via
    ``LeakNetworkMapper``.
    """

    def __init__(
        self, name: str = "network_mapper", event_bus: Optional[Any] = None
    ) -> None:
        super().__init__(name, event_bus)
        self._mapper: Optional[LeakNetworkMapper] = None
        self._builder: Optional[RelationshipBuilder] = None

    async def _initialize_impl(self) -> None:
        """Initialize graph mapper and relationship builder."""
        mapper_config = {
            "neo4j_uri": self._config.get("neo4j_uri", "bolt://localhost:7687"),
            "neo4j_user": self._config.get("neo4j_user", ""),
            "neo4j_password": self._config.get("neo4j_password", ""),
        }

        self._mapper = LeakNetworkMapper(mapper_config)
        await self._mapper.initialize()
        self._builder = RelationshipBuilder(self._mapper)

        await logger.ainfo("network_mapper_module_initialized")

    async def _subscribe_to_events(self) -> None:
        """Subscribe to leak signal events."""
        await self.subscribe_event("leak_signal_detected", self._on_leak_signal)

    async def _shutdown_impl(self) -> None:
        """Shutdown graph connection."""
        if self._mapper:
            await self._mapper.shutdown()
        await logger.ainfo("network_mapper_module_shutdown")

    # ------------------------------------------------------------------
    # event handler
    # ------------------------------------------------------------------

    async def _on_leak_signal(self, **data: Any) -> None:
        """Process leak signal and update graph."""
        if not self._mapper or not self._builder:
            return

        brand = data.get("brand", "")
        url = data.get("url", "")
        platform = data.get("platform", "unknown")

        try:
            relationships = await self._builder.process_signal(data)
            stats = await self._mapper.get_network_stats()
            graph_snapshot = await self._mapper.get_network(brand)

            # Build node_types summary
            node_types: Dict[str, int] = stats.get("node_types", {})

            await self.emit_event(
                "leak_network_detected",
                brand=brand,
                url=url,
                platform=platform,
                network_nodes=stats.get("nodes", 0),
                network_edges=stats.get("edges", 0),
                node_types=node_types,
                graph_data=graph_snapshot,
            )

            await logger.ainfo(
                "network_updated",
                brand=brand,
                nodes=stats.get("nodes", 0),
                edges=stats.get("edges", 0),
                relationships=len(relationships),
            )

        except Exception as exc:
            await logger.aerror("network_mapper_failed", brand=brand, url=url, error=str(exc))
