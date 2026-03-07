"""
Telegram Discovery Connector - Channel intelligence via Telethon.

Scans public Telegram channels for leak indicators: invite links, file
references, external URLs (Google Drive, Mega, etc.) and piracy keywords.

Config keys:
    api_id        Telegram API ID (required)
    api_hash      Telegram API hash (required)
    session_name  Telethon session name (default: "aimon_session")
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import structlog

from aimon.connectors.base import BaseConnector

logger = structlog.get_logger(__name__)

# Regex patterns for content extraction
_INVITE_PATTERN = re.compile(r"(?:https?://)?t\.me/(?:\+|joinchat/)([A-Za-z0-9_-]+)")
_FILE_EXT_PATTERN = re.compile(r"\S+\.(?:zip|rar|mp4|mkv|avi|mp3|wav|pdf|exe|iso)\b", re.I)
_EXTERNAL_URL_PATTERN = re.compile(r"https?://\S+")
_RISK_KEYWORDS = [
    "free download",
    "crack",
    "piracy",
    "leaked",
    "full course",
    "drive.google",
    "mega.nz",
    "magnet:",
    "torrent",
]


class ConfigurationError(Exception):
    """Raised when required configuration keys are missing."""


class TelegramDiscoveryConnector(BaseConnector):
    """
    Telegram intelligence connector using Telethon.

    Scans public channels to extract signals: invite links, file names,
    external URLs, and piracy risk indicators.

    Raises:
        ConfigurationError: If ``api_id`` or ``api_hash`` are not set in config.
    """

    def __init__(self, name: str = "telegram_discovery", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        self._client: Any = None

    async def initialize(self) -> None:
        """Initialize Telethon client.

        Raises:
            ConfigurationError: If API credentials are not configured.
        """
        api_id = self.config.get("api_id")
        api_hash = self.config.get("api_hash")

        if not api_id or not api_hash:
            raise ConfigurationError(
                "TelegramDiscoveryConnector requires 'api_id' and 'api_hash' in config. "
                "Obtain them from https://my.telegram.org/apps and add them to your AIMON config."
            )

        try:
            from telethon import TelegramClient

            session_name = self.config.get("session_name", "aimon_session")
            self._client = TelegramClient(session_name, int(api_id), api_hash)
            await self._client.start()
            await super().initialize()
            await logger.ainfo("telegram_discovery_connector_initialized")
        except ImportError as exc:
            raise ConfigurationError(
                "telethon is not installed. Install it with: pip install 'aimon[telegram]'"
            ) from exc
        except Exception as exc:
            await logger.aerror("telegram_connector_init_failed", error=str(exc))
            raise

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for public Telegram channels matching *query*.

        Args:
            query: Search term (channel name or keyword).

        Returns:
            List of channel scan result dicts.
        """
        if not self._client:
            return []

        results: List[Dict[str, Any]] = []
        try:
            from telethon.tl.functions.contacts import SearchRequest

            found = await self._client(SearchRequest(q=query, limit=20))
            for chat in getattr(found, "chats", []):
                channel_url = f"https://t.me/{getattr(chat, 'username', '')}"
                scan = await self.scan_channel(channel_url)
                results.append(scan)
        except Exception as exc:
            await logger.aerror("telegram_search_failed", query=query, error=str(exc))

        return results

    async def fetch(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch and scan a single Telegram channel URL.

        Args:
            url: Public channel URL (e.g., ``https://t.me/channelname``).

        Returns:
            Channel scan result dict.
        """
        return await self.scan_channel(url)

    async def scan_channel(self, channel_url: str) -> Dict[str, Any]:
        """
        Scan a Telegram channel for leak indicators.

        Args:
            channel_url: Full channel URL, e.g. ``https://t.me/channelname``.

        Returns:
            Dict with channel metadata and extracted signals.
        """
        invite_links: List[str] = []
        file_references: List[str] = []
        external_urls: List[str] = []
        risk_indicators: List[str] = []
        channel_title = ""
        message_count = 0

        try:
            entity = await self._client.get_entity(channel_url)
            channel_title = getattr(entity, "title", channel_url)

            async for message in self._client.iter_messages(entity, limit=200):
                text = getattr(message, "message", "") or ""
                message_count += 1

                # Invite links
                for match in _INVITE_PATTERN.finditer(text):
                    link = f"https://t.me/+{match.group(1)}"
                    if link not in invite_links:
                        invite_links.append(link)

                # File references
                for match in _FILE_EXT_PATTERN.finditer(text):
                    ref = match.group(0)
                    if ref not in file_references:
                        file_references.append(ref)

                # External URLs
                for match in _EXTERNAL_URL_PATTERN.finditer(text):
                    ext_url = match.group(0)
                    if ext_url not in external_urls:
                        external_urls.append(ext_url)

                # Risk indicators
                lower_text = text.lower()
                for keyword in _RISK_KEYWORDS:
                    if keyword in lower_text and keyword not in risk_indicators:
                        risk_indicators.append(keyword)

        except Exception as exc:
            await logger.aerror(
                "telegram_channel_scan_failed", channel=channel_url, error=str(exc)
            )

        return {
            "source_type": "telegram",
            "channel_url": channel_url,
            "channel_title": channel_title,
            "message_count": message_count,
            "invite_links": invite_links,
            "file_references": file_references,
            "external_urls": external_urls,
            "risk_indicators": risk_indicators,
            "platform": "telegram",
        }

    async def shutdown(self) -> None:
        """Disconnect Telethon client."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
        await super().shutdown()
