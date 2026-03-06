"""
SECTION 3 — EVENT BUS PIPELINE TEST

Simulates the full event chain:
1. DiscoveryModule emits source_discovered
2. CrawlerModule receives event → crawls
3. CrawlerModule emits page_crawled
4. IntelligenceModule receives event → analyzes
5. IntelligenceModule emits threat_detected
6. AlertsModule receives event → generates alert

Verifies event propagation works end-to-end.
"""

import asyncio
import pytest
from aimon.core.event_bus import EventBus
from aimon.modules import (
    DiscoveryModule,
    CrawlerModule,
    IntelligenceModule,
    AlertsModule,
)


async def _make_initialized_bus():
    bus = EventBus()
    await bus.initialize()
    return bus


async def _make_all_modules(bus):
    discovery = DiscoveryModule("discovery")
    crawler = CrawlerModule("crawler")
    intelligence = IntelligenceModule("intelligence")
    alerts = AlertsModule("alerts")

    for m in [discovery, crawler, intelligence, alerts]:
        m.event_bus = bus
        await m.initialize()

    return discovery, crawler, intelligence, alerts


async def _shutdown_all(modules):
    for m in modules:
        try:
            await m.shutdown()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Full pipeline via discovery.search()
# ---------------------------------------------------------------------------

async def test_source_discovered_emitted():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    try:
        await discovery.search("movie download")
        await asyncio.sleep(0.2)

        log = await bus.get_event_log(event_type="source_discovered")
        assert len(log) > 0
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


async def test_page_crawled_emitted_after_source_discovered():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    try:
        await discovery.search("course torrent")
        await asyncio.sleep(0.3)

        log = await bus.get_event_log(event_type="page_crawled")
        assert len(log) > 0
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


async def test_threat_detected_emitted_after_page_crawled():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    try:
        await discovery.search("software crack")
        await asyncio.sleep(0.3)

        log = await bus.get_event_log(event_type="threat_detected")
        assert len(log) > 0
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


async def test_alert_generated_emitted_after_threat_detected():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    try:
        await discovery.search("leaked course")
        await asyncio.sleep(0.3)

        log = await bus.get_event_log(event_type="alert_generated")
        assert len(log) > 0
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


async def test_crawler_has_crawled_pages_after_search():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    try:
        await discovery.search("movie download")
        await asyncio.sleep(0.3)

        pages = crawler.get_crawled_pages()
        assert len(pages) > 0
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


async def test_intelligence_has_threats_after_search():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    try:
        await discovery.search("movie download")
        await asyncio.sleep(0.3)

        threats = intelligence.get_threats()
        assert len(threats) > 0
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


async def test_alerts_has_alerts_after_search():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    try:
        await discovery.search("movie download")
        await asyncio.sleep(0.3)

        alert_list = alerts.get_alerts()
        assert len(alert_list) > 0
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


# ---------------------------------------------------------------------------
# Direct listener subscription
# ---------------------------------------------------------------------------

async def test_direct_listener_on_source_discovered():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    collected = []

    async def on_source(**data):
        collected.append(data)

    await bus.subscribe("source_discovered", on_source)

    try:
        await discovery.search("test query")
        await asyncio.sleep(0.2)

        assert len(collected) > 0
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


async def test_direct_listener_on_page_crawled():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    collected = []

    async def on_page(**data):
        collected.append(data)

    await bus.subscribe("page_crawled", on_page)

    try:
        await discovery.search("test query")
        await asyncio.sleep(0.3)

        assert len(collected) > 0
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


# ---------------------------------------------------------------------------
# Multiple sequential queries
# ---------------------------------------------------------------------------

async def test_multiple_queries_in_sequence():
    bus = await _make_initialized_bus()
    discovery, crawler, intelligence, alerts = await _make_all_modules(bus)

    try:
        for query in ["software crack", "movie download"]:
            await discovery.search(query)
            await asyncio.sleep(0.1)

        log = await bus.get_event_log(event_type="source_discovered")
        assert len(log) >= 2
    finally:
        await _shutdown_all([discovery, crawler, intelligence, alerts])
        await bus.clear()


# ---------------------------------------------------------------------------
# Manual source_discovered emission triggers crawler
# ---------------------------------------------------------------------------

async def test_manual_source_discovered_triggers_crawler():
    bus = await _make_initialized_bus()
    _, crawler, _, _ = await _make_all_modules(bus)

    source = {
        "id": "manual_source",
        "name": "Manual Source",
        "url": "https://example.com/manual",
        "source_type": "web",
    }

    try:
        await bus.emit("source_discovered", "test", source=source)
        await asyncio.sleep(0.2)

        pages = crawler.get_crawled_pages()
        ids = [p["source_id"] for p in pages]
        assert "manual_source" in ids
    finally:
        discovery = DiscoveryModule("disc_tmp")
        intelligence = IntelligenceModule("intel_tmp")
        alerts = AlertsModule("alerts_tmp")
        # Just shut down crawler
        try:
            await crawler.shutdown()
        except Exception:
            pass
        await bus.clear()
