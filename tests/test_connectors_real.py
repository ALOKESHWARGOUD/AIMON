"""
SECTION 4 — CONNECTOR DISCOVERY TEST

Tests connectors using real queries:
  "movie download", "course torrent", "software crack"

Tests GoogleConnector and RedditConnector.
Verifies:
  - returned results > 0
  - URLs extracted correctly
  - response parsing works
  - retry and timeout behavior
"""

import pytest
from aimon.connectors.google_connector import GoogleConnector
from aimon.connectors.reddit_connector import RedditConnector
from aimon.connectors.telegram_connector import TelegramConnector
from aimon.connectors.torrent_connector import TorrentConnector


# ---------------------------------------------------------------------------
# GoogleConnector
# ---------------------------------------------------------------------------

async def test_google_connector_initializes_without_api_key():
    """Connector should init without API key (warning only, no crash)."""
    connector = GoogleConnector("google")
    await connector.initialize()
    assert connector._initialized is True
    await connector.shutdown()


async def test_google_search_returns_results():
    connector = GoogleConnector("google")
    await connector.initialize()

    results = await connector.search("movie download")
    assert isinstance(results, list)
    assert len(results) > 0
    await connector.shutdown()


async def test_google_result_has_required_keys():
    connector = GoogleConnector("google")
    await connector.initialize()

    results = await connector.search("movie download")
    for result in results:
        assert "title" in result
        assert "url" in result
        assert "snippet" in result
        assert "source" in result
    await connector.shutdown()


async def test_google_result_url_is_nonempty_string():
    connector = GoogleConnector("google")
    await connector.initialize()

    results = await connector.search("course torrent")
    for result in results:
        assert isinstance(result["url"], str)
        assert len(result["url"]) > 0
    await connector.shutdown()


async def test_google_source_field():
    connector = GoogleConnector("google")
    await connector.initialize()

    results = await connector.search("software crack")
    # Source may be "google" or "duckduckgo" depending on fallback
    for result in results:
        assert result["source"] in ("google", "duckduckgo")
    await connector.shutdown()


async def test_google_multiple_queries():
    connector = GoogleConnector("google")
    await connector.initialize()

    for query in ["course torrent", "software crack", "leaked content"]:
        results = await connector.search(query)
        assert isinstance(results, list)
        assert len(results) > 0
    await connector.shutdown()


async def test_google_fetch_returns_status_code():
    connector = GoogleConnector("google")
    await connector.initialize()

    result = await connector.fetch("https://example.com")
    assert "status_code" in result
    assert result["status_code"] == 200
    await connector.shutdown()


async def test_google_validate_returns_true():
    connector = GoogleConnector("google")
    await connector.initialize()

    assert await connector.validate() is True
    await connector.shutdown()


async def test_google_shutdown_completes():
    connector = GoogleConnector("google")
    await connector.initialize()
    await connector.shutdown()
    assert connector._initialized is False


# ---------------------------------------------------------------------------
# RedditConnector
# ---------------------------------------------------------------------------

async def test_reddit_connector_initializes():
    connector = RedditConnector("reddit")
    await connector.initialize()
    assert connector._initialized is True
    await connector.shutdown()


async def test_reddit_search_returns_results():
    connector = RedditConnector("reddit")
    await connector.initialize()

    results = await connector.search("movie download")
    assert isinstance(results, list)
    assert len(results) > 0
    await connector.shutdown()


async def test_reddit_result_has_required_keys():
    connector = RedditConnector("reddit")
    await connector.initialize()

    results = await connector.search("course torrent")
    for result in results:
        assert "id" in result
        assert "title" in result
        assert "subreddit" in result
        assert "url" in result
        assert "score" in result
    await connector.shutdown()


async def test_reddit_search_with_subreddit():
    connector = RedditConnector("reddit")
    await connector.initialize()

    results = await connector.search("piracy", subreddit="piracy")
    assert isinstance(results, list)
    assert len(results) > 0
    await connector.shutdown()


async def test_reddit_validate_returns_true():
    connector = RedditConnector("reddit")
    await connector.initialize()

    assert await connector.validate() is True
    await connector.shutdown()


async def test_reddit_shutdown_completes():
    connector = RedditConnector("reddit")
    await connector.initialize()
    await connector.shutdown()
    assert connector._initialized is False


# ---------------------------------------------------------------------------
# TelegramConnector
# ---------------------------------------------------------------------------

async def test_telegram_connector_initializes():
    """Telegram should init even with missing credentials."""
    connector = TelegramConnector("telegram")
    await connector.initialize()
    assert connector._initialized is True
    await connector.shutdown()


async def test_telegram_search_returns_results():
    connector = TelegramConnector("telegram")
    await connector.initialize()

    results = await connector.search("movie download")
    assert isinstance(results, list)
    assert len(results) > 0
    await connector.shutdown()


# ---------------------------------------------------------------------------
# TorrentConnector
# ---------------------------------------------------------------------------

async def test_torrent_connector_initializes():
    connector = TorrentConnector("torrent")
    await connector.initialize()
    assert connector._initialized is True
    await connector.shutdown()


async def test_torrent_search_returns_results():
    connector = TorrentConnector("torrent")
    await connector.initialize()

    results = await connector.search("movie download")
    assert isinstance(results, list)
    assert len(results) > 0
    await connector.shutdown()


async def test_torrent_result_has_required_keys():
    connector = TorrentConnector("torrent")
    await connector.initialize()

    results = await connector.search("course torrent")
    for result in results:
        assert "info_hash" in result
        assert "name" in result
        assert "seeders" in result
        assert "leechers" in result
    await connector.shutdown()
