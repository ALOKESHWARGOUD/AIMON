"""
Custom Connector Example — Subclassing BaseConnector.

Demonstrates:
  - Subclassing BaseConnector
  - Implementing search() and fetch() with aiohttp
  - Registering the custom connector with PluginEngine
  - Using the custom connector inside a DiscoveryModule
"""

import asyncio
from typing import Any, Dict, List, Optional

import aiohttp

from aimon.connectors.base import BaseConnector
from aimon.core.event_bus import EventBus
from aimon.core.plugin_engine import PluginEngine
from aimon.core.runtime import AIMONCoreRuntime
from aimon.modules import DiscoveryModule


# ---------------------------------------------------------------------------
# Custom connector
# ---------------------------------------------------------------------------

class HackerNewsConnector(BaseConnector):
    """
    A connector that searches Hacker News via the Algolia HN Search API.

    https://hn.algolia.com/api/v1/search?query=<q>&tags=story
    """

    _SEARCH_URL = "https://hn.algolia.com/api/v1/search"

    def __init__(self, name: str = "hackernews", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config or {})

    async def initialize(self) -> None:
        await super().initialize()
        print(f"[Connector] {self.name} initialized")

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search HN stories matching *query*."""
        timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", 10))
        params = {"query": query, "tags": "story", "hitsPerPage": 10}

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self._SEARCH_URL, params=params) as resp:
                    resp.raise_for_status()
                    body = await resp.json()

            hits = body.get("hits", [])
            results = [
                {
                    "title": h.get("title", ""),
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    "snippet": h.get("story_text", "")[:200],
                    "source": "hackernews",
                }
                for h in hits
                if h.get("title")
            ]
            print(f"[Connector] search '{query}' → {len(results)} results")
            return results
        except Exception as exc:
            print(f"[Connector] search failed: {exc}")
            return []

    async def fetch(self, url: str, **kwargs) -> Dict[str, Any]:
        """Fetch the raw HTML of *url*."""
        timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", 10))
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    content = await resp.text(errors="replace")
                    return {
                        "url": url,
                        "status_code": resp.status,
                        "content": content[:50_000],
                        "content_type": resp.headers.get("Content-Type", ""),
                    }
        except Exception as exc:
            print(f"[Connector] fetch failed: {exc}")
            return {"url": url, "status_code": 0, "content": "", "content_type": ""}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("[*] Custom Connector Example")

    # 1. Register the connector with PluginEngine
    plugin_engine = PluginEngine()
    await plugin_engine.register_plugin("connector", "hackernews", HackerNewsConnector)
    print("[*] HackerNewsConnector registered with PluginEngine")

    # 2. Retrieve and instantiate the connector from the registry
    ConnectorClass = await plugin_engine.get_plugin("connector", "hackernews")
    hn_connector = ConnectorClass("hackernews", config={"timeout": 10})
    await hn_connector.initialize()

    # 3. Wire it into a DiscoveryModule
    AIMONCoreRuntime.reset_instance()
    bus = EventBus()
    await bus.initialize()

    discovery = DiscoveryModule("discovery")
    discovery.event_bus = bus
    # Inject our custom connector
    discovery.connectors = [hn_connector]
    await discovery.initialize()

    # 4. Search via the custom connector
    print("\n[*] Searching Hacker News for 'AI leak'…")
    try:
        results = await hn_connector.search("AI leak")
        print(f"[+] Found {len(results)} results")
        for r in results[:3]:
            print(f"  - {r['title']}")
            print(f"    {r['url']}")
    except Exception as exc:
        print(f"[!] Search failed (network unavailable in sandbox?): {exc}")

    # 5. Shutdown
    await discovery.shutdown()
    AIMONCoreRuntime.reset_instance()
    print("\n[+] Custom connector example complete")


if __name__ == "__main__":
    asyncio.run(main())
