"""
Leak Signal Module - Detects leak signals in crawled content.

Subscribes to: page_crawled, telegram_signal_detected
Emits: leak_signal_detected
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import structlog

from aimon.core.base_module import BaseModule

logger = structlog.get_logger(__name__)

# URL patterns that indicate a leak signal
_URL_LEAK_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"drive\.google\.com", re.I), "url_pattern"),
    (re.compile(r"mega\.(?:nz|co\.nz)", re.I), "url_pattern"),
    (re.compile(r"t\.me/(?:\+|joinchat/)", re.I), "invite_link"),
    (re.compile(r"magnet:\?", re.I), "url_pattern"),
    (re.compile(r"mediafire\.com", re.I), "url_pattern"),
    (re.compile(r"dropbox\.com/s/", re.I), "url_pattern"),
    (re.compile(r"1337x\.to", re.I), "url_pattern"),
    (re.compile(r"thepiratebay\.org", re.I), "url_pattern"),
]

_FILE_EXT_PATTERN = re.compile(
    r"\b\S+\.(?:zip|rar|mp4|mkv|avi|mp3|wav|aac|pdf|torrent|exe|iso)\b", re.I
)

_LEAK_KEYWORDS = [
    "free download",
    "full course",
    "crack",
    "piracy",
    "leaked",
    "torrent",
    "magnet link",
    "google drive",
    "mega.nz",
    "telegram channel",
]


class LeakSignalModule(BaseModule):
    """
    Analyses crawled content and Telegram signals for leak indicators.

    Each detected signal receives a preliminary confidence score based on
    the number and type of indicators found.  All output is communicated
    via the EventBus — no direct module calls.
    """

    def __init__(self, name: str = "leak_signal", event_bus: Optional[Any] = None) -> None:
        super().__init__(name, event_bus)

    async def _initialize_impl(self) -> None:
        """Initialize the leak signal module."""
        await logger.ainfo("leak_signal_module_initialized")

    async def _subscribe_to_events(self) -> None:
        """Subscribe to upstream events."""
        await self.subscribe_event("page_crawled", self._on_page_crawled)
        await self.subscribe_event("telegram_signal_detected", self._on_telegram_signal)

    # ------------------------------------------------------------------
    # event handlers
    # ------------------------------------------------------------------

    async def _on_page_crawled(self, **data: Any) -> None:
        """Analyse a crawled page for leak signals."""
        page: Dict[str, Any] = data.get("page", data)
        url = page.get("url", "") or data.get("url", "")
        brand = data.get("brand", page.get("brand", ""))
        content = page.get("content", "") or ""
        title = page.get("title", "") or ""
        platform = page.get("platform", data.get("platform", "unknown"))

        # Combine all text for analysis
        combined_text = f"{title} {content} {url}"
        metadata: Dict[str, Any] = page.get("metadata", {}) or {}

        # Gather raw signals from metadata if available
        raw_signals: List[str] = []
        raw_signals.extend(metadata.get("embedded_links", []))
        raw_signals.extend(metadata.get("file_references", []))

        signals = self._analyse_text(combined_text, raw_signals)
        if not signals:
            return

        await self._emit_signal(
            brand=brand,
            url=url,
            platform=platform,
            signals=signals,
            source_event="page_crawled",
        )

    async def _on_telegram_signal(self, **data: Any) -> None:
        """Convert a telegram_signal_detected event into a leak_signal_detected."""
        channel_url = data.get("channel_url", "")
        brand = data.get("brand", "")
        invite_links: List[str] = data.get("invite_links", [])
        file_references: List[str] = data.get("file_references", [])
        external_urls: List[str] = data.get("external_urls", [])
        risk_indicators: List[str] = data.get("risk_indicators", [])

        raw_signals = invite_links + file_references + external_urls + risk_indicators
        combined_text = " ".join(raw_signals)
        signals = self._analyse_text(combined_text, raw_signals, force_invite=bool(invite_links))

        if not signals:
            # At minimum emit a keyword signal if we have any indicators
            if risk_indicators:
                signals.append(
                    {
                        "signal_type": "keyword_match",
                        "confidence": 0.5,
                        "raw": risk_indicators[:3],
                    }
                )
            else:
                return

        await self._emit_signal(
            brand=brand,
            url=channel_url,
            platform="telegram",
            signals=signals,
            source_event="telegram_signal_detected",
        )

    # ------------------------------------------------------------------
    # internal analysis
    # ------------------------------------------------------------------

    def _analyse_text(
        self,
        text: str,
        raw_signals: List[str],
        force_invite: bool = False,
    ) -> List[Dict[str, Any]]:
        """Scan text and raw_signals for leak indicators."""
        found: List[Dict[str, Any]] = []

        if force_invite:
            found.append({"signal_type": "invite_link", "confidence": 0.85, "raw": []})

        # URL pattern detection
        for pattern, signal_type in _URL_LEAK_PATTERNS:
            matched = [s for s in raw_signals if pattern.search(s)]
            if pattern.search(text):
                matched.append(text[:120])
            if matched:
                found.append(
                    {
                        "signal_type": signal_type,
                        "confidence": 0.75,
                        "raw": matched[:5],
                    }
                )

        # File extension detection
        file_matches = _FILE_EXT_PATTERN.findall(" ".join(raw_signals) + " " + text)
        if file_matches:
            found.append(
                {
                    "signal_type": "file_reference",
                    "confidence": 0.6,
                    "raw": list(set(file_matches))[:5],
                }
            )

        # Keyword matching
        lower = text.lower()
        matched_keywords = [kw for kw in _LEAK_KEYWORDS if kw in lower]
        if matched_keywords:
            found.append(
                {
                    "signal_type": "keyword_match",
                    "confidence": min(0.3 + 0.1 * len(matched_keywords), 0.7),
                    "raw": matched_keywords,
                }
            )

        return found

    async def _emit_signal(
        self,
        brand: str,
        url: str,
        platform: str,
        signals: List[Dict[str, Any]],
        source_event: str,
    ) -> None:
        """Aggregate detected signals and emit leak_signal_detected."""
        # Pick the highest-confidence signal type
        primary = max(signals, key=lambda s: s["confidence"])
        all_raw: List[str] = []
        for s in signals:
            all_raw.extend(s.get("raw", []))

        confidence = min(1.0, sum(s["confidence"] for s in signals) / len(signals) + 0.1)

        await self.emit_event(
            "leak_signal_detected",
            brand=brand,
            url=url,
            platform=platform,
            signal_type=primary["signal_type"],
            confidence=round(confidence, 3),
            raw_signals=list(set(all_raw))[:20],
            source_event=source_event,
        )

        await logger.ainfo(
            "leak_signal_emitted",
            brand=brand,
            url=url,
            signal_type=primary["signal_type"],
            confidence=confidence,
        )
