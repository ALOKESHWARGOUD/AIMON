"""Shared pytest fixtures for AIMON test suite."""

import pytest
import asyncio
from aimon.core.event_bus import EventBus
from aimon.core.runtime import AIMONCoreRuntime
from aimon.storage.memory_storage import MemoryStorage
from aimon.modules import (
    DiscoveryModule,
    CrawlerModule,
    IntelligenceModule,
    AlertsModule,
)


@pytest.fixture
async def event_bus():
    """Create + initialize EventBus; clear after each test."""
    bus = EventBus()
    await bus.initialize()
    yield bus
    await bus.clear()


@pytest.fixture
async def runtime():
    """Full runtime: reset singleton, initialize, yield, stop, reset again."""
    AIMONCoreRuntime.reset_instance()
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    yield rt
    try:
        await rt.stop()
    except Exception:
        pass
    AIMONCoreRuntime.reset_instance()


@pytest.fixture
def fresh_runtime():
    """Lighter fixture: just reset + get_instance (no initialize)."""
    AIMONCoreRuntime.reset_instance()
    rt = AIMONCoreRuntime.get_instance()
    yield rt
    AIMONCoreRuntime.reset_instance()


@pytest.fixture
async def memory_storage():
    """Create + initialize MemoryStorage."""
    storage = MemoryStorage()
    await storage.initialize()
    yield storage


@pytest.fixture
async def all_modules(event_bus):
    """Create all 4 modules sharing the same event_bus; initialize all; yield dict; shutdown all."""
    discovery = DiscoveryModule("discovery")
    crawler = CrawlerModule("crawler")
    intelligence = IntelligenceModule("intelligence")
    alerts = AlertsModule("alerts")

    for module in [discovery, crawler, intelligence, alerts]:
        module.event_bus = event_bus
        await module.initialize()

    yield {
        "discovery": discovery,
        "crawler": crawler,
        "intelligence": intelligence,
        "alerts": alerts,
    }

    for module in [discovery, crawler, intelligence, alerts]:
        try:
            await module.shutdown()
        except Exception:
            pass
