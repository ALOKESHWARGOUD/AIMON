"""
Plugin Example — Custom plugin with event subscription.

Demonstrates:
  - Creating a custom plugin class with initialize(context) and shutdown()
  - Subscribing to "page_crawled" events inside the plugin
  - Manually registering the plugin with PluginEngine
  - Running the framework and showing the plugin received events
"""

import asyncio
from typing import Any, Dict, List

from aimon.core.base_module import BaseModule
from aimon.core.event_bus import EventBus
from aimon.core.plugin_engine import PluginEngine
from aimon.core.runtime import AIMONCoreRuntime
from aimon.modules import DiscoveryModule, CrawlerModule


# ---------------------------------------------------------------------------
# Custom plugin implementation
# ---------------------------------------------------------------------------

class PageCrawledLogger(BaseModule):
    """
    A simple plugin that logs every 'page_crawled' event it receives.

    In a real plugin you might forward events to a SIEM, write to a database,
    trigger a webhook, etc.
    """

    def __init__(self, name: str = "page_crawled_logger", config=None):
        super().__init__(name, config or {})
        self.received_events: List[Dict[str, Any]] = []

    async def _initialize_impl(self):
        print(f"[Plugin] {self.name} initialized")

    async def _subscribe_to_events(self):
        await self.subscribe_event("page_crawled", self._on_page_crawled)

    async def _on_page_crawled(self, **data):
        self.received_events.append(data)
        url = data.get("url", "unknown")
        print(f"[Plugin] page_crawled received — url={url}")

    async def _shutdown_impl(self):
        print(f"[Plugin] {self.name} shutting down "
              f"(received {len(self.received_events)} events)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("[*] Plugin Example")

    # 1. Reset any existing singleton
    AIMONCoreRuntime.reset_instance()

    # 2. Create shared EventBus
    bus = EventBus()
    await bus.initialize()

    # 3. Register the plugin with PluginEngine
    plugin_engine = PluginEngine()
    await plugin_engine.register_plugin("module", "page_crawled_logger", PageCrawledLogger)
    print("[*] Plugin registered with PluginEngine")

    # 4. Instantiate + initialise modules on the shared bus
    plugin = PageCrawledLogger()
    discovery = DiscoveryModule("discovery")
    crawler = CrawlerModule("crawler")

    for mod in (plugin, discovery, crawler):
        mod.event_bus = bus
        await mod.initialize()

    # 5. Trigger the event chain: search → source_discovered → page_crawled
    print("\n[*] Running discovery (triggers page_crawled via crawler)…")
    await discovery.search("leaked content")
    await asyncio.sleep(0.3)   # let async events propagate

    # 6. Show results
    print(f"\n[+] Plugin received {len(plugin.received_events)} 'page_crawled' events")
    for evt in plugin.received_events[:3]:
        print(f"    url={evt.get('url', '?')}")

    # 7. Shutdown
    for mod in (plugin, discovery, crawler):
        await mod.shutdown()

    print("\n[+] Plugin example complete")


if __name__ == "__main__":
    asyncio.run(main())
