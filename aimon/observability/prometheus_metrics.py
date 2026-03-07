"""
Prometheus Metrics Exporter - HTTP metrics endpoint for AIMON framework.

Exposes counters, histograms, and gauges via prometheus_client and starts
an HTTP server on a configurable port (default: 9090).
"""

from __future__ import annotations

from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class PrometheusMetricsExporter:
    """
    Subscribes to framework EventBus events and exposes Prometheus metrics.

    Metrics exposed:
        aimon_sources_discovered_total        Counter
        aimon_pages_crawled_total             Counter
        aimon_leaks_detected_total            Counter
        aimon_risk_score                      Histogram (0.1 buckets)
        aimon_network_nodes_total             Gauge
        aimon_verification_duration_seconds   Histogram

    Args:
        event_bus: The framework :class:`EventBus` instance.
        port: HTTP port to serve metrics on (default: ``9090``).
    """

    def __init__(self, event_bus: Any, port: int = 9090) -> None:
        self._event_bus = event_bus
        self._port = port
        self._server: Optional[Any] = None
        self._metrics: dict = {}

    async def start(self) -> None:
        """Initialise metrics and start the HTTP exposition server."""
        try:
            import prometheus_client as prom  # type: ignore

            buckets = [i / 10 for i in range(1, 11)]

            self._metrics = {
                "sources_discovered_total": prom.Counter(
                    "aimon_sources_discovered_total",
                    "Total number of sources discovered",
                ),
                "pages_crawled_total": prom.Counter(
                    "aimon_pages_crawled_total",
                    "Total number of pages crawled",
                ),
                "leaks_detected_total": prom.Counter(
                    "aimon_leaks_detected_total",
                    "Total number of leaks detected",
                ),
                "risk_score": prom.Histogram(
                    "aimon_risk_score",
                    "Distribution of risk scores",
                    buckets=buckets,
                ),
                "network_nodes_total": prom.Gauge(
                    "aimon_network_nodes_total",
                    "Current total nodes in leak network",
                ),
                "verification_duration_seconds": prom.Histogram(
                    "aimon_verification_duration_seconds",
                    "Time spent verifying content",
                    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
                ),
            }

            # Subscribe to events
            await self._event_bus.subscribe(
                "source_discovered", self._on_source_discovered
            )
            await self._event_bus.subscribe("page_crawled", self._on_page_crawled)
            await self._event_bus.subscribe("threat_detected", self._on_threat_detected)
            await self._event_bus.subscribe(
                "leak_network_detected", self._on_network_detected
            )

            # Start HTTP server
            prom.start_http_server(self._port)
            await logger.ainfo("prometheus_metrics_started", port=self._port)

        except ImportError as exc:
            raise ImportError(
                "prometheus-client must be installed.  "
                "Install with: pip install 'aimon[monitoring]'"
            ) from exc

    async def stop(self) -> None:
        """Unsubscribe event handlers."""
        try:
            await self._event_bus.unsubscribe("source_discovered", self._on_source_discovered)
            await self._event_bus.unsubscribe("page_crawled", self._on_page_crawled)
            await self._event_bus.unsubscribe("threat_detected", self._on_threat_detected)
            await self._event_bus.unsubscribe(
                "leak_network_detected", self._on_network_detected
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # event handlers
    # ------------------------------------------------------------------

    async def _on_source_discovered(self, **data: Any) -> None:
        counter = self._metrics.get("sources_discovered_total")
        if counter:
            counter.inc()

    async def _on_page_crawled(self, **data: Any) -> None:
        counter = self._metrics.get("pages_crawled_total")
        if counter:
            counter.inc()

    async def _on_threat_detected(self, **data: Any) -> None:
        counter = self._metrics.get("leaks_detected_total")
        if counter:
            counter.inc()

        histogram = self._metrics.get("risk_score")
        if histogram:
            risk_score = float(data.get("risk_score", 0.0))
            histogram.observe(risk_score)

    async def _on_network_detected(self, **data: Any) -> None:
        gauge = self._metrics.get("network_nodes_total")
        if gauge:
            nodes = int(data.get("network_nodes", 0))
            gauge.set(nodes)
