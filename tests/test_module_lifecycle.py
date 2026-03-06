"""
SECTION 2 — MODULE LIFECYCLE TEST

Tests lifecycle transitions:
  UNINITIALIZED → INITIALIZING → READY → SHUTTING_DOWN → STOPPED

For modules: DiscoveryModule, CrawlerModule, IntelligenceModule, AlertsModule
"""

import pytest
from aimon.core.event_bus import EventBus
from aimon.core.base_module import ModuleState
from aimon.modules import (
    DiscoveryModule,
    CrawlerModule,
    IntelligenceModule,
    AlertsModule,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def make_bus():
    bus = EventBus()
    await bus.initialize()
    return bus


# ---------------------------------------------------------------------------
# DiscoveryModule
# ---------------------------------------------------------------------------

async def test_discovery_starts_uninitialized():
    m = DiscoveryModule("discovery")
    assert m.state == ModuleState.UNINITIALIZED


async def test_discovery_ready_after_initialize():
    bus = await make_bus()
    m = DiscoveryModule("discovery")
    m.event_bus = bus
    await m.initialize()
    assert m.state == ModuleState.READY
    assert m.is_ready() is True
    await m.shutdown()


async def test_discovery_stopped_after_shutdown():
    bus = await make_bus()
    m = DiscoveryModule("discovery")
    m.event_bus = bus
    await m.initialize()
    await m.shutdown()
    assert m.state == ModuleState.STOPPED
    assert m.is_ready() is False


async def test_discovery_double_initialize_noop():
    bus = await make_bus()
    m = DiscoveryModule("discovery")
    m.event_bus = bus
    await m.initialize()
    await m.initialize()  # second call should be no-op
    assert m.state == ModuleState.READY
    await m.shutdown()


async def test_discovery_double_shutdown_noop():
    bus = await make_bus()
    m = DiscoveryModule("discovery")
    m.event_bus = bus
    await m.initialize()
    await m.shutdown()
    await m.shutdown()  # second shutdown should be no-op
    assert m.state == ModuleState.STOPPED


async def test_discovery_get_status():
    bus = await make_bus()
    m = DiscoveryModule("discovery")
    m.event_bus = bus
    await m.initialize()
    status = m.get_status()
    assert isinstance(status, dict)
    assert "state" in status
    await m.shutdown()


# ---------------------------------------------------------------------------
# CrawlerModule
# ---------------------------------------------------------------------------

async def test_crawler_starts_uninitialized():
    m = CrawlerModule("crawler")
    assert m.state == ModuleState.UNINITIALIZED


async def test_crawler_ready_after_initialize():
    bus = await make_bus()
    m = CrawlerModule("crawler")
    m.event_bus = bus
    await m.initialize()
    assert m.state == ModuleState.READY
    assert m.is_ready() is True
    await m.shutdown()


async def test_crawler_stopped_after_shutdown():
    bus = await make_bus()
    m = CrawlerModule("crawler")
    m.event_bus = bus
    await m.initialize()
    await m.shutdown()
    assert m.state == ModuleState.STOPPED
    assert m.is_ready() is False


async def test_crawler_subscribes_to_source_discovered():
    """Crawler should have subscriptions after initialize."""
    bus = await make_bus()
    m = CrawlerModule("crawler")
    m.event_bus = bus
    await m.initialize()
    # After init, at least one subscription for source_discovered
    assert len(m._subscriptions) > 0
    await m.shutdown()


async def test_crawler_double_initialize_noop():
    bus = await make_bus()
    m = CrawlerModule("crawler")
    m.event_bus = bus
    await m.initialize()
    await m.initialize()
    assert m.state == ModuleState.READY
    await m.shutdown()


async def test_crawler_get_status():
    bus = await make_bus()
    m = CrawlerModule("crawler")
    m.event_bus = bus
    await m.initialize()
    status = m.get_status()
    assert isinstance(status, dict)
    assert "state" in status
    await m.shutdown()


# ---------------------------------------------------------------------------
# IntelligenceModule
# ---------------------------------------------------------------------------

async def test_intelligence_starts_uninitialized():
    m = IntelligenceModule("intelligence")
    assert m.state == ModuleState.UNINITIALIZED


async def test_intelligence_ready_after_initialize():
    bus = await make_bus()
    m = IntelligenceModule("intelligence")
    m.event_bus = bus
    await m.initialize()
    assert m.state == ModuleState.READY
    assert m.is_ready() is True
    await m.shutdown()


async def test_intelligence_stopped_after_shutdown():
    bus = await make_bus()
    m = IntelligenceModule("intelligence")
    m.event_bus = bus
    await m.initialize()
    await m.shutdown()
    assert m.state == ModuleState.STOPPED
    assert m.is_ready() is False


async def test_intelligence_get_status():
    bus = await make_bus()
    m = IntelligenceModule("intelligence")
    m.event_bus = bus
    await m.initialize()
    status = m.get_status()
    assert isinstance(status, dict)
    assert "state" in status
    await m.shutdown()


# ---------------------------------------------------------------------------
# AlertsModule
# ---------------------------------------------------------------------------

async def test_alerts_starts_uninitialized():
    m = AlertsModule("alerts")
    assert m.state == ModuleState.UNINITIALIZED


async def test_alerts_ready_after_initialize():
    bus = await make_bus()
    m = AlertsModule("alerts")
    m.event_bus = bus
    await m.initialize()
    assert m.state == ModuleState.READY
    assert m.is_ready() is True
    await m.shutdown()


async def test_alerts_stopped_after_shutdown():
    bus = await make_bus()
    m = AlertsModule("alerts")
    m.event_bus = bus
    await m.initialize()
    await m.shutdown()
    assert m.state == ModuleState.STOPPED
    assert m.is_ready() is False


async def test_alerts_get_status():
    bus = await make_bus()
    m = AlertsModule("alerts")
    m.event_bus = bus
    await m.initialize()
    status = m.get_status()
    assert isinstance(status, dict)
    assert "state" in status
    await m.shutdown()


# ---------------------------------------------------------------------------
# Module emit_event requires event_bus
# ---------------------------------------------------------------------------

async def test_module_emit_event_works():
    """emit_event should call event_bus.emit without error."""
    bus = await make_bus()
    received = []

    async def listener(**data):
        received.append(data)

    await bus.subscribe("test_emit", listener)

    m = DiscoveryModule("discovery")
    m.event_bus = bus
    await m.initialize()

    await m.emit_event("test_emit", foo="bar")
    import asyncio
    await asyncio.sleep(0.05)

    assert len(received) > 0
    assert received[0].get("foo") == "bar"
    await m.shutdown()
