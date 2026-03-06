"""
Tests for Storage and Connector Systems.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from aimon.storage import MemoryStorage, FileStorage
from aimon.connectors import (
    GoogleConnector,
    RedditConnector,
    TelegramConnector,
    TorrentConnector,
)


# Test MemoryStorage
@pytest.mark.asyncio
async def test_memory_storage_save_get():
    """Test save and get operations."""
    storage = MemoryStorage()
    await storage.initialize()
    
    success = await storage.save("key1", {"data": "value1"})
    assert success
    
    retrieved = await storage.get("key1")
    assert retrieved["data"] == "value1"


@pytest.mark.asyncio
async def test_memory_storage_delete():
    """Test delete operation."""
    storage = MemoryStorage()
    await storage.initialize()
    
    await storage.save("key1", {"data": "value1"})
    deleted = await storage.delete("key1")
    assert deleted
    
    retrieved = await storage.get("key1")
    assert retrieved is None


@pytest.mark.asyncio
async def test_memory_storage_query():
    """Test query operation."""
    storage = MemoryStorage()
    await storage.initialize()
    
    await storage.save("key1", {"type": "alert", "level": "high"})
    await storage.save("key2", {"type": "alert", "level": "low"})
    await storage.save("key3", {"type": "threat", "level": "high"})
    
    results = await storage.query({"type": "alert", "level": "high"})
    assert len(results) == 1


@pytest.mark.asyncio
async def test_memory_storage_count():
    """Test count operation."""
    storage = MemoryStorage()
    await storage.initialize()
    
    await storage.save("key1", "data1")
    await storage.save("key2", "data2")
    
    count = await storage.count()
    assert count == 2


# Test FileStorage
@pytest.mark.asyncio
async def test_file_storage_save_get():
    """Test file storage save and get."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(config={"storage_path": tmpdir})
        await storage.initialize()
        
        data = {"name": "test", "value": 123}
        success = await storage.save("test_key", data)
        assert success
        
        retrieved = await storage.get("test_key")
        assert retrieved["name"] == "test"
        assert retrieved["value"] == 123


@pytest.mark.asyncio
async def test_file_storage_delete():
    """Test file storage delete."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(config={"storage_path": tmpdir})
        await storage.initialize()
        
        await storage.save("key1", {"data": "value"})
        deleted = await storage.delete("key1")
        assert deleted
        
        retrieved = await storage.get("key1")
        assert retrieved is None


@pytest.mark.asyncio
async def test_file_storage_count():
    """Test file storage count."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(config={"storage_path": tmpdir})
        await storage.initialize()
        
        await storage.save("key1", "data1")
        await storage.save("key2", "data2")
        
        count = await storage.count()
        assert count == 2


# Test GoogleConnector
@pytest.mark.asyncio
async def test_google_connector_initialization():
    """Test Google connector initialization."""
    connector = GoogleConnector("google")
    await connector.initialize()
    
    assert connector._initialized


@pytest.mark.asyncio
async def test_google_connector_search():
    """Test Google connector search."""
    connector = GoogleConnector("google")
    await connector.initialize()
    
    results = await connector.search("test query")
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_google_connector_fetch():
    """Test Google connector fetch."""
    connector = GoogleConnector("google")
    await connector.initialize()
    
    result = await connector.fetch("https://example.com")
    assert result["status_code"] == 200


# Test RedditConnector
@pytest.mark.asyncio
async def test_reddit_connector_search():
    """Test Reddit connector search."""
    connector = RedditConnector("reddit")
    await connector.initialize()
    
    results = await connector.search("test query")
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_reddit_connector_fetch():
    """Test Reddit connector fetch."""
    connector = RedditConnector("reddit")
    await connector.initialize()
    
    result = await connector.fetch("https://reddit.com/r/test")
    assert result is not None


# Test TelegramConnector
@pytest.mark.asyncio
async def test_telegram_connector_search():
    """Test Telegram connector search."""
    connector = TelegramConnector("telegram")
    await connector.initialize()
    
    results = await connector.search("test query")
    assert isinstance(results, list)
    assert len(results) > 0


# Test TorrentConnector
@pytest.mark.asyncio
async def test_torrent_connector_search():
    """Test Torrent connector search."""
    connector = TorrentConnector("torrent")
    await connector.initialize()
    
    results = await connector.search("test query")
    assert isinstance(results, list)
    assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
