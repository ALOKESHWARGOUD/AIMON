"""
Crawler Module - Crawls discovered sources to extract content and metadata.

Subscribes to: source_discovered
Emits: page_crawled, content_extracted
"""

from typing import Dict, Any, List
import asyncio
from aimon.core.base_module import BaseModule
import structlog

logger = structlog.get_logger(__name__)

# Simulated page content templates keyed by platform identifier.
# ``{name}`` is replaced with the source name at crawl time.
_PLATFORM_CONTENT: Dict[str, str] = {
    "reddit":   (
        "Forum thread: users discussing {name}. "
        "Several replies include links to free download mirrors."
    ),
    "telegram": (
        "Telegram channel sharing {name}. "
        "Free lectures and torrent links are distributed here."
    ),
    "gdrive": (
        "Google Drive folder containing {name} course materials. "
        "Files available for free download via drive.google.com."
    ),
    "1337x": (
        "Torrent listing: {name} – full course for free. "
        "Torrent file and magnet link provided."
    ),
    "scribd": (
        "Document library entry for {name}. "
        "Lecture notes and course materials available."
    ),
}


class CrawlerModule(BaseModule):
    """
    Crawls web pages and sources to extract content.
    
    Processes source_discovered events from DiscoveryModule.
    Extracts content and emits page_crawled events.
    """
    
    async def _initialize_impl(self) -> None:
        """Initialize the crawler module."""
        self.crawled_pages = []
        self.active_crawls = set()
        await logger.ainfo("crawler_module_initialized")
    
    async def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events."""
        await self.subscribe_event("source_discovered", self._on_source_discovered)
    
    async def _shutdown_impl(self) -> None:
        """Shutdown the crawler module."""
        await logger.ainfo("crawler_module_shutdown")
    
    async def crawl(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crawl a source to extract content.
        
        Args:
            source: Source to crawl
            
        Returns:
            Crawled page data
        """
        source_id = source.get("id", "unknown")
        
        try:
            await logger.ainfo("crawl_started", source_id=source_id)
            
            # Build contextual page content based on the source's platform.
            platform = source.get("platform", "")
            name = source.get("name", source_id)
            content_tpl = _PLATFORM_CONTENT.get(
                platform,
                "Web page content related to {name}.",
            )
            content = content_tpl.format(name=name)

            page_data = {
                "source_id": source_id,
                "url": source.get("url"),
                "title": f"Page from {source_id}",
                "content": content,
                "metadata": {
                    "status_code": 200,
                    "content_type": "text/html",
                    "crawl_time": 0.5,
                }
            }
            
            self.crawled_pages.append(page_data)
            
            # Emit page_crawled event
            await self.emit_event("page_crawled", page=page_data)
            
            await logger.ainfo("crawl_completed", source_id=source_id)
            
            return page_data
            
        except Exception as e:
            await logger.aerror("crawl_failed", source_id=source_id, error=str(e))
            await self.emit_event("crawl_failed", source_id=source_id, error=str(e))
            raise
    
    async def _on_source_discovered(self, **data) -> None:
        """Handle source_discovered event."""
        source = data.get("source", {})
        source_id = source.get("id", "unknown")
        
        if source_id not in self.active_crawls:
            self.active_crawls.add(source_id)
            try:
                await self.crawl(source)
            finally:
                self.active_crawls.discard(source_id)
    
    def get_crawled_pages(self) -> List[Dict[str, Any]]:
        """Get all crawled pages."""
        return self.crawled_pages.copy()
