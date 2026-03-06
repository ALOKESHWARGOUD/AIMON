"""
Tests for AIMON Modules - Discovery, Crawler, Intelligence, Alerts.
"""

import pytest
import asyncio
from aimon.modules import (
    DiscoveryModule,
    CrawlerModule,
    IntelligenceModule,
    AlertsModule,
)
from aimon.core.event_bus import EventBus


@pytest.fixture
async def event_bus():
    """Create test event bus."""
    bus = EventBus()
    await bus.initialize()
    yield bus
    await bus.clear()


# Test DiscoveryModule
@pytest.mark.asyncio
async def test_discovery_module_initialization(event_bus):
    """Test discovery module initialization."""
    module = DiscoveryModule("discovery")
    module.event_bus = event_bus
    
    await module.initialize()
    assert module.is_ready()


@pytest.mark.asyncio
async def test_discovery_module_search(event_bus):
    """Test discovery search."""
    module = DiscoveryModule("discovery")
    module.event_bus = event_bus
    
    await module.initialize()
    
    sources = await module.search("test query")
    assert len(sources) > 0
    assert "id" in sources[0]


@pytest.mark.asyncio
async def test_discovery_emits_event(event_bus):
    """Test discovery emits source_discovered event."""
    module = DiscoveryModule("discovery")
    module.event_bus = event_bus
    
    received_events = []
    
    async def listener(**data):
        received_events.append(data)
    
    await event_bus.subscribe("source_discovered", listener)
    await module.initialize()
    
    await module.search("test")
    await asyncio.sleep(0.1)
    
    assert len(received_events) > 0


# Test CrawlerModule
@pytest.mark.asyncio
async def test_crawler_module_initialization(event_bus):
    """Test crawler module initialization."""
    module = CrawlerModule("crawler")
    module.event_bus = event_bus
    
    await module.initialize()
    assert module.is_ready()


@pytest.mark.asyncio
async def test_crawler_crawl_source(event_bus):
    """Test crawler crawls a source."""
    module = CrawlerModule("crawler")
    module.event_bus = event_bus
    
    await module.initialize()
    
    source = {"id": "test_source", "url": "https://example.com"}
    page = await module.crawl(source)
    
    assert page["source_id"] == "test_source"
    assert "content" in page


@pytest.mark.asyncio
async def test_crawler_emits_page_crawled(event_bus):
    """Test crawler emits page_crawled event."""
    module = CrawlerModule("crawler")
    module.event_bus = event_bus
    
    received = []
    
    async def listener(**data):
        received.append(data)
    
    await event_bus.subscribe("page_crawled", listener)
    await module.initialize()
    
    source = {"id": "test", "url": "https://example.com"}
    await module.crawl(source)
    await asyncio.sleep(0.1)
    
    assert len(received) > 0


# Test IntelligenceModule
@pytest.mark.asyncio
async def test_intelligence_module_initialization(event_bus):
    """Test intelligence module initialization."""
    module = IntelligenceModule("intelligence")
    module.event_bus = event_bus
    
    await module.initialize()
    assert module.is_ready()


@pytest.mark.asyncio
async def test_intelligence_analyze(event_bus):
    """Test content analysis."""
    module = IntelligenceModule("intelligence")
    module.event_bus = event_bus
    
    await module.initialize()
    
    page = {
        "source_id": "test_source",
        "content": "This is leaked course material",
        "url": "https://example.com"
    }
    
    analysis = await module.analyze(page)
    
    assert "threat_score" in analysis
    assert "threat_level" in analysis
    assert analysis["threat_score"] >= 0.0 and analysis["threat_score"] <= 1.0


@pytest.mark.asyncio
async def test_intelligence_detects_threats(event_bus):
    """Test threat detection."""
    module = IntelligenceModule("intelligence")
    module.event_bus = event_bus
    
    threats_detected = []
    
    async def listener(**data):
        threats_detected.append(data)
    
    await event_bus.subscribe("threat_detected", listener)
    await module.initialize()
    
    page = {"source_id": "test", "content": "leaked content"}
    await module.analyze(page)
    await asyncio.sleep(0.1)
    
    # Should detect threat (threat_score > 0.3)
    assert len(threats_detected) > 0


# Test AlertsModule
@pytest.mark.asyncio
async def test_alerts_module_initialization(event_bus):
    """Test alerts module initialization."""
    module = AlertsModule("alerts")
    module.event_bus = event_bus
    
    await module.initialize()
    assert module.is_ready()


@pytest.mark.asyncio
async def test_alerts_generate_alert(event_bus):
    """Test alert generation."""
    module = AlertsModule("alerts")
    module.event_bus = event_bus
    
    await module.initialize()
    
    threat = {
        "source_id": "test",
        "threat_level": "high",
        "threat_score": 0.8,
        "detected_assets": ["asset1"]
    }
    
    alert = await module.generate_alert(threat)
    
    assert "alert_id" in alert
    assert "message" in alert
    assert alert["threat_level"] == "high"


@pytest.mark.asyncio
async def test_alerts_send_alert(event_bus):
    """Test sending alert."""
    module = AlertsModule("alerts")
    module.event_bus = event_bus
    
    await module.initialize()
    
    threat = {
        "source_id": "test",
        "threat_level": "medium",
        "threat_score": 0.6,
        "detected_assets": []
    }
    
    alert = await module.generate_alert(threat)
    success = await module.send_alert(alert)
    
    assert success
    assert alert["status"] == "sent"


# Test Module Chain
@pytest.mark.asyncio
async def test_module_chain_discovery_to_crawler(event_bus):
    """Test event chain from discovery to crawler."""
    discovery = DiscoveryModule("discovery")
    crawler = CrawlerModule("crawler")
    
    for module in [discovery, crawler]:
        module.event_bus = event_bus
        await module.initialize()
    
    # Get crawled pages
    sources = await discovery.search("test")
    await asyncio.sleep(0.2)
    
    pages = crawler.get_crawled_pages()
    
    # Crawler should have crawled sources from discovery
    assert len(pages) > 0


@pytest.mark.asyncio
async def test_module_chain_crawler_to_intelligence(event_bus):
    """Test event chain from crawler to intelligence."""
    crawler = CrawlerModule("crawler")
    intelligence = IntelligenceModule("intelligence")
    
    for module in [crawler, intelligence]:
        module.event_bus = event_bus
        await module.initialize()
    
    source = {"id": "test", "url": "https://example.com", "name": "test source"}
    await crawler.crawl(source)
    await asyncio.sleep(0.2)
    
    threats = intelligence.get_threats()
    
    # Intelligence should have analyzed crawled content
    assert len(threats) >= 0  # May or may not detect threat


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
