"""
PostgreSQL Storage Backend - Async storage via SQLAlchemy + asyncpg.

Stores leaks and sources in a PostgreSQL database.

Config keys:
    database_url  SQLAlchemy URL, e.g.
                  ``postgresql+asyncpg://user:pass@localhost/aimon``
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from aimon.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class PostgresStorage(StorageBackend):
    """
    PostgreSQL-backed storage using SQLAlchemy async engine.

    Schema:
        leaks   — detected leak records
        sources — discovered source records
    """

    def __init__(
        self, name: str = "postgres", config: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(name, config)
        self._engine: Any = None
        self._session_factory: Any = None

    # ------------------------------------------------------------------
    # StorageBackend interface
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create engine, session factory, and ensure tables exist."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy import MetaData, Table, Column, String, Float, DateTime, JSON, text

            db_url = self.config.get("database_url", "")
            if not db_url:
                raise ValueError(
                    "PostgresStorage requires 'database_url' in config. "
                    "Example: postgresql+asyncpg://user:pass@localhost/aimon"
                )

            self._engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
            self._session_factory = sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )

            await self._create_tables()
            await super().initialize()
            await logger.ainfo("postgres_storage_initialized", url=db_url.split("@")[-1])

        except ImportError as exc:
            raise ImportError(
                "sqlalchemy[asyncio] and asyncpg must be installed. "
                "Install with: pip install 'aimon[postgres]'"
            ) from exc

    async def save(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Persist *data* under *key*.

        The key prefix determines the target table:
        * ``leak:``   → ``leaks`` table
        * ``source:`` → ``sources`` table
        * otherwise   → generic key-value in ``leaks`` with sentinel type
        """
        try:
            from sqlalchemy import text

            async with self._session_factory() as session:
                if isinstance(data, dict):
                    if key.startswith("source:"):
                        await session.execute(
                            text(
                                "INSERT INTO sources (id, source_type, url, platform, "
                                "discovered_at, metadata) VALUES (:id, :source_type, :url, "
                                ":platform, :discovered_at, :metadata) "
                                "ON CONFLICT (id) DO UPDATE SET metadata = EXCLUDED.metadata"
                            ),
                            {
                                "id": key,
                                "source_type": data.get("source_type", ""),
                                "url": data.get("url", ""),
                                "platform": data.get("platform", ""),
                                "discovered_at": datetime.utcnow().isoformat(),
                                "metadata": json.dumps(data),
                            },
                        )
                    else:
                        await session.execute(
                            text(
                                "INSERT INTO leaks (id, brand, url, platform, risk_score, "
                                "risk_level, detected_at, signals) VALUES (:id, :brand, :url, "
                                ":platform, :risk_score, :risk_level, :detected_at, :signals) "
                                "ON CONFLICT (id) DO UPDATE SET risk_score = EXCLUDED.risk_score, "
                                "risk_level = EXCLUDED.risk_level"
                            ),
                            {
                                "id": key,
                                "brand": data.get("brand", ""),
                                "url": data.get("url", ""),
                                "platform": data.get("platform", ""),
                                "risk_score": float(data.get("risk_score", 0.0)),
                                "risk_level": data.get("risk_level", "low"),
                                "detected_at": datetime.utcnow().isoformat(),
                                "signals": json.dumps(data.get("signals", [])),
                            },
                        )
                await session.commit()
            return True
        except Exception as exc:
            await logger.aerror("postgres_save_failed", key=key, error=str(exc))
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a record by *key*."""
        try:
            from sqlalchemy import text

            table = "sources" if key.startswith("source:") else "leaks"
            async with self._session_factory() as session:
                result = await session.execute(
                    text(f"SELECT * FROM {table} WHERE id = :id"), {"id": key}
                )
                row = result.mappings().one_or_none()
                return dict(row) if row else None
        except Exception as exc:
            await logger.aerror("postgres_get_failed", key=key, error=str(exc))
            return None

    async def delete(self, key: str) -> bool:
        """Delete a record by *key*."""
        try:
            from sqlalchemy import text

            table = "sources" if key.startswith("source:") else "leaks"
            async with self._session_factory() as session:
                await session.execute(
                    text(f"DELETE FROM {table} WHERE id = :id"), {"id": key}
                )
                await session.commit()
            return True
        except Exception as exc:
            await logger.aerror("postgres_delete_failed", key=key, error=str(exc))
            return False

    async def query(self, query_filter: Dict[str, Any]) -> List[Any]:
        """Query leaks by filter (simple equality match)."""
        try:
            from sqlalchemy import text

            table = query_filter.pop("_table", "leaks")
            conditions = " AND ".join(
                f"{col} = :{col}" for col in query_filter
            )
            where = f"WHERE {conditions}" if conditions else ""
            async with self._session_factory() as session:
                result = await session.execute(
                    text(f"SELECT * FROM {table} {where} LIMIT 1000"),
                    query_filter,
                )
                return [dict(row) for row in result.mappings()]
        except Exception as exc:
            await logger.aerror("postgres_query_failed", error=str(exc))
            return []

    async def count(self) -> int:
        """Return total count across both tables."""
        try:
            from sqlalchemy import text

            async with self._session_factory() as session:
                r1 = await session.execute(text("SELECT COUNT(*) FROM leaks"))
                r2 = await session.execute(text("SELECT COUNT(*) FROM sources"))
                return (r1.scalar() or 0) + (r2.scalar() or 0)
        except Exception as exc:
            await logger.aerror("postgres_count_failed", error=str(exc))
            return 0

    async def shutdown(self) -> None:
        """Close the async engine."""
        if self._engine:
            await self._engine.dispose()
        await super().shutdown()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def _create_tables(self) -> None:
        """Ensure the schema tables exist."""
        from sqlalchemy import text

        create_leaks = """
            CREATE TABLE IF NOT EXISTS leaks (
                id          TEXT PRIMARY KEY,
                brand       TEXT,
                url         TEXT,
                platform    TEXT,
                risk_score  FLOAT,
                risk_level  TEXT,
                detected_at TEXT,
                signals     TEXT
            )
        """
        create_sources = """
            CREATE TABLE IF NOT EXISTS sources (
                id            TEXT PRIMARY KEY,
                source_type   TEXT,
                url           TEXT,
                platform      TEXT,
                discovered_at TEXT,
                metadata      TEXT
            )
        """
        async with self._engine.begin() as conn:
            await conn.execute(text(create_leaks))
            await conn.execute(text(create_sources))
