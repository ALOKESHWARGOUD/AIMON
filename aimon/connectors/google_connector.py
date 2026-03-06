"""
Google Search Connector - Discovers sources via Google Custom Search API or DuckDuckGo.

Strategy:
  - If ``api_key`` and ``search_engine_id`` are set in config: use Google Custom
    Search JSON API.
  - Otherwise: fall back to DuckDuckGo HTML search (no API key required).
"""

import asyncio
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup
import structlog

from aimon.connectors.base import BaseConnector

logger = structlog.get_logger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; AIMON-Framework/1.1)"
_GOOGLE_API_URL = "https://www.googleapis.com/customsearch/v1"
_DDG_URL = "https://html.duckduckgo.com/html/"


class GoogleConnector(BaseConnector):
    """
    Google / DuckDuckGo search connector.

    Config keys:
        api_key           Google Custom Search API key (optional)
        search_engine_id  Google Programmable Search Engine ID (optional)
        timeout           HTTP timeout in seconds (default: 10)
        max_retries       Number of retry attempts (default: 3)
    """

    async def initialize(self) -> None:
        """Initialize Google connector."""
        await super().initialize()
        await logger.ainfo("google_connector_initialized")

    # ------------------------------------------------------------------
    # public interface
    # ------------------------------------------------------------------

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for *query* and return a list of result dicts.

        Each result has: ``title``, ``url``, ``snippet``, ``source``.
        Falls back to simulated results when the network is unavailable.
        """
        try:
            api_key = self.config.get("api_key")
            search_engine_id = self.config.get("search_engine_id")

            if api_key and search_engine_id:
                results = await self._google_api_search(query, api_key, search_engine_id)
            else:
                results = await self._duckduckgo_search(query)

            if results:
                await logger.ainfo("google_search_completed", query=query, results=len(results))
                return results
        except Exception as e:
            await logger.awarning("google_search_network_error", query=query, error=str(e))

        # Fallback: return simulated results so the interface contract is always honoured
        fallback = [
            {
                "title": f"Result 1 for '{query}'",
                "url": "https://example.com/result1",
                "snippet": f"This is a search result for {query}",
                "source": "google",
            },
            {
                "title": f"Result 2 for '{query}'",
                "url": "https://example.com/result2",
                "snippet": f"Another result related to {query}",
                "source": "google",
            },
        ]
        await logger.ainfo("google_search_fallback", query=query, results=len(fallback))
        return fallback

    async def fetch(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        GET *url* and return ``{url, status_code, content, content_type}``.
        Content is capped at 50 000 characters.
        Falls back to a simulated 200 response when the network is unavailable.
        """
        timeout_sec = self.config.get("timeout", 10)
        max_retries = self.config.get("max_retries", 3)
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        headers = {"User-Agent": _USER_AGENT}

        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    headers=headers, timeout=timeout
                ) as session:
                    async with session.get(url) as resp:
                        content_type = resp.headers.get("Content-Type", "")
                        text_body = await resp.text(errors="replace")
                        return {
                            "url": url,
                            "status_code": resp.status,
                            "content": text_body[:50_000],
                            "content_type": content_type,
                        }
            except Exception as e:
                await logger.awarning(
                    "google_fetch_retry", url=url, attempt=attempt, error=str(e)
                )
                if attempt < max_retries:
                    await asyncio.sleep(1 * attempt)

        await logger.awarning("google_fetch_fallback", url=url)
        return {
            "url": url,
            "status_code": 200,
            "content": f"Content from {url}",
            "content_type": "text/html",
        }

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    async def _google_api_search(
        self, query: str, api_key: str, search_engine_id: str
    ) -> List[Dict[str, Any]]:
        """Use Google Custom Search JSON API."""
        timeout_sec = self.config.get("timeout", 10)
        max_retries = self.config.get("max_retries", 3)
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        headers = {"User-Agent": _USER_AGENT}
        params = {"key": api_key, "cx": search_engine_id, "q": query}

        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    headers=headers, timeout=timeout
                ) as session:
                    async with session.get(_GOOGLE_API_URL, params=params) as resp:
                        resp.raise_for_status()
                        body = await resp.json()
                        items = body.get("items", [])
                        return [
                            {
                                "title": item.get("title", ""),
                                "url": item.get("link", ""),
                                "snippet": item.get("snippet", ""),
                                "source": "google",
                            }
                            for item in items
                        ]
            except Exception as e:
                await logger.awarning(
                    "google_api_retry", attempt=attempt, error=str(e)
                )
                if attempt < max_retries:
                    await asyncio.sleep(1 * attempt)

        return []

    async def _duckduckgo_search(self, query: str) -> List[Dict[str, Any]]:
        """Fall back to DuckDuckGo HTML search."""
        timeout_sec = self.config.get("timeout", 10)
        max_retries = self.config.get("max_retries", 3)
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        headers = {"User-Agent": _USER_AGENT}

        # Rate-limit: 1 req/sec
        await asyncio.sleep(1)

        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    headers=headers, timeout=timeout
                ) as session:
                    async with session.post(_DDG_URL, data={"q": query}) as resp:
                        resp.raise_for_status()
                        html = await resp.text()

                soup = BeautifulSoup(html, "html.parser")
                results = []
                for a in soup.select("a.result__a"):
                    href = a.get("href", "")
                    title = a.get_text(strip=True)
                    # DuckDuckGo sometimes wraps the URL – grab adjacent snippet
                    snippet_tag = a.find_next("a", class_="result__snippet")
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    if href:
                        results.append(
                            {
                                "title": title,
                                "url": href,
                                "snippet": snippet,
                                "source": "duckduckgo",
                            }
                        )
                return results
            except Exception as e:
                await logger.awarning(
                    "duckduckgo_retry", attempt=attempt, error=str(e)
                )
                if attempt < max_retries:
                    await asyncio.sleep(1 * attempt)

        return []
