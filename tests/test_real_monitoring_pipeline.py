"""
SECTION 11 — REAL WORLD INTEGRATION TEST

Simulates real monitoring:
1. Start framework
2. Run discovery query
3. Crawl discovered URLs
4. Analyze content
5. Generate alerts

Verifies complete workflow.
"""

import asyncio
import pytest
from aimon.framework_api import AIMON
from aimon.core.runtime import AIMONCoreRuntime


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before and after each test."""
    AIMONCoreRuntime.reset_instance()
    yield
    AIMONCoreRuntime.reset_instance()


# ---------------------------------------------------------------------------
# Context manager usage
# ---------------------------------------------------------------------------

async def test_context_manager_search_returns_results():
    AIMONCoreRuntime.reset_instance()
    async with AIMON() as fw:
        sources = await fw.search_sources("course torrent")
        assert isinstance(sources, list)
        assert len(sources) > 0


async def test_context_manager_get_threats_returns_list():
    AIMONCoreRuntime.reset_instance()
    async with AIMON() as fw:
        await fw.search_sources("course torrent")
        await asyncio.sleep(0.5)
        threats = await fw.get_threats()
        assert isinstance(threats, list)


async def test_context_manager_get_alerts_returns_list():
    AIMONCoreRuntime.reset_instance()
    async with AIMON() as fw:
        await fw.search_sources("movie download")
        await asyncio.sleep(0.5)
        alerts = await fw.get_alerts_list()
        assert isinstance(alerts, list)


async def test_context_manager_get_status_initialized():
    AIMONCoreRuntime.reset_instance()
    async with AIMON() as fw:
        status = await fw.get_status()
        assert isinstance(status, dict)
        assert status["initialized"] is True


async def test_context_manager_get_metrics_returns_dict():
    AIMONCoreRuntime.reset_instance()
    async with AIMON() as fw:
        metrics = await fw.get_metrics()
        assert isinstance(metrics, dict)


# ---------------------------------------------------------------------------
# Manual initialize / shutdown
# ---------------------------------------------------------------------------

async def test_manual_initialize_shutdown():
    AIMONCoreRuntime.reset_instance()
    fw = AIMON()
    await fw.initialize()
    try:
        sources = await fw.search_sources("software crack")
        assert isinstance(sources, list)
    finally:
        await fw.shutdown()


async def test_manual_status_after_initialize():
    AIMONCoreRuntime.reset_instance()
    fw = AIMON()
    await fw.initialize()
    try:
        status = await fw.get_status()
        assert status["initialized"] is True
    finally:
        await fw.shutdown()


# ---------------------------------------------------------------------------
# Multiple sequential queries → cumulative threats
# ---------------------------------------------------------------------------

async def test_multiple_queries_cumulative_threats():
    AIMONCoreRuntime.reset_instance()
    async with AIMON() as fw:
        queries = ["software crack", "movie download", "leaked course"]
        for q in queries:
            await fw.search_sources(q)
        await asyncio.sleep(0.5)

        threats = await fw.get_threats()
        assert isinstance(threats, list)
        assert len(threats) >= len(queries)


# ---------------------------------------------------------------------------
# Event chain verification
# ---------------------------------------------------------------------------

async def test_event_chain_occurred():
    """Verify event log has entries for the full pipeline."""
    AIMONCoreRuntime.reset_instance()
    async with AIMON() as fw:
        await fw.search_sources("course torrent")
        await asyncio.sleep(0.5)

        bus = fw.runtime.event_bus
        log = await bus.get_event_log()
        event_types = {e.event_type for e in log}

        assert "source_discovered" in event_types
        assert "page_crawled" in event_types
        assert "threat_detected" in event_types


# ---------------------------------------------------------------------------
# Stop and re-start with fresh instance
# ---------------------------------------------------------------------------

async def test_restart_with_fresh_instance():
    """Framework can be stopped and then a new instance started."""
    AIMONCoreRuntime.reset_instance()
    fw1 = AIMON()
    await fw1.initialize()
    await fw1.shutdown()

    AIMONCoreRuntime.reset_instance()
    async with AIMON() as fw2:
        sources = await fw2.search_sources("movie download")
        assert isinstance(sources, list)
