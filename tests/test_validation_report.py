"""
SECTION 12 — TEST VALIDATION REPORT

Generates the AIMON Validation Report.

Runs a comprehensive check of all systems and prints:
  - Total systems checked
  - Passed systems
  - Failed systems
  - Performance metrics
"""

import asyncio
import time
import pytest
from aimon.core.runtime import AIMONCoreRuntime
from aimon.core.event_bus import EventBus
from aimon.core.execution_engine import ExecutionEngine, TaskPriority
from aimon.modules import (
    DiscoveryModule,
    CrawlerModule,
    IntelligenceModule,
    AlertsModule,
)
from aimon.storage.memory_storage import MemoryStorage
from aimon.connectors.google_connector import GoogleConnector
from aimon.connectors.reddit_connector import RedditConnector
from aimon.fingerprint import VideoFingerprinter, AudioFingerprinter
from aimon.sync import AIMONSync


async def test_generate_aimon_validation_report():
    """
    Comprehensive validation of all AIMON v1 subsystems.
    Prints formatted validation report. Asserts all subsystems pass.
    """
    results = {}
    performance = {}

    # -----------------------------------------------------------------------
    # Helper
    # -----------------------------------------------------------------------
    async def check(name: str, coro):
        try:
            await coro
            results[name] = "PASS"
        except Exception as e:
            results[name] = f"FAIL: {e}"

    # -----------------------------------------------------------------------
    # 1. Runtime initialization
    # -----------------------------------------------------------------------
    async def _test_runtime():
        AIMONCoreRuntime.reset_instance()
        rt = AIMONCoreRuntime.get_instance()
        await rt.initialize()
        assert rt._initialized
        await rt.stop()
        AIMONCoreRuntime.reset_instance()

    await check("Runtime Initialization", _test_runtime())

    # -----------------------------------------------------------------------
    # 2. EventBus pub/sub — also measure perf (10 events)
    # -----------------------------------------------------------------------
    async def _test_event_bus():
        bus = EventBus()
        await bus.initialize()
        received = []

        async def handler(**data):
            received.append(data)

        await bus.subscribe("val_event", handler)
        t0 = time.perf_counter()
        for _ in range(10):
            await bus.emit("val_event", "test")
        elapsed_eb = time.perf_counter() - t0
        performance["eventbus_10_events_sec"] = 10 / elapsed_eb if elapsed_eb > 1e-9 else 10000.0
        assert len(received) == 10
        await bus.clear()

    await check("EventBus Pub/Sub", _test_event_bus())

    # -----------------------------------------------------------------------
    # 3. ExecutionEngine task execution — also measure perf (10 tasks)
    # -----------------------------------------------------------------------
    async def _test_execution_engine():
        engine = ExecutionEngine(max_concurrent=10)
        await engine.start()

        async def noop():
            await asyncio.sleep(0)
            return True

        t0 = time.perf_counter()
        task_ids = [await engine.submit(noop(), priority=TaskPriority.NORMAL) for _ in range(10)]
        deadline = time.perf_counter() + 5.0
        done = set()
        while len(done) < 10 and time.perf_counter() < deadline:
            for tid in task_ids:
                if tid not in done:
                    r = await engine.get_result(tid)
                    if r and r.result is not None:
                        done.add(tid)
            if len(done) < 10:
                await asyncio.sleep(0.05)
        elapsed_ee = time.perf_counter() - t0
        performance["engine_10_tasks_sec"] = len(done) / elapsed_ee if elapsed_ee > 1e-9 else 10000.0
        assert len(done) == 10
        await engine.stop()

    await check("ExecutionEngine Task Execution", _test_execution_engine())

    # -----------------------------------------------------------------------
    # 4. DiscoveryModule search
    # -----------------------------------------------------------------------
    async def _test_discovery():
        bus = EventBus()
        await bus.initialize()
        m = DiscoveryModule("d")
        m.event_bus = bus
        await m.initialize()
        sources = await m.search("movie download")
        assert isinstance(sources, list) and len(sources) > 0
        await m.shutdown()
        await bus.clear()

    await check("DiscoveryModule Search", _test_discovery())

    # -----------------------------------------------------------------------
    # 5. CrawlerModule crawl
    # -----------------------------------------------------------------------
    async def _test_crawler():
        bus = EventBus()
        await bus.initialize()
        m = CrawlerModule("c")
        m.event_bus = bus
        await m.initialize()
        page = await m.crawl({"id": "s1", "url": "https://example.com", "name": "Test"})
        assert "source_id" in page
        await m.shutdown()
        await bus.clear()

    await check("CrawlerModule Crawl", _test_crawler())

    # -----------------------------------------------------------------------
    # 6. IntelligenceModule analyze
    # -----------------------------------------------------------------------
    async def _test_intelligence():
        bus = EventBus()
        await bus.initialize()
        m = IntelligenceModule("i")
        m.event_bus = bus
        await m.initialize()
        analysis = await m.analyze({"source_id": "s1", "content": "leaked content"})
        assert "threat_score" in analysis
        await m.shutdown()
        await bus.clear()

    await check("IntelligenceModule Analyze", _test_intelligence())

    # -----------------------------------------------------------------------
    # 7. AlertsModule generate_alert
    # -----------------------------------------------------------------------
    async def _test_alerts():
        bus = EventBus()
        await bus.initialize()
        m = AlertsModule("a")
        m.event_bus = bus
        await m.initialize()
        alert = await m.generate_alert({
            "source_id": "s1", "threat_level": "high",
            "threat_score": 0.9, "detected_assets": []
        })
        assert "alert_id" in alert
        await m.shutdown()
        await bus.clear()

    await check("AlertsModule Generate Alert", _test_alerts())

    # -----------------------------------------------------------------------
    # 8. MemoryStorage CRUD
    # -----------------------------------------------------------------------
    async def _test_memory_storage():
        s = MemoryStorage()
        await s.initialize()
        assert await s.save("k", {"v": 1})
        data = await s.get("k")
        assert data == {"v": 1}
        assert await s.delete("k")
        assert await s.get("k") is None

    await check("MemoryStorage CRUD", _test_memory_storage())

    # -----------------------------------------------------------------------
    # 9. GoogleConnector search
    # -----------------------------------------------------------------------
    async def _test_google():
        c = GoogleConnector("google")
        await c.initialize()
        r = await c.search("movie download")
        assert isinstance(r, list) and len(r) > 0
        await c.shutdown()

    await check("GoogleConnector Search", _test_google())

    # -----------------------------------------------------------------------
    # 10. RedditConnector search
    # -----------------------------------------------------------------------
    async def _test_reddit():
        c = RedditConnector("reddit")
        await c.initialize()
        r = await c.search("movie download")
        assert isinstance(r, list) and len(r) > 0
        await c.shutdown()

    await check("RedditConnector Search", _test_reddit())

    # -----------------------------------------------------------------------
    # 11. VideoFingerprinter
    # -----------------------------------------------------------------------
    async def _test_video_fp():
        fp = VideoFingerprinter()
        result = await fp.fingerprint("video data")
        assert isinstance(result, str) and len(result) > 0

    await check("VideoFingerprinter", _test_video_fp())

    # -----------------------------------------------------------------------
    # 12. AudioFingerprinter
    # -----------------------------------------------------------------------
    async def _test_audio_fp():
        fp = AudioFingerprinter()
        result = await fp.fingerprint("audio data")
        assert isinstance(result, str) and len(result) > 0

    await check("AudioFingerprinter", _test_audio_fp())

    # -----------------------------------------------------------------------
    # 13. AIMONSync search_sources (run in thread to avoid nested-loop issue)
    # -----------------------------------------------------------------------
    async def _test_sync_api():
        import concurrent.futures

        def _run_sync():
            AIMONCoreRuntime.reset_instance()
            fw = AIMONSync()
            fw.initialize()
            sources = fw.search_sources("movie download")
            fw.shutdown()
            AIMONCoreRuntime.reset_instance()
            return sources

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            sources = await loop.run_in_executor(pool, _run_sync)
        assert isinstance(sources, list) and len(sources) > 0

    await check("AIMONSync Search Sources", _test_sync_api())

    # -----------------------------------------------------------------------
    # 14. Full pipeline (source → crawl → analyze → alert) — also measure perf
    # -----------------------------------------------------------------------
    async def _test_full_pipeline():
        bus = EventBus()
        await bus.initialize()
        discovery = DiscoveryModule("dp")
        crawler = CrawlerModule("cp")
        intelligence = IntelligenceModule("ip")
        alerts = AlertsModule("ap")

        for m in [discovery, crawler, intelligence, alerts]:
            m.event_bus = bus
            await m.initialize()

        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            sources = await discovery.search("pipeline test")
            assert len(sources) > 0
            page = await crawler.crawl(sources[0])
            analysis = await intelligence.analyze(page)
            await alerts.generate_alert(analysis)
            latencies.append((time.perf_counter() - t0) * 1000)

        performance["pipeline_avg_ms"] = sum(latencies) / len(latencies)
        for m in [discovery, crawler, intelligence, alerts]:
            await m.shutdown()
        await bus.clear()

    await check("Full Pipeline", _test_full_pipeline())

    # -----------------------------------------------------------------------
    # Tally results
    # -----------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for v in results.values() if v == "PASS")
    failed = total - passed

    eb_rate = performance.get("eventbus_10_events_sec", 0)
    ee_rate = performance.get("engine_10_tasks_sec", 0)
    pipeline_ms = performance.get("pipeline_avg_ms", 0)

    # Print validation report
    width = 56
    border = "═" * width

    print(f"\n╔{border}╗")
    print(f"║{'AIMON v1 Validation Report':^{width}}║")
    print(f"╠{border}╣")
    print(f"║  {'Total Systems Checked:':<30}{total:>22}  ║")
    print(f"║  {'Passed:':<30}{passed:>22}  ║")
    print(f"║  {'Failed:':<30}{failed:>22}  ║")

    if failed > 0:
        print(f"╠{border}╣")
        print(f"║  {'Failed Systems:':<{width - 2}}  ║")
        for name, val in results.items():
            if val != "PASS":
                msg = f"  ✗ {name}: {val}"
                print(f"║{msg:<{width}}║")

    print(f"╠{border}╣")
    print(f"║  {'Performance Metrics':<{width - 2}}  ║")
    print(f"║  {'EventBus:':<30}{eb_rate:>18.1f} ev/s  ║")
    print(f"║  {'ExecutionEngine:':<30}{ee_rate:>18.1f} t/s  ║")
    print(f"║  {'Pipeline Latency:':<30}{pipeline_ms:>16.1f} ms/c  ║")
    print(f"╠{border}╣")
    status_str = "AIMON v1: PRODUCTION READY ✓" if failed == 0 else f"AIMON v1: {failed} SYSTEM(S) FAILED ✗"
    print(f"║{status_str:^{width}}║")
    print(f"╚{border}╝\n")

    assert failed == 0, f"{failed} subsystem(s) failed: " + ", ".join(
        k for k, v in results.items() if v != "PASS"
    )
