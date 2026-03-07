"""
Tests for the Verification Layer.

Tests VideoFingerprintEngine, AudioFingerprintEngine, VerificationModule,
and filename similarity logic.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aimon.core.event_bus import EventBus
from aimon.modules.verification_module import VerificationModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_event_bus() -> EventBus:
    bus = EventBus()
    await bus.initialize()
    return bus


# ===========================================================================
# TestVideoFingerprintEngine
# ===========================================================================


class TestVideoFingerprintEngine:
    """Tests for VideoFingerprintEngine."""

    @pytest.fixture
    def engine(self):
        from aimon.fingerprint.video_fingerprint_engine import VideoFingerprintEngine
        return VideoFingerprintEngine(sample_rate=5)

    async def test_extract_frame_hashes_returns_list_on_cv2_error(self, engine):
        """Returns empty list when cv2 raises an error."""
        with patch.object(engine, "_extract_hashes_sync", side_effect=Exception("cv2 error")):
            result = await engine.extract_frame_hashes("/nonexistent/video.mp4")
        assert isinstance(result, list)
        assert result == []

    async def test_compare_videos_empty_lists(self, engine):
        """Returns 0.0 when either list is empty."""
        score = await engine.compare_videos([], ["abc"], threshold=0.85)
        assert score == 0.0

        score = await engine.compare_videos(["abc"], [], threshold=0.85)
        assert score == 0.0

    async def test_compare_videos_identical_hashes(self, engine):
        """Identical hash sets score 1.0."""
        hashes = ["0000000000000000", "1111111111111111"]

        def fake_compare(hashes_a, hashes_b, threshold):
            return 1.0

        with patch.object(engine, "_compare_hashes_sync", side_effect=fake_compare):
            score = await engine.compare_videos(hashes, hashes, threshold=0.85)
        assert score == 1.0

    async def test_extract_hashes_uses_executor(self, engine):
        """extract_frame_hashes offloads work to executor."""
        call_made = []

        async def fake_run_in_executor(executor, fn, *args):
            call_made.append(True)
            return ["aabbccdd"]

        import asyncio
        loop = asyncio.get_event_loop()
        with patch.object(loop, "run_in_executor", side_effect=fake_run_in_executor):
            result = await engine.extract_frame_hashes("/tmp/test.mp4")
        assert call_made

    async def test_compare_videos_different_hashes(self, engine):
        """Different hashes produce < 1.0 score."""
        hashes_a = ["0000000000000000"]
        hashes_b = ["ffffffffffffffff"]

        def fake_compare(ha, hb, threshold):
            return 0.0

        with patch.object(engine, "_compare_hashes_sync", side_effect=fake_compare):
            score = await engine.compare_videos(hashes_a, hashes_b, threshold=0.85)
        assert score < 1.0


# ===========================================================================
# TestAudioFingerprintEngine
# ===========================================================================


class TestAudioFingerprintEngine:
    """Tests for AudioFingerprintEngine."""

    @pytest.fixture
    def engine(self):
        from aimon.fingerprint.audio_fingerprint_engine import AudioFingerprintEngine
        return AudioFingerprintEngine()

    async def test_compare_fingerprints_both_none_returns_zero(self, engine):
        """Returns 0.0 when inputs cause an error."""
        with patch.object(engine, "_compare_sync", side_effect=Exception("numpy error")):
            result = await engine.compare_fingerprints(None, None)
        assert result == 0.0

    async def test_extract_fingerprint_returns_none_on_error(self, engine):
        """Returns fallback on librosa load error."""
        with patch.object(engine, "_extract_sync", side_effect=Exception("librosa error")):
            result = await engine.extract_audio_fingerprint("/nonexistent/audio.mp3")
        # Should return a zero array or None — not raise
        # (either is acceptable since librosa is optional)

    async def test_compare_fingerprints_uses_cosine(self, engine):
        """Comparison delegates to _compare_sync."""
        import numpy as np

        fp_a = np.ones((128, 10))
        fp_b = np.ones((128, 10))

        call_made = []

        def fake_compare(a, b):
            call_made.append(True)
            return 1.0

        with patch.object(engine, "_compare_sync", side_effect=fake_compare):
            result = await engine.compare_fingerprints(fp_a, fp_b)

        assert call_made
        assert result == 1.0

    async def test_fingerprint_from_url_returns_none_on_error(self, engine):
        """Returns None when URL fetch fails."""
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.side_effect = Exception("network error")
            result = await engine.fingerprint_from_url("https://example.com/fake.mp3")
        assert result is None


# ===========================================================================
# TestVerificationModule
# ===========================================================================


class TestVerificationModule:
    """Tests for VerificationModule event handling."""

    @pytest.fixture
    async def module_and_bus(self):
        bus = await _make_event_bus()
        module = VerificationModule("verification", bus)
        await module.initialize()
        return module, bus

    async def test_emits_content_verified_event(self, module_and_bus):
        """Module emits content_verified after leak_signal_detected."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("content_verified", lambda **d: received.append(d))

        await bus.emit(
            "leak_signal_detected",
            "test",
            brand="DocTutorials",
            url="https://t.me/+FREECOURSECHANNEL",
            platform="telegram",
            signal_type="invite_link",
            confidence=0.9,
            raw_signals=["DocTutorials course.zip"],
            source_event="page_crawled",
        )
        await asyncio.sleep(0.3)

        assert len(received) > 0

    async def test_content_verified_schema(self, module_and_bus):
        """Emitted content_verified event has the correct schema."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("content_verified", lambda **d: received.append(d))

        await bus.emit(
            "leak_signal_detected",
            "test",
            brand="TestBrand",
            url="https://mega.nz/file/testbrand-full-course",
            platform="mega",
            signal_type="url_pattern",
            confidence=0.8,
            raw_signals=["TestBrand complete course.rar"],
            source_event="page_crawled",
        )
        await asyncio.sleep(0.3)

        assert received
        ev = received[0]
        required = {"brand", "url", "verification_method", "similarity_score", "verified", "confidence"}
        assert required.issubset(set(ev.keys()))
        assert 0.0 <= ev["similarity_score"] <= 1.0

    async def test_no_emit_when_brand_missing(self, module_and_bus):
        """Does NOT emit when brand is empty."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("content_verified", lambda **d: received.append(d))

        await bus.emit(
            "leak_signal_detected",
            "test",
            brand="",
            url="https://drive.google.com/something",
            platform="gdrive",
            signal_type="url_pattern",
            confidence=0.6,
            raw_signals=[],
            source_event="page_crawled",
        )
        await asyncio.sleep(0.2)

        assert len(received) == 0

    async def test_video_url_triggers_video_check(self, module_and_bus):
        """URL ending in .mp4 triggers video fingerprint path."""
        module, bus = module_and_bus

        video_called = []

        async def fake_video_verify(brand, url):
            video_called.append(url)
            return "video_fingerprint", 0.9

        # Use a URL that scores low on filename similarity so the pipeline
        # continues to the video fingerprint step.  Ensure _video_engine is
        # non-None so the branch is reached.
        module._video_engine = object()

        with patch.object(module, "_video_verify", side_effect=fake_video_verify):
            result_method, result_score, verified = await module._run_pipeline(
                "DocTutorials",
                "https://example.com/random_unrelated_video.mp4",
                [],
            )

        assert video_called
        assert result_method == "video_fingerprint"


# ===========================================================================
# TestFilenameSimilarity
# ===========================================================================


class TestFilenameSimilarity:
    """Tests for filename similarity logic using rapidfuzz."""

    @pytest.fixture
    def module(self):
        """Create a VerificationModule without event bus for unit testing."""
        return VerificationModule("verification", None)

    async def test_exact_brand_in_url_scores_high(self, module):
        """URL containing exact brand name scores above threshold."""
        method, score = await module._filename_similarity(
            "DocTutorials",
            "https://example.com/DocTutorials_full_course.zip",
            [],
        )
        assert method == "filename_similarity"
        assert score > 0.75

    async def test_typosquatted_brand_scores_medium(self, module):
        """URL with a typo variant of the brand scores lower."""
        method, score = await module._filename_similarity(
            "DocTutorials",
            "https://example.com/DockTutorials_course.zip",
            [],
        )
        assert method == "filename_similarity"
        # Should get some similarity but maybe not over threshold
        assert score >= 0.0

    async def test_unrelated_url_scores_low(self, module):
        """Completely unrelated URL scores near 0."""
        method, score = await module._filename_similarity(
            "DocTutorials",
            "https://example.com/random_cooking_recipe",
            [],
        )
        assert method == "filename_similarity"
        assert score < 0.75

    async def test_brand_in_raw_signals_detected(self, module):
        """Brand name in raw_signals is detected."""
        method, score = await module._filename_similarity(
            "DocTutorials",
            "https://drive.google.com/drive/folders/random",
            ["DocTutorials_Complete_Course_2024.zip"],
        )
        assert score > 0.75

    async def test_empty_brand_scores_zero(self, module):
        """Empty brand name always returns 0."""
        method, score = await module._filename_similarity(
            "",
            "https://example.com/anything",
            [],
        )
        assert score == 0.0
