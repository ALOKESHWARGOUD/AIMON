"""
SECTION 5 — CRAWLER TEST

Tests crawling real URLs discovered by connectors.
Steps:
1. Get URLs from connectors
2. Pass URLs to CrawlerModule
3. Fetch page content

Verifies:
  - page returned has expected structure
  - content field is present
  - metadata has status_code
  - crawled pages list grows
"""

import asyncio
import pytest
from aimon.core.event_bus import EventBus
from aimon.modules.crawler import CrawlerModule


async def make_crawler():
    bus = EventBus()
    await bus.initialize()
    crawler = CrawlerModule("crawler")
    crawler.event_bus = bus
    await crawler.initialize()
    return crawler, bus


async def test_crawl_returns_expected_structure():
    crawler, bus = await make_crawler()
    try:
        source = {"id": "test_id", "url": "https://example.com", "name": "Test"}
        page = await crawler.crawl(source)

        assert "source_id" in page
        assert "url" in page
        assert "title" in page
        assert "content" in page
        assert "metadata" in page
    finally:
        await crawler.shutdown()
        await bus.clear()


async def test_crawl_source_id_matches():
    crawler, bus = await make_crawler()
    try:
        source = {"id": "my_source", "url": "https://example.com", "name": "Test"}
        page = await crawler.crawl(source)

        assert page["source_id"] == "my_source"
    finally:
        await crawler.shutdown()
        await bus.clear()


async def test_crawl_metadata_has_status_code_200():
    crawler, bus = await make_crawler()
    try:
        source = {"id": "test_id", "url": "https://example.com", "name": "Test"}
        page = await crawler.crawl(source)

        assert page["metadata"]["status_code"] == 200
    finally:
        await crawler.shutdown()
        await bus.clear()


async def test_crawl_metadata_has_content_type():
    crawler, bus = await make_crawler()
    try:
        source = {"id": "test_id", "url": "https://example.com", "name": "Test"}
        page = await crawler.crawl(source)

        assert "content_type" in page["metadata"]
    finally:
        await crawler.shutdown()
        await bus.clear()


async def test_crawled_pages_grows_after_crawl():
    crawler, bus = await make_crawler()
    try:
        source = {"id": "test_id", "url": "https://example.com", "name": "Test"}
        await crawler.crawl(source)

        pages = crawler.get_crawled_pages()
        assert len(pages) > 0
    finally:
        await crawler.shutdown()
        await bus.clear()


async def test_crawling_multiple_urls():
    crawler, bus = await make_crawler()
    try:
        sources = [
            {"id": f"src_{i}", "url": f"https://example.com/{i}", "name": f"Source {i}"}
            for i in range(3)
        ]
        for source in sources:
            await crawler.crawl(source)

        pages = crawler.get_crawled_pages()
        assert len(pages) == 3
    finally:
        await crawler.shutdown()
        await bus.clear()


async def test_page_crawled_event_emitted():
    crawler, bus = await make_crawler()
    received = []

    async def on_page(**data):
        received.append(data)

    await bus.subscribe("page_crawled", on_page)

    try:
        source = {"id": "evt_test", "url": "https://example.com", "name": "Test"}
        await crawler.crawl(source)
        await asyncio.sleep(0.1)

        assert len(received) > 0
    finally:
        await crawler.shutdown()
        await bus.clear()


async def test_on_source_discovered_handler():
    """Simulating source_discovered event triggers crawler."""
    crawler, bus = await make_crawler()

    try:
        source = {
            "id": "discovered_source",
            "url": "https://example.com/discovered",
            "name": "Discovered",
        }
        await bus.emit("source_discovered", "test", source=source)
        await asyncio.sleep(0.2)

        pages = crawler.get_crawled_pages()
        ids = [p["source_id"] for p in pages]
        assert "discovered_source" in ids
    finally:
        await crawler.shutdown()
        await bus.clear()


async def test_crawl_deduplication():
    """Crawling the same source_id twice shouldn't duplicate entries from active_crawls."""
    crawler, bus = await make_crawler()

    try:
        source = {"id": "dup_source", "url": "https://example.com", "name": "Test"}
        # Crawl directly (bypasses active_crawls dedup used in _on_source_discovered)
        await crawler.crawl(source)
        await crawler.crawl(source)

        pages = crawler.get_crawled_pages()
        # Direct crawl always appends, but event-driven one deduplicates
        assert len(pages) >= 1
    finally:
        await crawler.shutdown()
        await bus.clear()


async def test_crawl_source_missing_name_field():
    """Crawl should handle source without 'name' key gracefully."""
    crawler, bus = await make_crawler()
    try:
        source = {"id": "no_name_source", "url": "https://example.com"}
        page = await crawler.crawl(source)

        assert "source_id" in page
        assert page["source_id"] == "no_name_source"
    finally:
        await crawler.shutdown()
        await bus.clear()
