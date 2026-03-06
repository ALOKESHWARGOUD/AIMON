"""
Storage Base - Abstract storage interface.

Allows pluggable storage backends (memory, file, database, Redis, etc).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    
    All storage implementations must inherit from this.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize storage backend.
        
        Args:
            name: Storage backend name
            config: Configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend."""
        self._initialized = True
    
    @abstractmethod
    async def save(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """
        Save data.
        
        Args:
            key: Data key
            data: Data to save
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve data.
        
        Args:
            key: Data key
            
        Returns:
            Data or None if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete data.
        
        Args:
            key: Data key
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def query(self, query_filter: Dict[str, Any]) -> List[Any]:
        """
        Query data.
        
        Args:
            query_filter: Query filter
            
        Returns:
            List of matching records
        """
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Get count of stored items."""
        pass
    
    async def shutdown(self) -> None:
        """Shutdown the storage backend."""
        self._initialized = False
