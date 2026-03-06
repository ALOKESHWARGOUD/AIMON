"""
File Storage - File-based storage backend.

Stores data as JSON files on disk.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import structlog
from aimon.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class FileStorage(StorageBackend):
    """
    File-based storage backend.
    
    Stores data as JSON files on disk.
    Useful for persistent storage between runs.
    """
    
    def __init__(self, name: str = "file", config: Optional[Dict[str, Any]] = None):
        """
        Initialize file storage.
        
        Config should contain:
        - storage_path: Directory to store files (default: "./data")
        """
        super().__init__(name, config)
        self.storage_path = Path(self.config.get("storage_path", "./data"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """Initialize file storage."""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            await super().initialize()
            await logger.ainfo("file_storage_initialized", path=str(self.storage_path))
        except Exception as e:
            await logger.aerror("file_storage_init_failed", error=str(e))
            raise
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for key."""
        # Sanitize key to make it filename-safe
        safe_key = "".join(c if c.isalnum() or c in ("-_") else "_" for c in key)
        return self.storage_path / f"{safe_key}.json"
    
    async def save(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Save data to file."""
        try:
            file_path = self._get_file_path(key)
            
            # Prepare data with metadata
            storage_data = {
                "key": key,
                "data": data,
                "ttl": ttl,
            }
            
            # Write to file
            with open(file_path, "w") as f:
                json.dump(storage_data, f, indent=2, default=str)
            
            await logger.adebug("file_save", key=key, path=str(file_path))
            return True
            
        except Exception as e:
            await logger.aerror("file_save_failed", key=key, error=str(e))
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get data from file."""
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                return None
            
            with open(file_path, "r") as f:
                storage_data = json.load(f)
            
            await logger.adebug("file_get", key=key)
            return storage_data.get("data")
            
        except Exception as e:
            await logger.aerror("file_get_failed", key=key, error=str(e))
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete data from file."""
        try:
            file_path = self._get_file_path(key)
            
            if file_path.exists():
                file_path.unlink()
                await logger.adebug("file_delete", key=key)
                return True
            
            return False
            
        except Exception as e:
            await logger.aerror("file_delete_failed", key=key, error=str(e))
            return False
    
    async def query(self, query_filter: Dict[str, Any]) -> List[Any]:
        """Query data from files."""
        try:
            results = []
            
            # Scan all JSON files in storage path
            for file_path in self.storage_path.glob("*.json"):
                try:
                    with open(file_path, "r") as f:
                        storage_data = json.load(f)
                    
                    data = storage_data.get("data", {})
                    
                    if isinstance(data, dict):
                        # Simple filter matching
                        match = True
                        for filter_key, filter_value in query_filter.items():
                            if data.get(filter_key) != filter_value:
                                match = False
                                break
                        
                        if match:
                            results.append(data)
                
                except Exception as e:
                    await logger.aerror("file_query_parse_failed", 
                                      file=str(file_path), error=str(e))
            
            await logger.adebug("file_query", results=len(results))
            return results
            
        except Exception as e:
            await logger.aerror("file_query_failed", error=str(e))
            return []
    
    async def count(self) -> int:
        """Get count of stored files."""
        try:
            return len(list(self.storage_path.glob("*.json")))
        except Exception as e:
            await logger.aerror("file_count_failed", error=str(e))
            return 0
