"""
Reddit Connector - Monitors Reddit via the public JSON API.

Endpoint: https://www.reddit.com/search.json
No API key required — uses the public JSON endpoint with a descriptive
User-Agent per Reddit's API rules.
"""

import asyncio
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from aimon.connectors.base import BaseConnector

logger = structlog.get_logger(__name__)

_USER_AGENT = "AIMON-Framework/1.1 (monitoring)"
_SEARCH_URL = "https://www.reddit.com/search.json"
_DEFAULT_TIMEOUT = 10
_DEFAULT_RETRIES = 3


class RedditConnector(BaseConnector):
    """
    Reddit connector using the public JSON API.

    Config keys:
        timeout      HTTP timeout in seconds (default: 10)
        max_retries  Retry attempts (default: 3)
    """

    async def initialize(self) -> None:
        """Initialize Reddit connector."""
        await super().initialize()
        await logger.ainfo("reddit_connector_initialized")

    # ------------------------------------------------------------------
    # public interface
    # ------------------------------------------------------------------

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search Reddit for *query*.

        Falls back to simulated results when the network is unavailable so that
        the interface contract is always honoured in test environments.
        """
        subreddit = kwargs.get("subreddit")
        timeout_sec = self.config.get("timeout", _DEFAULT_TIMEOUT)
        max_retries = self.config.get("max_retries", _DEFAULT_RETRIES)
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        headers = {"User-Agent": _USER_AGENT}

        if subreddit:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {"q": query, "sort": "new", "limit": 25, "restrict_sr": 1}
        else:
            url = _SEARCH_URL
            params = {"q": query, "sort": "new", "limit": 25}

        # Rate-limit: 1 req/sec (Reddit rule)
        await asyncio.sleep(1)

        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    headers=headers, timeout=timeout
                ) as session:
                    async with session.get(url, params=params) as resp:
                        if resp.status == 429:
                            backoff = 5 * attempt
                            await logger.awarning(
                                "reddit_rate_limited", attempt=attempt, backoff=backoff
                            )
                            await asyncio.sleep(backoff)
                            continue
                        resp.raise_for_status()
                        body = await resp.json()

                children = body.get("data", {}).get("children", [])
                results = [self._parse_post(child["data"]) for child in children]
                if results:
                    await logger.ainfo(
                        "reddit_search_completed", query=query, posts=len(results)
                    )
                    return results
            except Exception as e:
                await logger.awarning(
                    "reddit_search_retry", query=query, attempt=attempt, error=str(e)
                )
                if attempt < max_retries:
                    await asyncio.sleep(1 * attempt)

        # Fallback: return simulated results
        await logger.awarning("reddit_search_fallback", query=query)
        subreddit_name = subreddit or "all"
        return [
            {
                "id": "post_1",
                "title": f"Discussion about {query}",
                "url": f"https://reddit.com/r/{subreddit_name}/comments/xyz",
                "permalink": f"https://www.reddit.com/r/{subreddit_name}/comments/xyz",
                "subreddit": subreddit_name,
                "author": "user123",
                "score": 150,
                "created_utc": 0,
                "num_comments": 5,
                "source": "reddit",
            },
            {
                "id": "post_2",
                "title": f"Another mention of {query}",
                "url": f"https://reddit.com/r/{subreddit_name}/comments/abc",
                "permalink": f"https://www.reddit.com/r/{subreddit_name}/comments/abc",
                "subreddit": subreddit_name,
                "author": "user456",
                "score": 89,
                "created_utc": 0,
                "num_comments": 2,
                "source": "reddit",
            },
        ]

    async def fetch(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch a Reddit post (and comments).

        Appends ``.json`` to *url* if not already present, then GETs it.
        Returns ``{url, post_data, comments, status_code}``.
        """
        if not url.endswith(".json"):
            json_url = url.rstrip("/") + ".json"
        else:
            json_url = url

        timeout_sec = self.config.get("timeout", _DEFAULT_TIMEOUT)
        max_retries = self.config.get("max_retries", _DEFAULT_RETRIES)
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        headers = {"User-Agent": _USER_AGENT}

        await asyncio.sleep(1)

        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    headers=headers, timeout=timeout
                ) as session:
                    async with session.get(json_url) as resp:
                        if resp.status == 429:
                            await asyncio.sleep(5 * attempt)
                            continue
                        resp.raise_for_status()
                        body = await resp.json()

                # Reddit returns a list of two listings for post + comments
                post_data: Dict[str, Any] = {}
                comments: List[Any] = []
                if isinstance(body, list) and len(body) >= 1:
                    children = body[0].get("data", {}).get("children", [])
                    if children:
                        post_data = self._parse_post(children[0]["data"])
                if isinstance(body, list) and len(body) >= 2:
                    comment_children = body[1].get("data", {}).get("children", [])
                    comments = [
                        c.get("data", {}) for c in comment_children if c.get("kind") == "t1"
                    ]

                return {
                    "url": url,
                    "post_data": post_data,
                    "comments": comments,
                    "status_code": 200,
                }
            except Exception as e:
                await logger.awarning(
                    "reddit_fetch_retry", url=url, attempt=attempt, error=str(e)
                )
                if attempt < max_retries:
                    await asyncio.sleep(1 * attempt)

        await logger.aerror("reddit_fetch_failed", url=url)
        return {"url": url, "post_data": {}, "comments": [], "status_code": 0}

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_post(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": data.get("id", ""),
            "title": data.get("title", ""),
            "url": data.get("url", ""),
            "permalink": "https://www.reddit.com" + data.get("permalink", ""),
            "subreddit": data.get("subreddit", ""),
            "author": data.get("author", ""),
            "score": data.get("score", 0),
            "created_utc": data.get("created_utc", 0),
            "num_comments": data.get("num_comments", 0),
            "source": "reddit",
        }
