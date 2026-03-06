"""
Performance Tests for AIMON Framework.

Uses time.perf_counter() and pytest-asyncio (no pytest-benchmark dependency).
"""

import asyncio
import time
from typing import List

import pytest

from aimon.core.event_bus import EventBus, Event
from aimon.core.execution_engine import ExecutionEngine, TaskPriority
from aimon.core.runtime import AIMONCoreRuntime
from aimon.modules import DiscoveryModule, CrawlerModule, IntelligenceModule


# ---------------------------------------------------------------------------
# Test 1 — EventBus: 100 events × 5 handlers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_event_bus_100_events():
    """EventBus should dispatch 100 events to 5 handlers (500 calls) under 5ms/event."""
    bus = EventBus()
    await bus.initialize()

    call_log: List[int] = []

    # Register 5 handlers
    for i in range(5):
        async def make_handler(idx=i):
            async def handler(event: Event):
                call_log.append(idx)
            return handler
        await bus.subscribe("perf_event", await make_handler())

    n_events = 100
    t_start = time.perf_counter()

    for _ in range(n_events):
        await bus.emit("perf_event", source="perf_test")

    # Allow async dispatch to settle
    await asyncio.sleep(0.2)

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    assert len(call_log) == 500, f"Expected 500 handler calls, got {len(call_log)}"

    per_event_ms = (elapsed / n_events) * 1000
    print(
        f"\n[EventBus] {n_events} events × 5 handlers = {len(call_log)} calls "
        f"in {elapsed:.4f}s ({per_event_ms:.3f} ms/event)"
    )
    assert per_event_ms < 5, f"Per-event latency {per_event_ms:.3f}ms exceeds 5ms limit"


# ---------------------------------------------------------------------------
# Test 2 — ExecutionEngine: 100 no-op tasks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execution_engine_100_tasks():
    """ExecutionEngine should complete 100 no-op tasks with >10 tasks/sec throughput."""
    engine = ExecutionEngine(max_concurrent=20)
    await engine.start()

    async def _noop_task():
        await asyncio.sleep(0)
        return True

    t_start = time.perf_counter()
    task_ids = []
    for _ in range(100):
        tid = await engine.submit(_noop_task(), priority=TaskPriority.NORMAL)
        task_ids.append(tid)

    # Wait for all tasks to complete (up to 5 seconds)
    deadline = time.perf_counter() + 5.0
    completed = set()
    while len(completed) < 100 and time.perf_counter() < deadline:
        for tid in task_ids:
            if tid not in completed:
                result = await engine.get_result(tid)
                if result is not None and result.result is not None:
                    completed.add(tid)
        if len(completed) < 100:
            await asyncio.sleep(0.05)

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    throughput = len(completed) / elapsed if elapsed > 0 else float("inf")
    print(
        f"\n[ExecutionEngine] {len(completed)}/100 tasks completed "
        f"in {elapsed:.4f}s ({throughput:.1f} tasks/sec)"
    )

    assert len(completed) == 100, f"Only {len(completed)}/100 tasks completed within 5 seconds"
    assert throughput > 10, f"Throughput {throughput:.1f} tasks/sec is below 10 tasks/sec"

    await engine.stop()


# ---------------------------------------------------------------------------
# Test 3 — DiscoveryModule: 100 search calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_module_chain_100_searches():
    """DiscoveryModule.search() should respond in <50ms per call on average."""
    AIMONCoreRuntime.reset_instance()

    bus = EventBus()
    await bus.initialize()

    discovery = DiscoveryModule("discovery_perf")
    discovery.event_bus = bus
    await discovery.initialize()

    n = 100
    t_start = time.perf_counter()

    for i in range(n):
        results = await discovery.search(f"test query {i}")
        assert isinstance(results, list), f"search() must return a list (got {type(results)})"

    t_end = time.perf_counter()
    elapsed = t_end - t_start
    per_search_ms = (elapsed / n) * 1000

    print(
        f"\n[DiscoveryModule] {n} searches in {elapsed:.4f}s "
        f"({per_search_ms:.3f} ms/search)"
    )
    assert per_search_ms < 50, f"Per-search time {per_search_ms:.3f}ms exceeds 50ms limit"

    await discovery.shutdown()
    AIMONCoreRuntime.reset_instance()


# ---------------------------------------------------------------------------
# Test 4 — Full chain: Discovery → Crawler → Intelligence for 10 queries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_chain_10_items():
    """Full search→crawl→analyze chain for 10 queries should complete within 30 s."""
    AIMONCoreRuntime.reset_instance()

    bus = EventBus()
    await bus.initialize()

    discovery = DiscoveryModule("discovery_chain")
    crawler = CrawlerModule("crawler_chain")
    intelligence = IntelligenceModule("intelligence_chain")

    for module in (discovery, crawler, intelligence):
        module.event_bus = bus
        await module.initialize()

    t_start = time.perf_counter()

    for i in range(10):
        sources = await discovery.search(f"chain query {i}")
        assert isinstance(sources, list)
        if sources:
            page = await crawler.crawl(sources[0])
            assert isinstance(page, dict)
            analysis = await intelligence.analyze(page)
            assert isinstance(analysis, dict)

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    print(f"\n[FullChain] 10 queries completed in {elapsed:.4f}s")
    assert elapsed < 30, f"Full chain took {elapsed:.2f}s, which exceeds 30s limit"

    for module in (discovery, crawler, intelligence):
        await module.shutdown()

    AIMONCoreRuntime.reset_instance()
