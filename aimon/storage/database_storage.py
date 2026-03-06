"""
Database Storage - Async SQL database storage backend.

Uses SQLAlchemy asyncio with a single key-value table.
Supports SQLite (dev) and PostgreSQL (production) via the same code path.
"""

import json
import time
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from aimon.storage.base import StorageBackend

logger = structlog.get_logger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS aimon_kv (
    key TEXT PRIMARY KEY,
    data TEXT,
    expires_at REAL
)
"""


class DatabaseStorage(StorageBackend):
    """
    Async SQL database storage backend.

    Uses a single ``aimon_kv`` table with key/data/expires_at columns.
    Supports SQLite (``sqlite+aiosqlite://``) and PostgreSQL
    (``postgresql+asyncpg://``) via the same code path.

    Config keys:
        database_url: SQLAlchemy async URL (default: sqlite+aiosqlite:///aimon.db)
    """

    def __init__(self, name: str = "database", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        self.database_url: str = (
            (config or {}).get("database_url", "sqlite+aiosqlite:///aimon.db")
        )
        self._engine = None
        self._session_factory = None

    async def initialize(self) -> None:
        """Initialize the engine and create the table."""
        try:
            self._engine = create_async_engine(self.database_url, echo=False)
            self._session_factory = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )
            async with self._engine.begin() as conn:
                await conn.execute(text(_CREATE_TABLE_SQL))
            await super().initialize()
            await logger.ainfo("database_storage_initialized", url=self.database_url)
        except Exception as e:
            await logger.aerror("database_storage_init_failed", error=str(e))
            raise

    async def save(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Upsert a key-value pair.  Uses INSERT … ON CONFLICT(key) DO UPDATE."""
        try:
            expires_at = time.time() + ttl if ttl is not None else None
            serialized = json.dumps(data)
            upsert_sql = text(
                "INSERT INTO aimon_kv (key, data, expires_at) VALUES (:key, :data, :expires_at) "
                "ON CONFLICT(key) DO UPDATE SET data = excluded.data, expires_at = excluded.expires_at"
            )
            async with self._session_factory() as session:
                await session.execute(
                    upsert_sql,
                    {"key": key, "data": serialized, "expires_at": expires_at},
                )
                await session.commit()
            await logger.adebug("database_save", key=key)
            return True
        except Exception as e:
            await logger.aerror("database_save_failed", key=key, error=str(e))
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value; returns None if not found or expired."""
        try:
            async with self._session_factory() as session:
                row = (
                    await session.execute(
                        text("SELECT data, expires_at FROM aimon_kv WHERE key = :key"),
                        {"key": key},
                    )
                ).fetchone()

            if row is None:
                return None

            data_str, expires_at = row
            if expires_at is not None and time.time() > expires_at:
                # Delete expired entry asynchronously
                await self.delete(key)
                return None

            await logger.adebug("database_get", key=key)
            return json.loads(data_str)
        except Exception as e:
            await logger.aerror("database_get_failed", key=key, error=str(e))
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key-value pair."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    text("DELETE FROM aimon_kv WHERE key = :key"), {"key": key}
                )
                await session.commit()
            deleted = result.rowcount > 0
            await logger.adebug("database_delete", key=key, deleted=deleted)
            return deleted
        except Exception as e:
            await logger.aerror("database_delete_failed", key=key, error=str(e))
            return False

    async def query(self, query_filter: Dict[str, Any]) -> List[Any]:
        """
        Linear scan: load all rows, JSON-parse each, return those matching
        every key/value pair in *query_filter*.
        """
        try:
            async with self._session_factory() as session:
                rows = (
                    await session.execute(text("SELECT data, expires_at FROM aimon_kv"))
                ).fetchall()

            now = time.time()
            results = []
            for data_str, expires_at in rows:
                if expires_at is not None and now > expires_at:
                    continue
                try:
                    value = json.loads(data_str)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(value, dict):
                    continue
                if all(value.get(k) == v for k, v in query_filter.items()):
                    results.append(value)

            await logger.adebug("database_query", results=len(results))
            return results
        except Exception as e:
            await logger.aerror("database_query_failed", error=str(e))
            return []

    async def count(self) -> int:
        """Return the number of non-expired rows."""
        try:
            async with self._session_factory() as session:
                row = (
                    await session.execute(
                        text(
                            "SELECT COUNT(*) FROM aimon_kv "
                            "WHERE expires_at IS NULL OR expires_at > :now"
                        ),
                        {"now": time.time()},
                    )
                ).fetchone()
            return row[0] if row else 0
        except Exception as e:
            await logger.aerror("database_count_failed", error=str(e))
            return 0

    async def shutdown(self) -> None:
        """Dispose the async engine."""
        if self._engine is not None:
            await self._engine.dispose()
        await super().shutdown()
        await logger.ainfo("database_storage_shutdown")
