"""
Redis Storage Backend - Async cache and storage via redis.asyncio.

Suitable for risk score caching, network snapshots, and deduplication.

Config keys:
    redis_url   Redis URL (default: ``redis://localhost:6379/0``)
    key_prefix  Key prefix for namespacing (default: ``"aimon:"``)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import structlog

from aimon.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class RedisStorage(StorageBackend):
    """
    Redis-backed storage using ``redis.asyncio``.

    Stores serialised JSON values under prefixed keys.  Supports TTL via
    ``SETEX``.
    """

    def __init__(
        self, name: str = "redis", config: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(name, config)
        self._client: Any = None
        self._prefix: str = ""

    async def initialize(self) -> None:
        """Connect to Redis."""
        try:
            import redis.asyncio as aioredis  # type: ignore

            redis_url = self.config.get("redis_url", "redis://localhost:6379/0")
            self._prefix = self.config.get("key_prefix", "aimon:")
            self._client = aioredis.from_url(
                redis_url, encoding="utf-8", decode_responses=True
            )
            # Verify connectivity
            await self._client.ping()
            await super().initialize()
            await logger.ainfo("redis_storage_initialized", url=redis_url)

        except ImportError as exc:
            raise ImportError(
                "redis>=4.6 must be installed.  "
                "Install with: pip install 'aimon[redis]'"
            ) from exc
        except Exception as exc:
            await logger.aerror("redis_init_failed", error=str(exc))
            raise

    async def save(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Store *data* at *key* with optional TTL (seconds)."""
        try:
            full_key = self._prefix + key
            serialised = json.dumps(data, default=str)
            if ttl:
                await self._client.setex(full_key, ttl, serialised)
            else:
                await self._client.set(full_key, serialised)
            return True
        except Exception as exc:
            await logger.aerror("redis_save_failed", key=key, error=str(exc))
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve and deserialise data from *key*."""
        try:
            full_key = self._prefix + key
            raw = await self._client.get(full_key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            await logger.aerror("redis_get_failed", key=key, error=str(exc))
            return None

    async def delete(self, key: str) -> bool:
        """Delete *key* from Redis."""
        try:
            full_key = self._prefix + key
            await self._client.delete(full_key)
            return True
        except Exception as exc:
            await logger.aerror("redis_delete_failed", key=key, error=str(exc))
            return False

    async def query(self, query_filter: Dict[str, Any]) -> List[Any]:
        """
        Scan keys matching a pattern (from ``query_filter["pattern"]``).

        All matching values are deserialised and returned.
        """
        pattern = self.config.get("key_prefix", "aimon:") + query_filter.get("pattern", "*")
        results: List[Any] = []
        try:
            async for key in self._client.scan_iter(pattern, count=100):
                raw = await self._client.get(key)
                if raw:
                    try:
                        results.append(json.loads(raw))
                    except json.JSONDecodeError:
                        results.append(raw)
        except Exception as exc:
            await logger.aerror("redis_query_failed", error=str(exc))
        return results

    async def count(self) -> int:
        """Return the number of keys with the configured prefix."""
        try:
            pattern = self._prefix + "*"
            count = 0
            async for _ in self._client.scan_iter(pattern, count=100):
                count += 1
            return count
        except Exception as exc:
            await logger.aerror("redis_count_failed", error=str(exc))
            return 0

    async def shutdown(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.aclose()
        await super().shutdown()
