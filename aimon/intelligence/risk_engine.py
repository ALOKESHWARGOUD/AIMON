"""
Risk Engine - Score and classify detected leak signals.

Provides:
* ``RiskEngine`` — Pure calculation class (no EventBus dependency).
* ``RiskEngineModule`` — BaseModule that aggregates signals and emits
  ``threat_detected`` for consumption by AlertsModule.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import structlog

from aimon.core.base_module import BaseModule

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SIGNAL_WEIGHTS: Dict[str, float] = {
    "invite_link": 0.7,
    "torrent_listing": 0.8,
    "drive_mirror": 0.9,
    "keyword_match": 0.4,
    "filename_match": 0.6,
    "video_fingerprint": 1.0,
    "audio_fingerprint": 1.0,
    "reddit_post": 0.3,
    "telegram_channel": 0.65,
}

RISK_LEVELS: Dict[str, Tuple[float, float]] = {
    "low": (0.0, 0.5),
    "suspicious": (0.5, 0.8),
    "confirmed": (0.8, 1.01),  # upper bound inclusive via > check
}


# ---------------------------------------------------------------------------
# Pure calculation engine
# ---------------------------------------------------------------------------


class RiskEngine:
    """
    Stateless risk scoring engine.

    Calculates a composite risk score from a list of signal dicts, classifies
    it, and builds a human-readable risk report.
    """

    def calculate_score(self, signals: List[Dict[str, Any]]) -> float:
        """
        Calculate a composite risk score from *signals*.

        The score is the probability-based combination of individual signal
        weights:

            score = 1 − ∏(1 − w_i)

        which ensures no single signal can exceed 1.0.

        Args:
            signals: List of signal dicts.  Each must have a ``signal_type``
                     key matching one of ``SIGNAL_WEIGHTS``.

        Returns:
            Float in [0.0, 1.0].
        """
        if not signals:
            return 0.0

        complement = 1.0
        for sig in signals:
            stype = sig.get("signal_type", sig.get("type", "keyword_match"))
            weight = SIGNAL_WEIGHTS.get(stype, 0.3)
            confidence = float(sig.get("confidence", 1.0))
            effective = weight * confidence
            complement *= 1.0 - effective

        return round(min(1.0, 1.0 - complement), 4)

    def classify(self, score: float) -> str:
        """
        Classify a numeric score into a risk level label.

        Args:
            score: Float in [0.0, 1.0].

        Returns:
            One of ``"low"``, ``"suspicious"``, ``"confirmed"``.
        """
        for level, (low, high) in RISK_LEVELS.items():
            if low <= score < high:
                return level
        return "confirmed" if score >= 0.8 else "low"

    def build_risk_report(
        self, signals: List[Dict[str, Any]], brand: str, url: str
    ) -> Dict[str, Any]:
        """
        Build a comprehensive risk report dict.

        Args:
            signals: List of signal dicts.
            brand: Brand name being monitored.
            url: URL where the leak was detected.

        Returns:
            Report dict with score, level, signals summary, etc.
        """
        score = self.calculate_score(signals)
        level = self.classify(score)
        signal_types = [s.get("signal_type", "unknown") for s in signals]

        return {
            "brand": brand,
            "url": url,
            "risk_score": score,
            "risk_level": level,
            "signals": signal_types,
            "signal_count": len(signals),
            "signal_weights": {
                st: SIGNAL_WEIGHTS.get(st, 0.3) for st in set(signal_types)
            },
        }


# ---------------------------------------------------------------------------
# EventBus-integrated module
# ---------------------------------------------------------------------------


class RiskEngineModule(BaseModule):
    """
    Aggregates network and verification signals and emits ``threat_detected``.

    Subscribes to:
        * ``leak_network_detected`` — graph context from NetworkMapperModule
        * ``content_verified``      — verification results from VerificationModule

    Emits:
        * ``threat_detected`` — feeds the existing AlertsModule pipeline
    """

    def __init__(self, name: str = "risk_engine", event_bus: Optional[Any] = None) -> None:
        super().__init__(name, event_bus)
        self._engine = RiskEngine()
        # url → list of accumulated signals
        self._pending: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"signals": [], "brand": "", "platform": "unknown", "network": {}}
        )
        self._lock: asyncio.Lock = asyncio.Lock()

    async def _initialize_impl(self) -> None:
        """Initialize risk engine module."""
        self._pending = defaultdict(
            lambda: {"signals": [], "brand": "", "platform": "unknown", "network": {}}
        )
        self._lock = asyncio.Lock()
        await logger.ainfo("risk_engine_module_initialized")

    async def _subscribe_to_events(self) -> None:
        """Subscribe to upstream signal events."""
        await self.subscribe_event("leak_network_detected", self._on_network_detected)
        await self.subscribe_event("content_verified", self._on_content_verified)

    # ------------------------------------------------------------------
    # event handlers
    # ------------------------------------------------------------------

    async def _on_network_detected(self, **data: Any) -> None:
        """Handle ``leak_network_detected`` event."""
        url = data.get("url", "")
        brand = data.get("brand", "")
        platform = data.get("platform", "unknown")
        node_types: Dict[str, int] = data.get("node_types", {})
        graph_data = data.get("graph_data", {})

        signals: List[Dict[str, Any]] = []
        # Derive signals from node types present in the network
        if node_types.get("TelegramChannel", 0) > 0:
            signals.append({"signal_type": "telegram_channel", "confidence": 0.9})
        if node_types.get("InviteLink", 0) > 0:
            signals.append({"signal_type": "invite_link", "confidence": 0.85})
        if node_types.get("DriveLink", 0) > 0:
            signals.append({"signal_type": "drive_mirror", "confidence": 0.9})
        if node_types.get("TorrentLink", 0) > 0:
            signals.append({"signal_type": "torrent_listing", "confidence": 0.95})
        if node_types.get("RedditPost", 0) > 0:
            signals.append({"signal_type": "reddit_post", "confidence": 0.7})

        async with self._lock:
            bucket = self._pending[url]
            bucket["signals"].extend(signals)
            bucket["brand"] = bucket["brand"] or brand
            bucket["platform"] = bucket["platform"] or platform
            bucket["network"] = graph_data
            await self._maybe_emit(url)

    async def _on_content_verified(self, **data: Any) -> None:
        """Handle ``content_verified`` event."""
        url = data.get("url", "")
        brand = data.get("brand", "")
        method = data.get("verification_method", "filename_similarity")
        similarity = float(data.get("similarity_score", 0.0))
        verified = bool(data.get("verified", False))

        if not verified:
            return

        signal = {"signal_type": method, "confidence": similarity}
        async with self._lock:
            bucket = self._pending[url]
            bucket["signals"].append(signal)
            bucket["brand"] = bucket["brand"] or brand
            await self._maybe_emit(url)

    async def _maybe_emit(self, url: str) -> None:
        """Emit threat_detected for *url* if we have enough signals."""
        bucket = self._pending.get(url)
        if not bucket or not bucket["signals"]:
            return

        report = self._engine.build_risk_report(
            bucket["signals"], bucket["brand"], url
        )

        await self.emit_event(
            "threat_detected",
            brand=report["brand"],
            url=url,
            platform=bucket["platform"],
            risk_score=report["risk_score"],
            risk_level=report["risk_level"],
            signals=report["signals"],
            detected_network=bucket["network"],
        )

        await logger.ainfo(
            "risk_threat_emitted",
            url=url,
            score=report["risk_score"],
            level=report["risk_level"],
        )
