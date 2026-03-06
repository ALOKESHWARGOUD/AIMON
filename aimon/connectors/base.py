"""
Base Connector - Abstract base class for all data source connectors.

Connectors are responsible for connecting to external APIs and data sources
to discover and retrieve information.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class BaseConnector(ABC):
    """
    Abstract base class for connectors.
    
    Connectors fetch data from external sources like search engines,
    APIs, social networks, file sharing platforms, etc.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize a connector.
        
        Args:
            name: Connector name
            config: Configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the connector (setup credentials, connections, etc)."""
        self._initialized = True
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for results matching the query.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters
            
        Returns:
            List of results
        """
        pass
    
    @abstractmethod
    async def fetch(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch content from a specific URL or resource.
        
        Args:
            url: URL or resource identifier
            **kwargs: Additional fetch parameters
            
        Returns:
            Fetched content
        """
        pass
    
    async def validate(self) -> bool:
        """
        Validate connector is working (test credentials, connectivity).
        
        Returns:
            True if valid
        """
        return self._initialized
    
    async def shutdown(self) -> None:
        """Shutdown the connector and cleanup resources."""
        self._initialized = False
