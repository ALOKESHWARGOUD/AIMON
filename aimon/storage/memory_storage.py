"""
Memory Storage - In-memory storage backend.

Stores data in RAM - useful for testing and caching.
"""

from typing import Any, Dict, List, Optional
import structlog
from aimon.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class MemoryStorage(StorageBackend):
    """
    In-memory storage backend.
    
    All data is stored in a dictionary in RAM.
    Data is lost when the application stops.
    """
    
    def __init__(self, name: str = "memory", config: Optional[Dict[str, Any]] = None):
        """Initialize memory storage."""
        super().__init__(name, config)
        self._store: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self) -> None:
        """Initialize memory storage."""
        await super().initialize()
        await logger.ainfo("memory_storage_initialized")
    
    async def save(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Save data to memory."""
        try:
            self._store[key] = data
            self._metadata[key] = {
                "ttl": ttl,
                "created": __import__("time").time(),
            }
            await logger.adebug("memory_save", key=key)
            return True
        except Exception as e:
            await logger.aerror("memory_save_failed", key=key, error=str(e))
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get data from memory."""
        try:
            if key not in self._store:
                return None
            
            # Check TTL
            metadata = self._metadata.get(key, {})
            if metadata.get("ttl"):
                import time
                elapsed = time.time() - metadata["created"]
                if elapsed > metadata["ttl"]:
                    del self._store[key]
                    del self._metadata[key]
                    return None
            
            await logger.adebug("memory_get", key=key)
            return self._store[key]
            
        except Exception as e:
            await logger.aerror("memory_get_failed", key=key, error=str(e))
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete data from memory."""
        try:
            if key in self._store:
                del self._store[key]
                del self._metadata[key]
                await logger.adebug("memory_delete", key=key)
                return True
            return False
        except Exception as e:
            await logger.aerror("memory_delete_failed", key=key, error=str(e))
            return False
    
    async def query(self, query_filter: Dict[str, Any]) -> List[Any]:
        """Query data from memory."""
        try:
            results = []
            
            for key, value in self._store.items():
                if isinstance(value, dict):
                    # Simple filter matching
                    match = True
                    for filter_key, filter_value in query_filter.items():
                        if value.get(filter_key) != filter_value:
                            match = False
                            break
                    
                    if match:
                        results.append(value)
            
            await logger.adebug("memory_query", results=len(results))
            return results
            
        except Exception as e:
            await logger.aerror("memory_query_failed", error=str(e))
            return []
    
    async def count(self) -> int:
        """Get count of items."""
        return len(self._store)
