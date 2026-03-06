"""
SECTION 6 — DATABASE STORAGE TEST

Tests: save, get, delete, query, count
Uses SQLite-backed DatabaseStorage and MemoryStorage.
Tests TTL expiration.
Verifies JSON data serialization.
"""

import asyncio
import tempfile
import os
from pathlib import Path
import pytest

from aimon.storage.memory_storage import MemoryStorage
from aimon.storage.database_storage import DatabaseStorage
from aimon.storage.file_storage import FileStorage


# ---------------------------------------------------------------------------
# MemoryStorage — CRUD
# ---------------------------------------------------------------------------

async def test_memory_save_returns_true():
    storage = MemoryStorage()
    await storage.initialize()
    result = await storage.save("key1", {"val": 1})
    assert result is True


async def test_memory_get_returns_saved_data():
    storage = MemoryStorage()
    await storage.initialize()
    await storage.save("key1", {"val": 42})
    data = await storage.get("key1")
    assert data == {"val": 42}


async def test_memory_get_nonexistent_returns_none():
    storage = MemoryStorage()
    await storage.initialize()
    data = await storage.get("missing_key")
    assert data is None


async def test_memory_delete_returns_true():
    storage = MemoryStorage()
    await storage.initialize()
    await storage.save("key1", {"val": 1})
    result = await storage.delete("key1")
    assert result is True


async def test_memory_delete_then_get_returns_none():
    storage = MemoryStorage()
    await storage.initialize()
    await storage.save("key1", {"val": 1})
    await storage.delete("key1")
    data = await storage.get("key1")
    assert data is None


async def test_memory_query_matching_filter():
    storage = MemoryStorage()
    await storage.initialize()
    await storage.save("k1", {"type": "alert", "level": "high"})
    await storage.save("k2", {"type": "alert", "level": "low"})
    await storage.save("k3", {"type": "threat", "level": "high"})

    results = await storage.query({"type": "alert", "level": "high"})
    assert len(results) == 1


async def test_memory_query_no_match_returns_empty():
    storage = MemoryStorage()
    await storage.initialize()
    await storage.save("k1", {"type": "alert"})

    results = await storage.query({"type": "nonexistent"})
    assert results == []


async def test_memory_count_correct():
    storage = MemoryStorage()
    await storage.initialize()
    await storage.save("k1", "data1")
    await storage.save("k2", "data2")
    count = await storage.count()
    assert count == 2


async def test_memory_count_decrements_after_delete():
    storage = MemoryStorage()
    await storage.initialize()
    await storage.save("k1", "data1")
    await storage.save("k2", "data2")
    await storage.delete("k1")
    count = await storage.count()
    assert count == 1


async def test_memory_complex_json_data():
    """Complex nested JSON structures should round-trip correctly."""
    storage = MemoryStorage()
    await storage.initialize()
    data = {
        "nested": {"a": 1, "b": [1, 2, 3]},
        "unicode": "hello 世界 🎉",
        "list": [{"x": 1}, {"x": 2}],
    }
    await storage.save("complex", data)
    retrieved = await storage.get("complex")
    assert retrieved == data


async def test_memory_ttl_expiration():
    """Items with TTL=1 should expire after ~1 second."""
    storage = MemoryStorage()
    await storage.initialize()
    await storage.save("ttl_key", {"val": "expires"}, ttl=1)

    # Should be there immediately
    data = await storage.get("ttl_key")
    assert data is not None

    # Should be gone after TTL expires
    await asyncio.sleep(1.1)
    data = await storage.get("ttl_key")
    assert data is None


# ---------------------------------------------------------------------------
# DatabaseStorage — SQLite
# ---------------------------------------------------------------------------

async def test_database_storage_initializes():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_aimon.db")
        storage = DatabaseStorage(config={"database_url": f"sqlite+aiosqlite:///{db_path}"})
        await storage.initialize()
        assert storage._engine is not None
        await storage.shutdown()


async def test_database_save_returns_true():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        storage = DatabaseStorage(config={"database_url": f"sqlite+aiosqlite:///{db_path}"})
        await storage.initialize()
        result = await storage.save("key1", {"val": 1})
        assert result is True
        await storage.shutdown()


async def test_database_get_returns_saved_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        storage = DatabaseStorage(config={"database_url": f"sqlite+aiosqlite:///{db_path}"})
        await storage.initialize()
        await storage.save("key1", {"val": 99})
        data = await storage.get("key1")
        assert data == {"val": 99}
        await storage.shutdown()


async def test_database_delete_returns_true():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        storage = DatabaseStorage(config={"database_url": f"sqlite+aiosqlite:///{db_path}"})
        await storage.initialize()
        await storage.save("key1", {"val": 1})
        result = await storage.delete("key1")
        assert result is True
        await storage.shutdown()


async def test_database_get_after_delete_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        storage = DatabaseStorage(config={"database_url": f"sqlite+aiosqlite:///{db_path}"})
        await storage.initialize()
        await storage.save("key1", {"val": 1})
        await storage.delete("key1")
        data = await storage.get("key1")
        assert data is None
        await storage.shutdown()


async def test_database_count_reflects_rows():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        storage = DatabaseStorage(config={"database_url": f"sqlite+aiosqlite:///{db_path}"})
        await storage.initialize()
        await storage.save("k1", {"a": 1})
        await storage.save("k2", {"a": 2})
        count = await storage.count()
        assert count == 2
        await storage.shutdown()


# ---------------------------------------------------------------------------
# FileStorage — full CRUD + JSON persistence
# ---------------------------------------------------------------------------

async def test_file_storage_save_get():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(config={"storage_path": tmpdir})
        await storage.initialize()

        await storage.save("key1", {"name": "test", "value": 123})
        data = await storage.get("key1")
        assert data["name"] == "test"
        assert data["value"] == 123


async def test_file_storage_delete():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(config={"storage_path": tmpdir})
        await storage.initialize()

        await storage.save("k1", {"x": 1})
        deleted = await storage.delete("k1")
        assert deleted is True
        data = await storage.get("k1")
        assert data is None


async def test_file_storage_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(config={"storage_path": tmpdir})
        await storage.initialize()

        await storage.save("k1", "data1")
        await storage.save("k2", "data2")
        count = await storage.count()
        assert count == 2


async def test_file_storage_json_persistence():
    """Data saved to file should survive re-initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage1 = FileStorage(config={"storage_path": tmpdir})
        await storage1.initialize()
        await storage1.save("persist_key", {"persistent": True})

        # Re-initialize from same directory
        storage2 = FileStorage(config={"storage_path": tmpdir})
        await storage2.initialize()
        data = await storage2.get("persist_key")
        assert data == {"persistent": True}
