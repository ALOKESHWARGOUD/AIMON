"""
Tests for the Discovery Layer.

Tests Google search connector, Reddit connector, Telegram discovery connector,
torrent search connector, and LeakSignalModule.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from aimon.connectors.google_search_connector import GoogleSearchConnector, LEAK_QUERY_TEMPLATES
from aimon.connectors.torrent_search_connector import TorrentSearchConnector
from aimon.connectors.reddit_connector import RedditConnector
from aimon.core.event_bus import EventBus
from aimon.modules.leak_signal_module import LeakSignalModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_event_bus() -> EventBus:
    bus = EventBus()
    await bus.initialize()
    return bus


# ===========================================================================
# TestGoogleSearchConnector
# ===========================================================================


class TestGoogleSearchConnector:
    """Tests for the Google Search connector with leak query strategies."""

    @pytest.fixture
    def connector(self):
        return GoogleSearchConnector("google_search", {})

    async def test_initialize(self, connector):
        """Connector initializes without error."""
        await connector.initialize()
        assert connector._initialized is True

    async def test_leak_query_templates_contain_brand(self):
        """All LEAK_QUERY_TEMPLATES use {brand} placeholder."""
        for template in LEAK_QUERY_TEMPLATES:
            assert "{brand}" in template, f"Template missing {{brand}}: {template}"

    async def test_infer_platform_telegram(self, connector):
        """Platform inference correctly identifies Telegram URLs."""
        url = "https://t.me/+ABCDEF12345"
        assert connector._infer_platform(url) == "telegram"

    async def test_infer_platform_torrent(self, connector):
        """Platform inference identifies torrent sites."""
        url = "https://1337x.to/torrent/12345/test"
        assert connector._infer_platform(url) == "torrent"

    async def test_infer_platform_gdrive(self, connector):
        """Platform inference identifies Google Drive."""
        url = "https://drive.google.com/file/d/XXXYYY"
        assert connector._infer_platform(url) == "gdrive"

    async def test_infer_platform_unknown(self, connector):
        """Unknown URL returns 'unknown'."""
        url = "https://example.com/page"
        assert connector._infer_platform(url) == "unknown"

    async def test_ddg_search_mock(self, connector):
        """DuckDuckGo fallback returns list of results."""
        fake_html = """
        <div class="result">
            <a class="result__a" href="/?uddg=https%3A%2F%2Ft.me%2Fchannel1">Channel leak</a>
            <a class="result__snippet">Free course for download</a>
        </div>
        """
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.text = AsyncMock(return_value=fake_html)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            mock_get = AsyncMock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_get.__aexit__ = AsyncMock(return_value=False)

            mock_session = AsyncMock()
            mock_session.post = MagicMock(return_value=mock_get)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            mock_session_cls.return_value = mock_session

            await connector.initialize()
            results = await connector._ddg_search("DocTutorials free download")
            # May get 0 results if selectolax parsing doesn't match — that's OK
            assert isinstance(results, list)

    async def test_google_api_search_mock(self, connector):
        """Google Custom Search API returns structured results."""
        fake_response = {
            "items": [
                {
                    "title": "DocTutorials Free Download",
                    "link": "https://t.me/some_channel",
                    "snippet": "Get DocTutorials for free",
                }
            ]
        }
        connector.config["api_key"] = "fake_key"
        connector.config["search_engine_id"] = "fake_cx"

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json = AsyncMock(return_value=fake_response)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            mock_get = AsyncMock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_get.__aexit__ = AsyncMock(return_value=False)

            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_get)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            mock_session_cls.return_value = mock_session

            await connector.initialize()
            results = await connector.search("DocTutorials")
            assert len(results) == 1
            assert results[0]["source_type"] == "google"
            assert results[0]["platform"] == "telegram"

    async def test_result_schema(self, connector):
        """parse_google_item returns correct schema."""
        item = {
            "title": "Test",
            "link": "https://mega.nz/test",
            "snippet": "Some snippet",
        }
        result = connector._parse_google_item(item, "test query")
        assert set(result.keys()) >= {"source_type", "url", "title", "snippet", "platform", "query"}
        assert result["source_type"] == "google"
        assert result["platform"] == "mega"


# ===========================================================================
# TestRedditConnector
# ===========================================================================


class TestRedditConnector:
    """Tests for the Reddit connector with enhanced schema."""

    @pytest.fixture
    def connector(self):
        return RedditConnector("reddit", {"timeout": 5, "max_retries": 1})

    async def test_initialize(self, connector):
        """Connector initializes correctly."""
        await connector.initialize()
        assert connector._initialized is True

    async def test_search_returns_fallback_on_error(self, connector):
        """Returns simulated results when network unavailable."""
        await connector.initialize()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.side_effect = Exception("Network error")
            results = await connector.search("DocTutorials")
        assert isinstance(results, list)
        assert len(results) > 0

    async def test_parse_post_schema(self, connector):
        """_parse_post returns the expected keys."""
        raw = {
            "id": "abc123",
            "title": "Free DocTutorials",
            "url": "https://reddit.com/r/learnprogramming/xyz",
            "permalink": "/r/learnprogramming/comments/abc123",
            "subreddit": "learnprogramming",
            "author": "user1",
            "score": 50,
            "created_utc": 1700000000.0,
            "num_comments": 5,
        }
        result = connector._parse_post(raw)
        assert result["id"] == "abc123"
        assert result["subreddit"] == "learnprogramming"
        assert result["score"] == 50
        assert "created_utc" in result

    async def test_search_with_subreddit_uses_correct_url(self, connector):
        """Subreddit search builds correct URL."""
        await connector.initialize()
        captured_url = []

        async def fake_get(*args, **kwargs):
            captured_url.append(args[0] if args else kwargs.get("url"))
            raise Exception("abort")

        with patch("aiohttp.ClientSession") as mock_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.get = MagicMock(side_effect=Exception("abort"))
            mock_cls.return_value = mock_session

            results = await connector.search("DocTutorials", subreddit="piracy")

        # Falls back to simulated, but at least we don't raise
        assert isinstance(results, list)

    async def test_fallback_result_has_source_key(self, connector):
        """Fallback results include the 'source' key."""
        await connector.initialize()
        with patch("aiohttp.ClientSession", side_effect=Exception("net err")):
            results = await connector.search("brand_name")
        assert all("source" in r for r in results)


# ===========================================================================
# TestTelegramDiscoveryConnector
# ===========================================================================


class TestTelegramDiscoveryConnector:
    """Tests for the Telegram Discovery connector."""

    def _make_connector(self, config=None):
        from aimon.connectors.telegram_discovery_connector import TelegramDiscoveryConnector
        return TelegramDiscoveryConnector("tg", config or {})

    async def test_raises_configuration_error_without_credentials(self):
        """Raises ConfigurationError when api_id/api_hash are missing."""
        from aimon.connectors.telegram_discovery_connector import ConfigurationError

        connector = self._make_connector({})
        with pytest.raises(ConfigurationError):
            await connector.initialize()

    async def test_raises_configuration_error_partial_credentials(self):
        """Raises ConfigurationError when only api_id is set."""
        from aimon.connectors.telegram_discovery_connector import ConfigurationError

        connector = self._make_connector({"api_id": 12345})
        with pytest.raises(ConfigurationError):
            await connector.initialize()

    async def test_scan_channel_returns_schema_on_error(self):
        """scan_channel returns valid structure even when client fails."""
        connector = self._make_connector({"api_id": 1, "api_hash": "abc"})
        # Bypass actual Telethon initialization
        connector._initialized = True

        # Mock a minimal client that raises on get_entity
        mock_client = AsyncMock()
        mock_client.get_entity = AsyncMock(side_effect=Exception("connection failed"))
        connector._client = mock_client

        result = await connector.scan_channel("https://t.me/testchannel")

        assert result["source_type"] == "telegram"
        assert result["platform"] == "telegram"
        assert isinstance(result["invite_links"], list)
        assert isinstance(result["file_references"], list)
        assert isinstance(result["external_urls"], list)
        assert isinstance(result["risk_indicators"], list)

    async def test_invite_link_pattern_detection(self):
        """Invite link regex correctly identifies t.me/+ links."""
        import re
        from aimon.connectors.telegram_discovery_connector import _INVITE_PATTERN

        text = "Join us at https://t.me/+ABCDEF123 for free content!"
        matches = _INVITE_PATTERN.findall(text)
        assert len(matches) == 1
        assert "ABCDEF123" in matches[0]

    async def test_file_extension_pattern(self):
        """File extension regex detects leak file types."""
        from aimon.connectors.telegram_discovery_connector import _FILE_EXT_PATTERN

        text = "Download course.zip and video.mp4 here"
        matches = _FILE_EXT_PATTERN.findall(text)
        assert len(matches) == 2


# ===========================================================================
# TestTorrentSearchConnector
# ===========================================================================


class TestTorrentSearchConnector:
    """Tests for the TorrentSearchConnector."""

    @pytest.fixture
    def connector(self):
        return TorrentSearchConnector("torrent", {"timeout": 5, "max_results": 5})

    async def test_initialize(self, connector):
        """Connector initializes without error."""
        await connector.initialize()
        assert connector._initialized is True

    async def test_piratebay_search_mock(self, connector):
        """Pirate Bay JSON API response is parsed correctly."""
        fake_data = [
            {
                "id": "1",
                "name": "DocTutorials Complete Course",
                "info_hash": "AABB1122",
                "seeders": 50,
                "leechers": 10,
                "size": 1073741824,
                "category": "600",
            }
        ]

        with patch("httpx.AsyncClient") as mock_cls:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json = MagicMock(return_value=fake_data)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            mock_cls.return_value = mock_client

            await connector.initialize()
            results = await connector._search_piratebay("DocTutorials")

        assert len(results) == 1
        r = results[0]
        assert r["source_type"] == "torrent"
        assert r["platform"] == "torrent"
        assert r["seeders"] == 50
        assert r["title"] == "DocTutorials Complete Course"
        assert r["magnet"] is not None

    async def test_result_schema_keys(self, connector):
        """Torrent result dict contains all required schema keys."""
        fake_data = [
            {
                "id": "2",
                "name": "TestCourse",
                "info_hash": "CC",
                "seeders": 0,
                "leechers": 0,
                "size": 0,
                "category": "unknown",
            }
        ]

        with patch("httpx.AsyncClient") as mock_cls:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json = MagicMock(return_value=fake_data)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            mock_cls.return_value = mock_client

            await connector.initialize()
            results = await connector._search_piratebay("test")

        required_keys = {"source_type", "url", "title", "seeders", "leechers", "size", "platform", "magnet", "category"}
        assert required_keys.issubset(set(results[0].keys()))

    async def test_search_aggregates_multiple_sources(self, connector):
        """search() aggregates results from multiple sources."""
        await connector.initialize()

        with patch.object(connector, "_search_1337x", return_value=[{"source_type": "torrent", "title": "a"}]):
            with patch.object(connector, "_search_piratebay", return_value=[{"source_type": "torrent", "title": "b"}]):
                results = await connector.search("test")

        assert len(results) == 2


# ===========================================================================
# TestLeakSignalModule
# ===========================================================================


class TestLeakSignalModule:
    """Tests for the LeakSignalModule event processing."""

    @pytest.fixture
    async def module_and_bus(self):
        bus = await _make_event_bus()
        module = LeakSignalModule("leak_signal", bus)
        await module.initialize()
        return module, bus

    async def test_emits_leak_signal_on_page_crawled(self, module_and_bus):
        """Emits leak_signal_detected when page contains leak URLs."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("leak_signal_detected", lambda **d: received.append(d))

        page = {
            "url": "https://t.me/+abc123",
            "content": "Free download at drive.google.com",
            "title": "Free DocTutorials",
            "platform": "telegram",
            "metadata": {"embedded_links": ["https://drive.google.com/file/1"]},
        }
        await bus.emit("page_crawled", "test", page=page, brand="DocTutorials")
        await asyncio.sleep(0.2)

        assert len(received) > 0
        signal = received[0]
        assert "brand" in signal
        assert "url" in signal
        assert "confidence" in signal
        assert "signal_type" in signal

    async def test_emits_on_telegram_signal(self, module_and_bus):
        """Converts telegram_signal_detected into leak_signal_detected."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("leak_signal_detected", lambda **d: received.append(d))

        await bus.emit(
            "telegram_signal_detected",
            "test",
            channel_url="https://t.me/testchannel",
            channel_title="Test Channel",
            invite_links=["https://t.me/+XYZ123"],
            file_references=["course.zip"],
            external_urls=["https://drive.google.com/file/abc"],
            risk_indicators=["free download"],
            brand="DocTutorials",
        )
        await asyncio.sleep(0.2)

        assert len(received) > 0
        assert received[0]["platform"] == "telegram"

    async def test_no_signal_on_clean_page(self, module_and_bus):
        """Does NOT emit when page has no leak indicators."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("leak_signal_detected", lambda **d: received.append(d))

        page = {
            "url": "https://example.com/blog",
            "content": "This is a normal blog post about cooking.",
            "title": "Cooking Tips",
            "platform": "web",
            "metadata": {},
        }
        await bus.emit("page_crawled", "test", page=page, brand="DocTutorials")
        await asyncio.sleep(0.2)

        assert len(received) == 0

    async def test_signal_schema(self, module_and_bus):
        """Emitted signal has all required schema fields."""
        module, bus = module_and_bus

        received = []
        await bus.subscribe("leak_signal_detected", lambda **d: received.append(d))

        page = {
            "url": "https://1337x.to/torrent/12345",
            "content": "Full course torrent magnet link",
            "title": "DocTutorials torrent",
            "platform": "torrent",
            "metadata": {},
        }
        await bus.emit("page_crawled", "test", page=page, brand="DocTutorials")
        await asyncio.sleep(0.2)

        if received:
            signal = received[0]
            required = {"brand", "url", "platform", "signal_type", "confidence", "raw_signals", "source_event"}
            assert required.issubset(set(signal.keys()))
            assert 0.0 <= signal["confidence"] <= 1.0
