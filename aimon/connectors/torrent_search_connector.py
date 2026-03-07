"""
Torrent Search Connector - Searches torrent index sites for piracy content.

Targets 1337x.to and thepiratebay.org using their public endpoints plus HTML
scraping via selectolax for performance.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import structlog

from aimon.connectors.base import BaseConnector

logger = structlog.get_logger(__name__)

_USER_AGENT = "AIMON-Framework/1.1 (monitoring)"
_DEFAULT_TIMEOUT = 15

# Magnet link pattern
_MAGNET_PATTERN = re.compile(r"magnet:\?[^\s\"'<>]+")


class TorrentSearchConnector(BaseConnector):
    """
    Torrent search connector.

    Queries 1337x and The Pirate Bay for content matching a query.
    Uses ``httpx`` with async mode and ``selectolax`` for HTML parsing.

    Config keys:
        timeout     HTTP timeout in seconds (default: 15)
        max_results Maximum results per site (default: 20)
    """

    async def initialize(self) -> None:
        """Initialize the torrent search connector."""
        await super().initialize()
        await logger.ainfo("torrent_search_connector_initialized")

    # ------------------------------------------------------------------
    # public interface
    # ------------------------------------------------------------------

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search torrent index sites for *query*.

        Args:
            query: Search query string.

        Returns:
            List of torrent result dicts.
        """
        results: List[Dict[str, Any]] = []

        tasks_results = await self._gather(
            self._search_1337x(query),
            self._search_piratebay(query),
        )
        for batch in tasks_results:
            results.extend(batch)

        return results

    async def fetch(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch a torrent page to extract its magnet link and metadata.

        Args:
            url: Torrent page URL.

        Returns:
            Dict with torrent metadata.
        """
        try:
            import httpx

            timeout = self.config.get("timeout", _DEFAULT_TIMEOUT)
            async with httpx.AsyncClient(
                headers={"User-Agent": _USER_AGENT},
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return self._extract_page_meta(resp.text, url)
        except Exception as exc:
            await logger.aerror("torrent_fetch_failed", url=url, error=str(exc))
            return {"url": url, "source_type": "torrent", "platform": "torrent"}

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    async def _gather(self, *coros) -> List[List[Dict[str, Any]]]:
        """Run coroutines concurrently and return their results."""
        import asyncio

        results = await asyncio.gather(*coros, return_exceptions=True)
        return [r if isinstance(r, list) else [] for r in results]

    async def _search_1337x(self, query: str) -> List[Dict[str, Any]]:
        """Scrape 1337x.to search results."""
        encoded = query.replace(" ", "+")
        url = f"https://www.1337x.to/search/{encoded}/1/"

        try:
            import httpx
            from selectolax.parser import HTMLParser

            timeout = self.config.get("timeout", _DEFAULT_TIMEOUT)
            async with httpx.AsyncClient(
                headers={"User-Agent": _USER_AGENT},
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                html = resp.text

            tree = HTMLParser(html)
            results: List[Dict[str, Any]] = []
            limit = self.config.get("max_results", 20)

            for row in tree.css("table.table-list tbody tr")[:limit]:
                name_node = row.css_first("td.name a:nth-child(2)")
                seeds_node = row.css_first("td.seeds")
                leeches_node = row.css_first("td.leeches")
                size_node = row.css_first("td.size")

                if not name_node:
                    continue

                href = name_node.attributes.get("href", "")
                detail_url = f"https://www.1337x.to{href}" if href.startswith("/") else href

                results.append(
                    {
                        "source_type": "torrent",
                        "url": detail_url,
                        "title": name_node.text(strip=True),
                        "seeders": _safe_int(seeds_node.text(strip=True) if seeds_node else "0"),
                        "leechers": _safe_int(
                            leeches_node.text(strip=True) if leeches_node else "0"
                        ),
                        "size": _clean_size(size_node.text(strip=True) if size_node else ""),
                        "platform": "torrent",
                        "magnet": None,
                        "category": "unknown",
                    }
                )

            await logger.ainfo("1337x_search_completed", query=query, results=len(results))
            return results

        except ImportError:
            await logger.awarning("httpx_or_selectolax_not_installed")
            return []
        except Exception as exc:
            await logger.awarning("1337x_search_failed", query=query, error=str(exc))
            return []

    async def _search_piratebay(self, query: str) -> List[Dict[str, Any]]:
        """Search The Pirate Bay via their JSON API."""
        encoded = query.replace(" ", "%20")
        api_url = f"https://apibay.org/q.php?q={encoded}"

        try:
            import httpx

            timeout = self.config.get("timeout", _DEFAULT_TIMEOUT)
            async with httpx.AsyncClient(
                headers={"User-Agent": _USER_AGENT},
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(api_url)
                if resp.status_code != 200:
                    return []
                data = resp.json()

            results: List[Dict[str, Any]] = []
            limit = self.config.get("max_results", 20)

            for item in data[:limit]:
                info_hash = item.get("info_hash", "")
                name = item.get("name", "")
                magnet = (
                    f"magnet:?xt=urn:btih:{info_hash}&dn={name.replace(' ', '+')}"
                    if info_hash
                    else None
                )

                results.append(
                    {
                        "source_type": "torrent",
                        "url": f"https://thepiratebay.org/description.php?id={item.get('id','')}",
                        "title": name,
                        "seeders": _safe_int(str(item.get("seeders", 0))),
                        "leechers": _safe_int(str(item.get("leechers", 0))),
                        "size": _format_bytes(item.get("size", 0)),
                        "platform": "torrent",
                        "magnet": magnet,
                        "category": item.get("category", "unknown"),
                    }
                )

            await logger.ainfo("piratebay_search_completed", query=query, results=len(results))
            return results

        except ImportError:
            await logger.awarning("httpx_not_installed")
            return []
        except Exception as exc:
            await logger.awarning("piratebay_search_failed", query=query, error=str(exc))
            return []

    @staticmethod
    def _extract_page_meta(html: str, url: str) -> Dict[str, Any]:
        """Extract torrent metadata from a detail page."""
        result: Dict[str, Any] = {
            "source_type": "torrent",
            "url": url,
            "title": "",
            "seeders": 0,
            "leechers": 0,
            "size": "",
            "platform": "torrent",
            "magnet": None,
            "category": "unknown",
        }
        magnet_match = _MAGNET_PATTERN.search(html)
        if magnet_match:
            result["magnet"] = magnet_match.group(0)

        try:
            from selectolax.parser import HTMLParser

            tree = HTMLParser(html)
            title_node = tree.css_first("title")
            if title_node:
                result["title"] = title_node.text(strip=True)
        except Exception:
            pass

        return result


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _safe_int(value: str) -> int:
    """Convert string to int, returning 0 on failure."""
    try:
        return int(value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0


def _clean_size(raw: str) -> str:
    """Strip non-size tokens (like seeder count mixed in)."""
    match = re.search(r"[\d.,]+\s*[KMGT]?B", raw, re.I)
    return match.group(0) if match else raw.strip()


def _format_bytes(size: Any) -> str:
    """Format byte count to human-readable string."""
    try:
        size = int(size)
    except (TypeError, ValueError):
        return "0 B"

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size //= 1024
    return f"{size:.1f} PB"
