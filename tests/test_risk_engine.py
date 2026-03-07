"""
Tests for the Risk Engine.

Tests RiskEngine calculation logic and RiskEngineModule event handling.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest

from aimon.core.event_bus import EventBus
from aimon.intelligence.risk_engine import RiskEngine, RiskEngineModule, SIGNAL_WEIGHTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_event_bus() -> EventBus:
    bus = EventBus()
    await bus.initialize()
    return bus


# ===========================================================================
# TestRiskEngine (pure calculation)
# ===========================================================================


class TestRiskEngine:
    """Unit tests for the stateless RiskEngine class."""

    @pytest.fixture
    def engine(self):
        return RiskEngine()

    # ------------------------------------------------------------------
    # calculate_score
    # ------------------------------------------------------------------

    async def test_empty_signals_returns_zero(self, engine):
        """No signals → score of 0.0."""
        score = engine.calculate_score([])
        assert score == 0.0

    async def test_single_signal_weight_applied(self, engine):
        """Single video_fingerprint signal → score close to weight."""
        signals = [{"signal_type": "video_fingerprint", "confidence": 1.0}]
        score = engine.calculate_score(signals)
        # score = 1 - (1 - 1.0) = 1.0
        assert score == pytest.approx(1.0, abs=0.01)

    async def test_low_weight_signals(self, engine):
        """Low-weight signals produce a score well below 0.5."""
        signals = [{"signal_type": "reddit_post", "confidence": 0.5}]
        score = engine.calculate_score(signals)
        # score = 1 - (1 - 0.3 * 0.5) = 0.15
        assert score == pytest.approx(0.15, abs=0.01)

    async def test_multiple_signals_increases_score(self, engine):
        """Multiple signals increase score via probability combination."""
        single = engine.calculate_score([{"signal_type": "keyword_match", "confidence": 1.0}])
        multiple = engine.calculate_score([
            {"signal_type": "keyword_match", "confidence": 1.0},
            {"signal_type": "invite_link", "confidence": 1.0},
        ])
        assert multiple > single

    async def test_score_capped_at_one(self, engine):
        """Score never exceeds 1.0."""
        signals = [{"signal_type": stype, "confidence": 1.0} for stype in SIGNAL_WEIGHTS]
        score = engine.calculate_score(signals)
        assert score <= 1.0

    async def test_unknown_signal_type_uses_default_weight(self, engine):
        """Unknown signal type falls back to default weight (0.3)."""
        signals = [{"signal_type": "custom_signal", "confidence": 1.0}]
        score = engine.calculate_score(signals)
        # 1 - (1 - 0.3 * 1.0) = 0.3
        assert score == pytest.approx(0.3, abs=0.01)

    # ------------------------------------------------------------------
    # classify
    # ------------------------------------------------------------------

    async def test_classify_low(self, engine):
        """Score < 0.5 → 'low'."""
        assert engine.classify(0.0) == "low"
        assert engine.classify(0.3) == "low"
        assert engine.classify(0.49) == "low"

    async def test_classify_suspicious(self, engine):
        """Score in [0.5, 0.8) → 'suspicious'."""
        assert engine.classify(0.5) == "suspicious"
        assert engine.classify(0.65) == "suspicious"
        assert engine.classify(0.79) == "suspicious"

    async def test_classify_confirmed(self, engine):
        """Score >= 0.8 → 'confirmed'."""
        assert engine.classify(0.8) == "confirmed"
        assert engine.classify(0.95) == "confirmed"
        assert engine.classify(1.0) == "confirmed"

    # ------------------------------------------------------------------
    # build_risk_report
    # ------------------------------------------------------------------

    async def test_build_risk_report_schema(self, engine):
        """build_risk_report returns dict with required keys."""
        signals = [
            {"signal_type": "invite_link", "confidence": 0.9},
            {"signal_type": "drive_mirror", "confidence": 0.8},
        ]
        report = engine.build_risk_report(signals, brand="DocTutorials", url="https://t.me/test")

        required = {"brand", "url", "risk_score", "risk_level", "signals", "signal_count", "signal_weights"}
        assert required.issubset(set(report.keys()))
        assert report["brand"] == "DocTutorials"
        assert report["url"] == "https://t.me/test"
        assert isinstance(report["signals"], list)
        assert report["signal_count"] == 2

    async def test_build_risk_report_consistent_classification(self, engine):
        """risk_level in report is consistent with risk_score."""
        signals = [{"signal_type": "video_fingerprint", "confidence": 1.0}]
        report = engine.build_risk_report(signals, "Brand", "https://url")
        assert report["risk_level"] == engine.classify(report["risk_score"])

    async def test_build_risk_report_empty_signals(self, engine):
        """Empty signals produces low-risk report."""
        report = engine.build_risk_report([], "Brand", "https://url")
        assert report["risk_score"] == 0.0
        assert report["risk_level"] == "low"


# ===========================================================================
# TestRiskEngineModule
# ===========================================================================


class TestRiskEngineModule:
    """Tests for RiskEngineModule event integration."""

    @pytest.fixture
    async def module_and_bus(self):
        bus = await _make_event_bus()
        module = RiskEngineModule("risk_engine", bus)
        await module.initialize()
        return module, bus

    async def test_network_detected_emits_threat(self, module_and_bus):
        """leak_network_detected event triggers threat_detected output."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("threat_detected", lambda **d: received.append(d))

        await bus.emit(
            "leak_network_detected",
            "test",
            brand="DocTutorials",
            url="https://t.me/piracy_channel",
            platform="telegram",
            network_nodes=5,
            network_edges=4,
            node_types={"TelegramChannel": 2, "DriveLink": 2, "Brand": 1},
            graph_data={"nodes": [], "edges": []},
        )
        await asyncio.sleep(0.3)

        assert len(received) > 0
        ev = received[0]
        assert ev["brand"] == "DocTutorials"
        assert "risk_score" in ev
        assert "risk_level" in ev

    async def test_content_verified_contributes_to_score(self, module_and_bus):
        """content_verified event raises the risk score when verified=True."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("threat_detected", lambda **d: received.append(d))

        url = "https://example.com/doctutorials_full.mp4"

        await bus.emit(
            "content_verified",
            "test",
            brand="DocTutorials",
            url=url,
            verification_method="video_fingerprint",
            similarity_score=0.95,
            verified=True,
            confidence=0.95,
        )
        await asyncio.sleep(0.3)

        assert len(received) > 0
        ev = received[0]
        assert ev["risk_score"] > 0.0

    async def test_unverified_content_does_not_emit(self, module_and_bus):
        """content_verified with verified=False does NOT trigger threat_detected."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("threat_detected", lambda **d: received.append(d))

        await bus.emit(
            "content_verified",
            "test",
            brand="DocTutorials",
            url="https://example.com/unrelated.pdf",
            verification_method="filename_similarity",
            similarity_score=0.3,
            verified=False,
            confidence=0.3,
        )
        await asyncio.sleep(0.2)

        # No threat should be emitted for unverified content
        assert len(received) == 0

    async def test_threat_detected_schema(self, module_and_bus):
        """Emitted threat_detected has the correct schema."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("threat_detected", lambda **d: received.append(d))

        await bus.emit(
            "leak_network_detected",
            "test",
            brand="TestBrand",
            url="https://mega.nz/file/test",
            platform="mega",
            network_nodes=3,
            network_edges=2,
            node_types={"DriveLink": 2, "Brand": 1},
            graph_data={},
        )
        await asyncio.sleep(0.3)

        assert received
        ev = received[0]
        required = {"brand", "url", "platform", "risk_score", "risk_level", "signals", "detected_network"}
        assert required.issubset(set(ev.keys()))
        assert ev["risk_level"] in ("low", "suspicious", "confirmed")
        assert 0.0 <= ev["risk_score"] <= 1.0

    async def test_multiple_network_signals_accumulate(self, module_and_bus):
        """Multiple leak_network_detected events for same URL raise score."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("threat_detected", lambda **d: received.append(d))

        url = "https://t.me/high_risk_channel"

        for node_types in [
            {"TelegramChannel": 1, "Brand": 1},
            {"InviteLink": 3, "Brand": 1},
            {"DriveLink": 2, "TorrentLink": 1},
        ]:
            await bus.emit(
                "leak_network_detected",
                "test",
                brand="DocTutorials",
                url=url,
                platform="telegram",
                network_nodes=sum(node_types.values()),
                network_edges=2,
                node_types=node_types,
                graph_data={},
            )

        await asyncio.sleep(0.5)

        # We should have received at least 3 threat events
        assert len(received) >= 3
