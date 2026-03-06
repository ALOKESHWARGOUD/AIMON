"""
Sync Wrapper - Synchronous API wrapper for AIMON.

Allows developers to use AIMON from synchronous (non-async) code.

Example usage:

    from aimon.sync import AIMONSync
    
    fw = AIMONSync()
    sources = fw.discovery.search("movie download")
    threats = fw.get_threats()
"""

import asyncio
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from aimon.framework_api import AIMON


class SyncWrapper:
    """Wraps async function to be callable from sync code."""
    
    def __init__(self, async_func):
        self.async_func = async_func
        self._loop = None
    
    def _get_loop(self):
        """Get or create event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
        return loop
    
    def __call__(self, *args, **kwargs):
        """Call async function from sync context."""
        try:
            loop = asyncio.get_running_loop()
            # Already in async context, create task
            return asyncio.ensure_future(self.async_func(*args, **kwargs))
        except RuntimeError:
            # Not in async context, run in new loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.async_func(*args, **kwargs))
            finally:
                loop.close()


class SyncDiscoveryModule:
    """Sync wrapper for DiscoveryModule."""
    
    def __init__(self, async_module):
        self._module = async_module
    
    def search(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for sources."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._module.search(query, filters or {}))
        finally:
            loop.close()


class SyncCrawlerModule:
    """Sync wrapper for CrawlerModule."""
    
    def __init__(self, async_module):
        self._module = async_module
    
    def crawl(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Crawl a source."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._module.crawl(source))
        finally:
            loop.close()
    
    def get_crawled_pages(self) -> List[Dict[str, Any]]:
        """Get crawled pages."""
        return self._module.get_crawled_pages()


class SyncIntelligenceModule:
    """Sync wrapper for IntelligenceModule."""
    
    def __init__(self, async_module):
        self._module = async_module
    
    def analyze(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a page."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._module.analyze(page))
        finally:
            loop.close()
    
    def get_threats(self) -> List[Dict[str, Any]]:
        """Get detected threats."""
        return self._module.get_threats()


class SyncAlertsModule:
    """Sync wrapper for AlertsModule."""
    
    def __init__(self, async_module):
        self._module = async_module
    
    def generate_alert(self, threat: Dict[str, Any]) -> Dict[str, Any]:
        """Generate alert."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._module.generate_alert(threat))
        finally:
            loop.close()
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts."""
        return self._module.get_alerts()
    
    def get_alert_history(self) -> List[Dict[str, Any]]:
        """Get alert history."""
        return self._module.get_alert_history()


class AIMONSync:
    """
    Synchronous wrapper for AIMON framework.
    
    Allows using AIMON from synchronous code.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize sync AIMON."""
        self._framework = AIMON(config)
        self._initialized = False
        
        # Wrapped modules
        self.discovery = None
        self.crawler = None
        self.intelligence = None
        self.alerts = None
    
    def initialize(self) -> None:
        """Initialize the framework."""
        if self._initialized:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._framework.initialize())
            
            # Wrap modules
            self.discovery = SyncDiscoveryModule(self._framework.discovery)
            self.crawler = SyncCrawlerModule(self._framework.crawler)
            self.intelligence = SyncIntelligenceModule(self._framework.intelligence)
            self.alerts = SyncAlertsModule(self._framework.alerts)
            
            self._initialized = True
        finally:
            loop.close()
    
    def shutdown(self) -> None:
        """Shutdown the framework."""
        if not self._initialized:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._framework.shutdown())
            self._initialized = False
        finally:
            loop.close()
    
    def search_sources(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for sources."""
        if not self._initialized:
            self.initialize()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self._framework.search_sources(query, filters or {})
            )
        finally:
            loop.close()
    
    def get_threats(self) -> List[Dict[str, Any]]:
        """Get all detected threats."""
        if not self._initialized:
            return []
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._framework.get_threats())
        finally:
            loop.close()
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts."""
        if not self._initialized:
            return []
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._framework.get_alerts_list())
        finally:
            loop.close()
    
    def get_status(self) -> Dict[str, Any]:
        """Get framework status."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._framework.get_status())
        finally:
            loop.close()
    
    def __enter__(self):
        """Sync context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.shutdown()
        return False
