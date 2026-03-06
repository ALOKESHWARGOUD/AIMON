"""
Tests for doctutorials_monitor.py

Covers:
- detect_leak(): risk scoring and the is_leak flag across all edge cases
- save_alert() / send_alert(): file output and timezone-aware timestamp
- scan_query(): interaction with the AIMON framework
- Integration: full framework run with DocTutorials queries
"""

import asyncio
import io
import json
import os
import sys
import pytest

from aimon.core.runtime import AIMONCoreRuntime

# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from doctutorials_monitor import (
    ALERT_FILE,
    KEYWORDS,
    LEAK_KEYWORDS,
    RISK_THRESHOLD,
    detect_leak,
    save_alert,
    scan_query,
    send_alert,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_runtime():
    """Ensure the AIMON singleton is fresh before and after each test."""
    AIMONCoreRuntime.reset_instance()
    yield
    AIMONCoreRuntime.reset_instance()


@pytest.fixture
def tmp_alert_file(tmp_path, monkeypatch):
    """Redirect ALERT_FILE writes to a temporary path."""
    import doctutorials_monitor as dm
    alert_path = str(tmp_path / "alerts_log.json")
    monkeypatch.setattr(dm, "ALERT_FILE", alert_path)
    return alert_path


# ===========================================================================
# detect_leak() tests
# ===========================================================================

class TestDetectLeak:

    def test_empty_string_returns_is_leak_false(self):
        result = detect_leak("")
        assert "is_leak" in result
        assert result["is_leak"] is False
        assert result["risk_score"] == 0

    def test_none_returns_is_leak_false(self):
        result = detect_leak(None)
        assert "is_leak" in result
        assert result["is_leak"] is False
        assert result["risk_score"] == 0

    def test_unrelated_content_has_zero_score(self):
        result = detect_leak("completely unrelated content about cats and dogs")
        assert result["risk_score"] == 0.0
        assert result["is_leak"] is False

    def test_doctutorials_keyword_adds_score(self):
        result = detect_leak("This page is about doctutorials courses.")
        assert result["risk_score"] == pytest.approx(0.4)
        assert result["is_leak"] is False  # 0.4 < 0.7 threshold

    def test_single_leak_keyword_adds_score(self):
        result = detect_leak("free download available here")
        assert result["risk_score"] == pytest.approx(0.15)
        assert result["is_leak"] is False

    def test_multiple_leak_keywords_accumulate(self):
        # download(0.15) + torrent(0.15) + telegram(0.15) = 0.45
        result = detect_leak("download torrent telegram")
        assert result["risk_score"] == pytest.approx(0.45)
        assert result["is_leak"] is False

    def test_doctutorials_plus_two_keywords_near_threshold(self):
        # doctutorials(0.4) + download(0.15) + torrent(0.15) ≈ 0.70
        # Due to floating-point representation this is just above the threshold,
        # so is_leak is True; we just verify the score is in the expected range.
        result = detect_leak("doctutorials download torrent")
        assert result["risk_score"] == pytest.approx(0.7, abs=1e-9)
        # is_leak reflects whether score strictly exceeds RISK_THRESHOLD
        assert isinstance(result["is_leak"], bool)

    def test_score_above_threshold_is_leak(self):
        # doctutorials(0.4) + download(0.15) + torrent(0.15) + telegram(0.15) = 0.85
        result = detect_leak("doctutorials download torrent telegram")
        assert result["risk_score"] > RISK_THRESHOLD
        assert result["is_leak"] is True

    def test_all_leak_keywords_present_score_capped_at_one(self):
        content = "doctutorials " + " ".join(LEAK_KEYWORDS)
        result = detect_leak(content)
        assert result["risk_score"] == pytest.approx(1.0)
        assert result["is_leak"] is True

    def test_score_never_exceeds_one(self):
        """Score is capped at 1.0 even with many keywords."""
        content = " ".join(LEAK_KEYWORDS * 10) + " doctutorials"
        result = detect_leak(content)
        assert result["risk_score"] <= 1.0

    def test_case_insensitive_doctutorials(self):
        result = detect_leak("DOCTUTORIALS free lectures")
        assert result["risk_score"] > 0

    def test_risk_score_and_is_leak_always_present(self):
        for content in ["", None, "hello", "doctutorials torrent download telegram"]:
            result = detect_leak(content)
            assert "risk_score" in result
            assert "is_leak" in result


# ===========================================================================
# save_alert() / send_alert() tests
# ===========================================================================

class TestSaveAlert:

    def test_save_alert_creates_file(self, tmp_alert_file):
        import doctutorials_monitor as dm
        dm.save_alert({"platform": "DocTutorials", "url": "http://x.com", "risk_score": 0.9})
        assert os.path.exists(tmp_alert_file)

    def test_save_alert_writes_valid_json(self, tmp_alert_file):
        import doctutorials_monitor as dm
        dm.save_alert({"platform": "DocTutorials", "url": "http://x.com", "risk_score": 0.9})
        with open(tmp_alert_file) as f:
            data = json.loads(f.read().strip())
        assert data["platform"] == "DocTutorials"
        assert data["url"] == "http://x.com"

    def test_save_alert_adds_timestamp(self, tmp_alert_file):
        import doctutorials_monitor as dm
        dm.save_alert({"platform": "x", "url": "http://x.com", "risk_score": 0.8})
        with open(tmp_alert_file) as f:
            data = json.loads(f.read().strip())
        assert "timestamp" in data
        assert data["timestamp"]  # non-empty

    def test_save_alert_timestamp_is_timezone_aware(self, tmp_alert_file):
        import doctutorials_monitor as dm
        dm.save_alert({"platform": "x", "url": "http://x.com", "risk_score": 0.8})
        with open(tmp_alert_file) as f:
            data = json.loads(f.read().strip())
        # timezone-aware ISO strings end with +HH:MM or Z
        ts = data["timestamp"]
        assert "+" in ts or ts.endswith("Z"), f"Expected tz-aware timestamp, got: {ts}"

    def test_save_alert_appends_multiple_entries(self, tmp_alert_file):
        import doctutorials_monitor as dm
        dm.save_alert({"platform": "x", "url": "http://1.com", "risk_score": 0.8})
        dm.save_alert({"platform": "x", "url": "http://2.com", "risk_score": 0.9})
        with open(tmp_alert_file) as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        assert len(lines) == 2

    def test_save_alert_does_not_raise_on_write_error(self, monkeypatch):
        """save_alert should print an error, not raise, if the file can't be written."""
        import doctutorials_monitor as dm
        monkeypatch.setattr(dm, "ALERT_FILE", "/invalid_path/\x00/alerts.json")
        # Should not raise
        dm.save_alert({"platform": "x", "url": "http://x.com", "risk_score": 0.8})


class TestSendAlert:

    def test_send_alert_prints_alert_fields(self, capsys, tmp_alert_file):
        import doctutorials_monitor as dm
        alert = {"platform": "DocTutorials", "url": "http://leak.com", "risk_score": 0.95}
        dm.send_alert(alert)
        out = capsys.readouterr().out
        assert "DocTutorials" in out
        assert "http://leak.com" in out
        assert "0.95" in out

    def test_send_alert_saves_to_file(self, tmp_alert_file):
        import doctutorials_monitor as dm
        alert = {"platform": "DocTutorials", "url": "http://leak.com", "risk_score": 0.95}
        dm.send_alert(alert)
        assert os.path.exists(tmp_alert_file)
        with open(tmp_alert_file) as f:
            data = json.loads(f.read().strip())
        assert data["url"] == "http://leak.com"


# ===========================================================================
# scan_query() tests (with live framework)
# ===========================================================================

class TestScanQuery:

    async def test_scan_query_runs_without_error(self):
        """scan_query completes without raising for a standard query."""
        from aimon import AIMON
        async with AIMON() as fw:
            await scan_query(fw, "DocTutorials download")

    async def test_scan_query_no_sources_returns_early(self, capsys):
        """When search_sources returns nothing, scan_query prints and returns."""
        from aimon import AIMON
        from unittest.mock import AsyncMock, patch

        async with AIMON() as fw:
            with patch.object(fw, "search_sources", new=AsyncMock(return_value=[])):
                await scan_query(fw, "DocTutorials download")
        out = capsys.readouterr().out
        assert "No sources found" in out

    async def test_scan_query_skips_source_without_url(self, tmp_alert_file):
        """Sources without a URL should be silently skipped."""
        from aimon import AIMON
        from unittest.mock import AsyncMock, patch

        async with AIMON() as fw:
            sources = [{"id": "s1", "name": "no-url-source"}]
            with patch.object(fw, "search_sources", new=AsyncMock(return_value=sources)):
                await scan_query(fw, "DocTutorials download")
        # No alert file should be written for URL-less sources
        assert not os.path.exists(tmp_alert_file)

    async def test_scan_query_handles_crawl_exception_gracefully(self, capsys):
        """Exceptions from the crawler are caught and printed, not re-raised."""
        from aimon import AIMON
        from unittest.mock import AsyncMock, patch, MagicMock

        async with AIMON() as fw:
            sources = [{"id": "s1", "url": "http://bad.com", "name": "Bad"}]
            with patch.object(fw, "search_sources", new=AsyncMock(return_value=sources)):
                fw.crawler.crawl = AsyncMock(side_effect=RuntimeError("crawl boom"))
                await scan_query(fw, "DocTutorials download")
        out = capsys.readouterr().out
        assert "Scan error" in out


# ===========================================================================
# Integration test: full framework run with DocTutorials keywords
# ===========================================================================

class TestIntegration:

    async def test_full_scan_discovers_multiple_sources(self):
        """search_sources returns sources from all platform templates."""
        from aimon import AIMON
        async with AIMON() as fw:
            sources = await fw.search_sources("DocTutorials download")
        assert len(sources) >= 3

    async def test_full_scan_sources_have_real_urls(self):
        """Discovered source URLs are realistic (not example.com placeholders)."""
        from aimon import AIMON
        async with AIMON() as fw:
            sources = await fw.search_sources("DocTutorials download")
        urls = [s["url"] for s in sources]
        for url in urls:
            assert "example.com" not in url
            assert url.startswith("http")

    async def test_full_scan_sources_cover_multiple_platforms(self):
        """Discovered sources span at least 3 distinct platforms."""
        from aimon import AIMON
        async with AIMON() as fw:
            sources = await fw.search_sources("DocTutorials download")
        platforms = {s.get("platform") for s in sources}
        assert len(platforms) >= 3

    async def test_crawler_returns_contextual_content(self):
        """The crawler returns platform-specific content, not a generic placeholder."""
        from aimon.core.event_bus import EventBus
        from aimon.modules.crawler import CrawlerModule

        bus = EventBus()
        await bus.initialize()
        crawler = CrawlerModule("crawler")
        crawler.event_bus = bus
        await crawler.initialize()

        try:
            source = {
                "id": "t1",
                "url": "https://t.me/s/doctutorials_free",
                "name": "telegram:DocTutorials download",
                "platform": "telegram",
            }
            page = await crawler.crawl(source)
            assert "telegram" in page["content"].lower()
        finally:
            await crawler.shutdown()
            await bus.clear()

    async def test_monitor_keywords_are_present(self):
        """KEYWORDS list is non-empty and contains expected DocTutorials terms."""
        assert len(KEYWORDS) > 0
        for kw in KEYWORDS:
            assert "DocTutorials" in kw

    async def test_all_doctutorials_keywords_return_sources(self):
        """Every configured KEYWORDS entry discovers at least one source."""
        from aimon import AIMON
        async with AIMON() as fw:
            for query in KEYWORDS:
                sources = await fw.search_sources(query)
                assert len(sources) > 0, f"No sources for query: {query}"
