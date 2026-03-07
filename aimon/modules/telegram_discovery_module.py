"""
Telegram Discovery Module - Scans Telegram channels for leak indicators.

Subscribes to: source_discovered (filters for source_type == "telegram")
Emits: telegram_signal_detected
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from aimon.core.base_module import BaseModule

logger = structlog.get_logger(__name__)


class TelegramDiscoveryModule(BaseModule):
    """
    Scans Telegram channels found via the discovery pipeline.

    Filters ``source_discovered`` events for Telegram sources and uses
    ``TelegramDiscoveryConnector`` to perform deep channel intelligence
    scanning.  Emits ``telegram_signal_detected`` with the full payload.
    """

    def __init__(
        self,
        name: str = "telegram_discovery",
        event_bus: Optional[Any] = None,
    ) -> None:
        super().__init__(name, event_bus)
        self._connector: Optional[Any] = None

    async def _initialize_impl(self) -> None:
        """Initialize the connector from config."""
        connector_config = {
            "api_id": self._config.get("telegram.api_id"),
            "api_hash": self._config.get("telegram.api_hash"),
            "session_name": self._config.get("telegram.session_name", "aimon_session"),
        }

        # Only initialise connector when credentials are present
        if connector_config["api_id"] and connector_config["api_hash"]:
            try:
                from aimon.connectors.telegram_discovery_connector import (
                    TelegramDiscoveryConnector,
                )

                self._connector = TelegramDiscoveryConnector(
                    "telegram_discovery", connector_config
                )
                await self._connector.initialize()
            except Exception as exc:
                await logger.awarning(
                    "telegram_connector_init_failed",
                    error=str(exc),
                    hint="Telegram scanning will be disabled.",
                )
                self._connector = None
        else:
            await logger.awarning(
                "telegram_credentials_missing",
                hint="Set telegram.api_id / telegram.api_hash in config to enable Telegram scanning.",
            )

        await logger.ainfo("telegram_discovery_module_initialized")

    async def _subscribe_to_events(self) -> None:
        """Subscribe to source_discovered events."""
        await self.subscribe_event("source_discovered", self._on_source_discovered)

    async def _shutdown_impl(self) -> None:
        """Shutdown connector."""
        if self._connector:
            try:
                await self._connector.shutdown()
            except Exception:
                pass
        await logger.ainfo("telegram_discovery_module_shutdown")

    # ------------------------------------------------------------------
    # event handlers
    # ------------------------------------------------------------------

    async def _on_source_discovered(self, **data: Any) -> None:
        """Handle source_discovered event, process Telegram sources only."""
        source: Dict[str, Any] = data.get("source", {})
        source_type = source.get("source_type", source.get("platform", ""))
        brand = data.get("brand", source.get("brand", ""))

        if source_type != "telegram":
            return

        channel_url: str = source.get("url", "")
        if not channel_url:
            return

        await logger.ainfo("telegram_discovery_scanning", channel=channel_url)

        if not self._connector:
            # Emit a minimal signal when connector is not available
            await self.emit_event(
                "telegram_signal_detected",
                channel_url=channel_url,
                channel_title=source.get("title", channel_url),
                invite_links=[],
                file_references=[],
                external_urls=[],
                risk_indicators=[],
                brand=brand,
            )
            return

        try:
            result = await self._connector.scan_channel(channel_url)

            await self.emit_event(
                "telegram_signal_detected",
                channel_url=result["channel_url"],
                channel_title=result["channel_title"],
                invite_links=result["invite_links"],
                file_references=result["file_references"],
                external_urls=result["external_urls"],
                risk_indicators=result["risk_indicators"],
                brand=brand,
            )

            await logger.ainfo(
                "telegram_signal_emitted",
                channel=channel_url,
                invite_links=len(result["invite_links"]),
                files=len(result["file_references"]),
            )
        except Exception as exc:
            await logger.aerror(
                "telegram_discovery_failed", channel=channel_url, error=str(exc)
            )
