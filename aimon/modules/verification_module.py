"""
Verification Module - Multi-technique content verification.

Subscribes to: leak_signal_detected
Emits: content_verified
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

import structlog

from aimon.core.base_module import BaseModule

logger = structlog.get_logger(__name__)

# File extension patterns for routing to the appropriate engine
_VIDEO_PATTERN = re.compile(r"\.(mp4|mkv|avi|mov|wmv|flv|webm)\b", re.I)
_AUDIO_PATTERN = re.compile(r"\.(mp3|wav|aac|ogg|flac|m4a)\b", re.I)

_FILENAME_THRESHOLD = 0.75
_SIMILARITY_THRESHOLD = 0.85


class VerificationModule(BaseModule):
    """
    Coordinates three content verification techniques:

    1. **Filename similarity** — ``rapidfuzz`` comparison against brand name
       variations (fastest, runs first).
    2. **Video fingerprint** — only when the signal URL points to a video file.
    3. **Audio fingerprint** — only when the signal URL points to an audio file.

    The pipeline stops at the first high-confidence match (score > 0.75).
    """

    def __init__(
        self, name: str = "verification", event_bus: Optional[Any] = None
    ) -> None:
        super().__init__(name, event_bus)
        self._video_engine: Optional[Any] = None
        self._audio_engine: Optional[Any] = None

    async def _initialize_impl(self) -> None:
        """Initialise fingerprint engines (lazy — import errors are non-fatal)."""
        try:
            from aimon.fingerprint.video_fingerprint_engine import VideoFingerprintEngine
            self._video_engine = VideoFingerprintEngine()
        except Exception as exc:
            await logger.awarning("video_engine_unavailable", error=str(exc))

        try:
            from aimon.fingerprint.audio_fingerprint_engine import AudioFingerprintEngine
            self._audio_engine = AudioFingerprintEngine()
        except Exception as exc:
            await logger.awarning("audio_engine_unavailable", error=str(exc))

        await logger.ainfo("verification_module_initialized")

    async def _subscribe_to_events(self) -> None:
        """Subscribe to leak signal events."""
        await self.subscribe_event("leak_signal_detected", self._on_leak_signal)

    async def _shutdown_impl(self) -> None:
        """Shutdown verification module."""
        await logger.ainfo("verification_module_shutdown")

    # ------------------------------------------------------------------
    # event handler
    # ------------------------------------------------------------------

    async def _on_leak_signal(self, **data: Any) -> None:
        """Run verification pipeline against a leak signal."""
        brand: str = data.get("brand", "")
        url: str = data.get("url", "")
        raw_signals = data.get("raw_signals", [])

        if not brand or not url:
            return

        method, score, verified = await self._run_pipeline(brand, url, raw_signals)

        await self.emit_event(
            "content_verified",
            brand=brand,
            url=url,
            verification_method=method,
            similarity_score=round(score, 4),
            verified=verified,
            confidence=round(score, 4),
        )

        await logger.ainfo(
            "content_verified_emitted",
            brand=brand,
            url=url,
            method=method,
            score=score,
            verified=verified,
        )

    # ------------------------------------------------------------------
    # verification pipeline
    # ------------------------------------------------------------------

    async def _run_pipeline(
        self, brand: str, url: str, raw_signals: list
    ) -> Tuple[str, float, bool]:
        """
        Run verification steps in order.  Returns as soon as a
        high-confidence result is found.
        """
        # Step 1: filename similarity
        method, score = await self._filename_similarity(brand, url, raw_signals)
        if score >= _FILENAME_THRESHOLD:
            return method, score, True

        # Step 2: video fingerprint (only if URL points to a video)
        combined = url + " " + " ".join(raw_signals)
        if _VIDEO_PATTERN.search(combined) and self._video_engine:
            v_method, v_score = await self._video_verify(brand, url)
            if v_score >= _SIMILARITY_THRESHOLD:
                return v_method, v_score, True
            if v_score > score:
                method, score = v_method, v_score

        # Step 3: audio fingerprint
        if _AUDIO_PATTERN.search(combined) and self._audio_engine:
            a_method, a_score = await self._audio_verify(brand, url)
            if a_score >= _SIMILARITY_THRESHOLD:
                return a_method, a_score, True
            if a_score > score:
                method, score = a_method, a_score

        return method, score, score >= _FILENAME_THRESHOLD

    async def _filename_similarity(
        self, brand: str, url: str, raw_signals: list
    ) -> Tuple[str, float]:
        """Use rapidfuzz to compare file/URL names against brand."""
        try:
            from rapidfuzz import fuzz  # type: ignore
        except ImportError:
            # Fall back to basic string containment
            lower_combined = (url + " " + " ".join(raw_signals)).lower()
            score = 0.8 if brand.lower() in lower_combined else 0.0
            return "filename_similarity", score

        candidates = [url] + raw_signals
        brand_lower = brand.lower()
        best = 0.0
        for candidate in candidates:
            cand_lower = candidate.lower()
            # Partial token ratio is best for matching brand name in a longer string
            score = fuzz.partial_token_sort_ratio(brand_lower, cand_lower) / 100.0
            if score > best:
                best = score

        return "filename_similarity", best

    async def _video_verify(self, brand: str, url: str) -> Tuple[str, float]:
        """Attempt video fingerprint verification."""
        if not self._video_engine:
            return "video_fingerprint", 0.0
        try:
            hashes = await self._video_engine.fingerprint_from_url(url)
            if not hashes:
                return "video_fingerprint", 0.0
            # Without a reference fingerprint we return a mid-level score
            # indicating the file exists and was accessible
            return "video_fingerprint", 0.6
        except Exception as exc:
            await logger.awarning("video_verify_failed", url=url, error=str(exc))
            return "video_fingerprint", 0.0

    async def _audio_verify(self, brand: str, url: str) -> Tuple[str, float]:
        """Attempt audio fingerprint verification."""
        if not self._audio_engine:
            return "audio_fingerprint", 0.0
        try:
            fp = await self._audio_engine.fingerprint_from_url(url)
            if fp is None:
                return "audio_fingerprint", 0.0
            return "audio_fingerprint", 0.6
        except Exception as exc:
            await logger.awarning("audio_verify_failed", url=url, error=str(exc))
            return "audio_fingerprint", 0.0
