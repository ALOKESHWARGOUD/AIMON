"""
Brand Monitor - High-level API for running full leak intelligence scans.

Coordinates the complete event pipeline and returns a consolidated
``LeakReport`` with risk score, network snapshot, and alert summary.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List

import structlog

if TYPE_CHECKING:
    from aimon.framework_api import AIMON

logger = structlog.get_logger(__name__)


@dataclass
class LeakReport:
    """Consolidated result of a brand leak intelligence scan."""

    brand: str
    risk_score: float
    risk_level: str
    leak_network: Dict[str, Any]
    sources_found: int
    leaks_confirmed: int
    alerts: List[Dict[str, Any]]
    scan_duration_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BrandMonitor:
    """
    High-level brand leak scanning orchestrator.

    Triggers the full discovery → crawl → signal → network → verify →
    risk → alert pipeline and returns a ``LeakReport``.

    Args:
        framework: Initialised :class:`aimon.framework_api.AIMON` instance.
    """

    def __init__(self, framework: "AIMON") -> None:
        self._fw = framework

    async def brand(self, brand_name: str) -> LeakReport:
        """
        Run a full leak intelligence scan for *brand_name*.

        The method:
        1. Triggers ``DiscoveryModule.search()`` with multiple leak queries.
        2. Waits for the event pipeline to settle (discovery → crawl →
           signal → network → verify → risk → alert).
        3. Collects results and returns a ``LeakReport``.

        Args:
            brand_name: The brand/product name to monitor.

        Returns:
            :class:`LeakReport` with aggregated scan results.
        """
        start = time.monotonic()
        await logger.ainfo("brand_monitor_starting", brand=brand_name)

        # Collect signals via EventBus subscriptions
        collected_alerts: List[Dict[str, Any]] = []
        threat_events: List[Dict[str, Any]] = []
        network_snapshots: List[Dict[str, Any]] = []
        sources_count = 0

        async def _on_alert_generated(**data: Any) -> None:
            alert = data.get("alert", data)
            collected_alerts.append(alert)

        async def _on_threat_detected(**data: Any) -> None:
            threat_events.append(data)

        async def _on_network_detected(**data: Any) -> None:
            network_snapshots.append(data.get("graph_data", {}))

        async def _on_source_discovered(**data: Any) -> None:
            nonlocal sources_count
            sources_count += 1

        # Subscribe temporary listeners
        event_bus = self._fw.runtime.event_bus
        await event_bus.subscribe("alert_generated", _on_alert_generated)
        await event_bus.subscribe("threat_detected", _on_threat_detected)
        await event_bus.subscribe("leak_network_detected", _on_network_detected)
        await event_bus.subscribe("source_discovered", _on_source_discovered)

        try:
            # Trigger discovery
            if self._fw.discovery:
                await self._fw.discovery.search(brand_name, {})

            # Allow the pipeline to process events
            await asyncio.sleep(2.0)

        finally:
            # Unsubscribe temporary listeners
            await event_bus.unsubscribe("alert_generated", _on_alert_generated)
            await event_bus.unsubscribe("threat_detected", _on_threat_detected)
            await event_bus.unsubscribe("leak_network_detected", _on_network_detected)
            await event_bus.unsubscribe("source_discovered", _on_source_discovered)

        # Aggregate risk metrics
        risk_score = 0.0
        risk_level = "low"
        if threat_events:
            risk_score = max(float(e.get("risk_score", 0.0)) for e in threat_events)
            for e in threat_events:
                if e.get("risk_level") == "confirmed":
                    risk_level = "confirmed"
                    break
                if e.get("risk_level") == "suspicious" and risk_level == "low":
                    risk_level = "suspicious"

        # Merge network snapshots
        combined_network: Dict[str, Any] = {"nodes": [], "edges": []}
        for snap in network_snapshots:
            combined_network["nodes"].extend(snap.get("nodes", []))
            combined_network["edges"].extend(snap.get("edges", []))

        # Also pull from existing alerts module
        existing_alerts = await self._fw.get_alerts_list()
        combined_alerts = collected_alerts + [
            a for a in existing_alerts if a not in collected_alerts
        ]

        duration = time.monotonic() - start

        report = LeakReport(
            brand=brand_name,
            risk_score=round(risk_score, 4),
            risk_level=risk_level,
            leak_network=combined_network,
            sources_found=sources_count,
            leaks_confirmed=len(
                [e for e in threat_events if e.get("risk_level") == "confirmed"]
            ),
            alerts=combined_alerts,
            scan_duration_seconds=round(duration, 2),
        )

        await logger.ainfo(
            "brand_monitor_completed",
            brand=brand_name,
            risk_level=report.risk_level,
            risk_score=report.risk_score,
            duration=report.scan_duration_seconds,
        )

        return report
