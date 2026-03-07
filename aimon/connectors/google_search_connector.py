"""
Google Search Connector - Leak-specific Google search strategies.

Uses Google Custom Search JSON API when configured, with DuckDuckGo HTML
scraping as fallback.  Selectolax is used for HTML parsing performance.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from aimon.connectors.base import BaseConnector

logger = structlog.get_logger(__name__)

# Platform inference patterns (url substring → platform label)
_PLATFORM_PATTERNS: List[tuple[str, str]] = [
    ("t.me", "telegram"),
    ("telegram.me", "telegram"),
    (".torrent", "torrent"),
    ("1337x", "torrent"),
    ("thepiratebay", "torrent"),
    ("piratebay", "torrent"),
    ("drive.google.com", "gdrive"),
    ("docs.google.com", "gdrive"),
    ("mega.nz", "mega"),
    ("mega.co.nz", "mega"),
    ("reddit.com", "reddit"),
    ("mediafire.com", "mediafire"),
    ("zippyshare.com", "zippyshare"),
]

LEAK_QUERY_TEMPLATES: List[str] = [
    "{brand} download",
    "{brand} telegram",
    "{brand} torrent",
    "{brand} free course",
    "{brand} google drive",
    "{brand} mega.nz",
]

_GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
_DDG_URL = "https://html.duckduckgo.com/html/"
_DEFAULT_TIMEOUT = 15
_USER_AGENT = "AIMON-Framework/1.1 (monitoring)"


class GoogleSearchConnector(BaseConnector):
    """
    Leak-aware Google search connector.

    Config keys:
        api_key          Google Custom Search API key (optional)
        search_engine_id Google Custom Search engine ID (optional)
        timeout          HTTP timeout in seconds (default: 15)
        max_results      Maximum results to return per query (default: 10)

    When ``api_key`` and ``search_engine_id`` are configured the Google
    Custom Search JSON API is used.  Otherwise falls back to DuckDuckGo
    HTML scraping via ``selectolax`` for speed.
    """

    async def initialize(self) -> None:
        """Initialize the Google search connector."""
        await super().initialize()
        await logger.ainfo("google_search_connector_initialized")

    # ------------------------------------------------------------------
    # public interface
    # ------------------------------------------------------------------

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for *query* using Google Custom Search or DuckDuckGo.

        Args:
            query: Search query string.
            **kwargs: Optional overrides.  ``brand`` key activates leak
                      query expansion using ``LEAK_QUERY_TEMPLATES``.

        Returns:
            List of result dicts matching the standard schema.
        """
        brand: Optional[str] = kwargs.get("brand")

        if brand:
            return await self._search_brand(brand)

        return await self._run_query(query)

    async def fetch(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch raw content from *url*.

        Args:
            url: Target URL.

        Returns:
            Dict with ``url``, ``html``, ``status_code``.
        """
        timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", _DEFAULT_TIMEOUT))
        headers = {"User-Agent": _USER_AGENT}

        try:
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(url) as resp:
                    html = await resp.text(errors="replace")
                    return {"url": url, "html": html, "status_code": resp.status}
        except Exception as exc:
            await logger.aerror("google_fetch_failed", url=url, error=str(exc))
            return {"url": url, "html": "", "status_code": 0}

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    async def _search_brand(self, brand: str) -> List[Dict[str, Any]]:
        """Run all LEAK_QUERY_TEMPLATES for *brand* and aggregate results."""
        results: List[Dict[str, Any]] = []
        for template in LEAK_QUERY_TEMPLATES:
            query = template.format(brand=brand)
            results.extend(await self._run_query(query, original_brand=brand))
        return results

    async def _run_query(
        self, query: str, original_brand: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute a single search query."""
        api_key = self.config.get("api_key")
        cx = self.config.get("search_engine_id")

        if api_key and cx:
            return await self._google_api_search(query, api_key, cx)
        return await self._ddg_search(query)

    async def _google_api_search(
        self, query: str, api_key: str, cx: str
    ) -> List[Dict[str, Any]]:
        """Search via Google Custom Search JSON API."""
        timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", _DEFAULT_TIMEOUT))
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": min(self.config.get("max_results", 10), 10),
        }

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(_GOOGLE_SEARCH_URL, params=params) as resp:
                    resp.raise_for_status()
                    body = await resp.json()

            items = body.get("items", [])
            return [self._parse_google_item(item, query) for item in items]
        except Exception as exc:
            await logger.aerror("google_api_search_failed", query=query, error=str(exc))
            return []

    async def _ddg_search(self, query: str) -> List[Dict[str, Any]]:
        """Fallback: scrape DuckDuckGo HTML results via selectolax."""
        timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", _DEFAULT_TIMEOUT))
        headers = {"User-Agent": _USER_AGENT}

        try:
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.post(_DDG_URL, data={"q": query}) as resp:
                    html = await resp.text(errors="replace")

            return self._parse_ddg_html(html, query)
        except Exception as exc:
            await logger.awarning("ddg_search_failed", query=query, error=str(exc))
            return []

    @staticmethod
    def _parse_google_item(item: Dict[str, Any], query: str) -> Dict[str, Any]:
        url = item.get("link", "")
        return {
            "source_type": "google",
            "url": url,
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "platform": GoogleSearchConnector._infer_platform(url),
            "query": query,
        }

    @staticmethod
    def _parse_ddg_html(html: str, query: str) -> List[Dict[str, Any]]:
        """Parse DuckDuckGo HTML response using selectolax."""
        results: List[Dict[str, Any]] = []
        try:
            from selectolax.parser import HTMLParser
            tree = HTMLParser(html)

            for result_node in tree.css("div.result"):
                title_node = result_node.css_first("a.result__a")
                snippet_node = result_node.css_first("a.result__snippet")
                url_node = result_node.css_first("a.result__url")

                if not title_node:
                    continue

                href = title_node.attributes.get("href", "")
                # DuckDuckGo wraps URLs: extract from uddg= param
                url_match = re.search(r"uddg=([^&]+)", href)
                if url_match:
                    from urllib.parse import unquote
                    url = unquote(url_match.group(1))
                else:
                    url = url_node.text(strip=True) if url_node else href

                results.append(
                    {
                        "source_type": "google",
                        "url": url,
                        "title": title_node.text(strip=True),
                        "snippet": snippet_node.text(strip=True) if snippet_node else "",
                        "platform": GoogleSearchConnector._infer_platform(url),
                        "query": query,
                    }
                )
        except Exception as exc:
            logger.warning("ddg_html_parse_failed", error=str(exc))

        return results

    @staticmethod
    def _infer_platform(url: str) -> str:
        """Infer the platform from a URL string."""
        lower = url.lower()
        for pattern, label in _PLATFORM_PATTERNS:
            if pattern in lower:
                return label
        return "unknown"
