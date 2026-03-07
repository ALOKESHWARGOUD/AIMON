"""
Tests for the Network Intelligence Layer.

Tests LeakNetworkMapper (in-memory mode), RelationshipBuilder, and
NetworkMapperModule.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from aimon.core.event_bus import EventBus
from aimon.intelligence.leak_network_mapper import LeakNetworkMapper
from aimon.intelligence.relationship_builder import RelationshipBuilder
from aimon.modules.network_mapper_module import NetworkMapperModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_mapper() -> LeakNetworkMapper:
    """Create a networkx-backed LeakNetworkMapper (no Neo4j required)."""
    mapper = LeakNetworkMapper({})  # no neo4j credentials → networkx fallback
    await mapper.initialize()
    return mapper


async def _make_event_bus() -> EventBus:
    bus = EventBus()
    await bus.initialize()
    return bus


# ===========================================================================
# TestLeakNetworkMapper
# ===========================================================================


class TestLeakNetworkMapper:
    """Tests for LeakNetworkMapper in networkx in-memory mode."""

    async def test_initialize_uses_networkx_fallback(self):
        """Mapper falls back to networkx when Neo4j not configured."""
        mapper = await _make_mapper()
        assert mapper._graph is not None
        assert mapper._use_neo4j is False

    async def test_add_node_returns_string_id(self):
        """add_node returns a non-empty string ID."""
        mapper = await _make_mapper()
        nid = await mapper.add_node("TelegramChannel", {"url": "https://t.me/test", "title": "Test"})
        assert isinstance(nid, str)
        assert len(nid) > 0

    async def test_add_node_stores_properties(self):
        """Node properties are stored and retrievable."""
        mapper = await _make_mapper()
        nid = await mapper.add_node("Brand", {"name": "DocTutorials"})
        assert nid in mapper._node_index
        assert mapper._node_index[nid]["name"] == "DocTutorials"
        assert mapper._node_index[nid]["_type"] == "Brand"

    async def test_add_relationship_creates_edge(self):
        """add_relationship creates a directed edge between nodes."""
        mapper = await _make_mapper()
        from_id = await mapper.add_node("TelegramChannel", {"url": "https://t.me/c1", "title": "C1"})
        to_id = await mapper.add_node("Brand", {"name": "TestBrand"})
        await mapper.add_relationship(from_id, to_id, "TARGETS")

        assert mapper._graph.has_edge(from_id, to_id)

    async def test_get_network_returns_brand_nodes(self):
        """get_network returns nodes related to the specified brand."""
        mapper = await _make_mapper()
        brand_id = await mapper.add_node("Brand", {"name": "DocTutorials"})
        channel_id = await mapper.add_node("TelegramChannel", {"url": "https://t.me/dt", "title": "DT"})
        await mapper.add_relationship(channel_id, brand_id, "TARGETS")

        network = await mapper.get_network("DocTutorials")

        assert "nodes" in network
        assert "edges" in network

    async def test_get_network_stats(self):
        """get_network_stats returns correct node and edge counts."""
        mapper = await _make_mapper()
        n1 = await mapper.add_node("TelegramChannel", {"url": "https://t.me/a", "title": "A"})
        n2 = await mapper.add_node("DriveLink", {"url": "https://drive.google.com/1", "provider": "google_drive"})
        await mapper.add_relationship(n1, n2, "SHARED_BY")

        stats = await mapper.get_network_stats()
        assert stats["nodes"] >= 2
        assert stats["edges"] >= 1
        assert "node_types" in stats

    async def test_find_connected_nodes(self):
        """find_connected_nodes traverses the graph."""
        mapper = await _make_mapper()
        n1 = await mapper.add_node("TelegramChannel", {"url": "https://t.me/b", "title": "B"})
        n2 = await mapper.add_node("InviteLink", {"url": "https://t.me/+INVITE", "platform": "telegram"})
        await mapper.add_relationship(n1, n2, "SHARED_BY")

        connected = await mapper.find_connected_nodes(n1, depth=2)
        assert isinstance(connected, list)
        # n2 should be reachable
        urls = [c.get("url") for c in connected]
        assert "https://t.me/+INVITE" in urls

    async def test_duplicate_node_updates_properties(self):
        """Adding the same node twice updates its properties."""
        mapper = await _make_mapper()
        nid1 = await mapper.add_node("Brand", {"name": "BrandA", "extra": "old"})
        nid2 = await mapper.add_node("Brand", {"name": "BrandA", "extra": "new"})
        assert nid1 == nid2
        assert mapper._node_index[nid1]["extra"] == "new"


# ===========================================================================
# TestRelationshipBuilder
# ===========================================================================


class TestRelationshipBuilder:
    """Tests for RelationshipBuilder signal → node/edge extraction."""

    async def _make_builder(self):
        mapper = await _make_mapper()
        builder = RelationshipBuilder(mapper)
        return builder, mapper

    async def test_telegram_signal_creates_channel_node(self):
        """Telegram platform signal creates TelegramChannel node."""
        builder, mapper = await self._make_builder()

        signal = {
            "brand": "DocTutorials",
            "url": "https://t.me/testchannel",
            "platform": "telegram",
            "signal_type": "invite_link",
            "confidence": 0.9,
            "raw_signals": ["https://t.me/+INVITEABC"],
            "source_event": "telegram_signal_detected",
        }

        relationships = await builder.process_signal(signal)
        assert len(relationships) > 0

        node_types = [mapper._node_index[nid]["_type"] for nid in mapper._node_index]
        assert "TelegramChannel" in node_types
        assert "Brand" in node_types

    async def test_drive_link_creates_drive_node(self):
        """Signal with Google Drive URL creates DriveLink node."""
        builder, mapper = await self._make_builder()

        signal = {
            "brand": "TestBrand",
            "url": "https://reddit.com/r/piracy/comments/xyz",
            "platform": "reddit",
            "signal_type": "url_pattern",
            "confidence": 0.7,
            "raw_signals": [
                "https://drive.google.com/file/d/XYZABC/view",
            ],
            "source_event": "page_crawled",
        }

        await builder.process_signal(signal)
        node_types = [mapper._node_index[nid]["_type"] for nid in mapper._node_index]
        assert "DriveLink" in node_types

    async def test_torrent_link_creates_torrent_node(self):
        """Signal with torrent site URL creates TorrentLink node."""
        builder, mapper = await self._make_builder()

        signal = {
            "brand": "TestBrand",
            "url": "https://t.me/piratechannel",
            "platform": "telegram",
            "signal_type": "url_pattern",
            "confidence": 0.8,
            "raw_signals": ["https://1337x.to/torrent/12345/course"],
            "source_event": "page_crawled",
        }

        await builder.process_signal(signal)
        node_types = [mapper._node_index[nid]["_type"] for nid in mapper._node_index]
        assert "TorrentLink" in node_types

    async def test_empty_signal_creates_brand_node(self):
        """Minimal signal with no URLs still creates a Brand node."""
        builder, mapper = await self._make_builder()

        signal = {
            "brand": "CleanBrand",
            "url": "https://example.com",
            "platform": "unknown",
            "signal_type": "keyword_match",
            "confidence": 0.4,
            "raw_signals": [],
            "source_event": "page_crawled",
        }

        await builder.process_signal(signal)
        node_types = [mapper._node_index[nid]["_type"] for nid in mapper._node_index]
        assert "Brand" in node_types

    async def test_relationships_list_returned(self):
        """process_signal returns a list of (from, rel, to) tuples."""
        builder, mapper = await self._make_builder()

        signal = {
            "brand": "DocTutorials",
            "url": "https://t.me/doc_channel",
            "platform": "telegram",
            "signal_type": "invite_link",
            "confidence": 0.95,
            "raw_signals": ["https://t.me/+JOIN123"],
            "source_event": "telegram_signal_detected",
        }

        relationships = await builder.process_signal(signal)
        assert isinstance(relationships, list)
        for rel in relationships:
            assert len(rel) == 3
            from_id, rel_type, to_id = rel
            assert isinstance(from_id, str)
            assert isinstance(rel_type, str)
            assert isinstance(to_id, str)


# ===========================================================================
# TestNetworkMapperModule
# ===========================================================================


class TestNetworkMapperModule:
    """Tests for NetworkMapperModule event handling."""

    @pytest.fixture
    async def module_and_bus(self):
        bus = await _make_event_bus()
        module = NetworkMapperModule("network_mapper", bus)
        await module.initialize()
        return module, bus

    async def test_emits_leak_network_detected(self, module_and_bus):
        """Module emits leak_network_detected after receiving a signal."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("leak_network_detected", lambda **d: received.append(d))

        await bus.emit(
            "leak_signal_detected",
            "test",
            brand="DocTutorials",
            url="https://t.me/piracy_channel",
            platform="telegram",
            signal_type="invite_link",
            confidence=0.9,
            raw_signals=["https://t.me/+INVITE999"],
            source_event="page_crawled",
        )
        await asyncio.sleep(0.3)

        assert len(received) > 0
        event = received[0]
        assert "brand" in event
        assert "network_nodes" in event
        assert "network_edges" in event
        assert "node_types" in event
        assert "graph_data" in event

    async def test_network_detected_schema(self, module_and_bus):
        """Emitted event has correct field types."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("leak_network_detected", lambda **d: received.append(d))

        await bus.emit(
            "leak_signal_detected",
            "test",
            brand="BrandX",
            url="https://drive.google.com/file/abc",
            platform="gdrive",
            signal_type="url_pattern",
            confidence=0.8,
            raw_signals=[],
            source_event="page_crawled",
        )
        await asyncio.sleep(0.3)

        assert received
        ev = received[0]
        assert isinstance(ev["network_nodes"], int)
        assert isinstance(ev["network_edges"], int)
        assert isinstance(ev["node_types"], dict)

    async def test_module_initializes_mapper(self, module_and_bus):
        """Module's internal mapper is initialized after module init."""
        module, bus = module_and_bus
        assert module._mapper is not None
        assert module._builder is not None

    async def test_multiple_signals_accumulate_nodes(self, module_and_bus):
        """Multiple signals add more nodes to the graph."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("leak_network_detected", lambda **d: received.append(d))

        for i in range(3):
            await bus.emit(
                "leak_signal_detected",
                "test",
                brand="DocTutorials",
                url=f"https://t.me/channel_{i}",
                platform="telegram",
                signal_type="invite_link",
                confidence=0.85,
                raw_signals=[],
                source_event="page_crawled",
            )

        await asyncio.sleep(0.5)
        assert len(received) >= 3
