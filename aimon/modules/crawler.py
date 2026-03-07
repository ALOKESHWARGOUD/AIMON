"""
Crawler Module - Crawls discovered sources to extract content and metadata.

Subscribes to: source_discovered
Emits: page_crawled, content_extracted
"""

from __future__ import annotations

from typing import Any, Dict, List
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

# Keywords that suggest download/leak intent
_DOWNLOAD_KEYWORDS = frozenset(
    ["download", "get", "free", "torrent", "magnet"]
)

# File extensions that indicate leaked/pirated content
_LEAK_EXTENSIONS = frozenset(
    [".zip", ".rar", ".pdf", ".mp4", ".mkv", ".torrent"]
)


def extract_metadata(html: str, url: str) -> Dict[str, Any]:
    """
    Extract structured metadata from an HTML page using selectolax.

    Args:
        html: Raw HTML string.
        url: Source URL (used for context / relative link resolution).

    Returns:
        Dict with keys: ``page_title``, ``download_buttons``,
        ``embedded_links``, ``file_references``, ``meta_description``.
    """
    result: Dict[str, Any] = {
        "page_title": "",
        "download_buttons": [],
        "embedded_links": [],
        "file_references": [],
        "meta_description": "",
    }

    try:
        from selectolax.parser import HTMLParser

        tree = HTMLParser(html)

        # Page title
        title_node = tree.css_first("title")
        if title_node:
            result["page_title"] = title_node.text(strip=True)

        # Meta description
        for meta in tree.css("meta"):
            name = meta.attributes.get("name", "").lower()
            if name == "description":
                result["meta_description"] = meta.attributes.get("content", "")
                break

        # All anchor links
        embedded: List[str] = []
        download_buttons: List[str] = []
        file_refs: List[str] = []

        for anchor in tree.css("a"):
            href = anchor.attributes.get("href", "")
            if not href:
                continue
            embedded.append(href)

            # Download buttons — anchors whose text matches known keywords
            text_lower = anchor.text(strip=True).lower()
            if any(kw in text_lower for kw in _DOWNLOAD_KEYWORDS):
                download_buttons.append(href)

            # File references — links to known leak extensions
            href_lower = href.lower().split("?")[0]
            if any(href_lower.endswith(ext) for ext in _LEAK_EXTENSIONS):
                file_refs.append(href)

        result["embedded_links"] = embedded
        result["download_buttons"] = download_buttons
        result["file_references"] = file_refs

    except ImportError:
        # selectolax not installed — return empty metadata gracefully
        logger.warning("selectolax_not_installed", hint="pip install selectolax")
    except Exception as exc:
        logger.warning("metadata_extraction_failed", url=url, error=str(exc))

    return result


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
            url = source.get("url", "")

            # Extract structured metadata from the simulated HTML
            simulated_html = f"<html><head><title>Page from {source_id}</title></head><body>{content}</body></html>"
            metadata_extracted = extract_metadata(simulated_html, url)
            metadata_extracted.update({
                "status_code": 200,
                "content_type": "text/html",
                "crawl_time": 0.5,
            })

            page_data = {
                "source_id": source_id,
                "url": url,
                "title": f"Page from {source_id}",
                "content": content,
                "metadata": {
                    "status_code": 200,
                    "content_type": "text/html",
                    "crawl_time": 0.5,
                },
                "metadata_extracted": metadata_extracted,
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
