# AIMON Plugin System

## What Are Plugins?

Plugins are Python packages or modules that extend AIMON at runtime without
modifying core framework code.  They are **auto-discovered** from the
`aimon.plugins.*` namespace and can also be registered manually.

---

## Auto-Discovery

Place your plugin package anywhere on `sys.path` under the namespace
`aimon.plugins`:

```
aimon_my_plugin/
    aimon/
        plugins/
            my_plugin.py    ← discovered automatically
```

On startup, `PluginEngine.discover_plugins("aimon.plugins")` imports every
module it finds under that namespace and logs the result.

---

## Creating a Connector Plugin

Subclass `BaseConnector` and implement `initialize`, `search`, and `fetch`:

```python
# aimon/plugins/my_connector.py
import aiohttp
from aimon.connectors.base import BaseConnector

class MyConnector(BaseConnector):
    async def initialize(self):
        await super().initialize()

    async def search(self, query, **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://my-api.example.com/search",
                params={"q": query}
            ) as resp:
                data = await resp.json()
        return [
            {"title": r["title"], "url": r["url"], "snippet": r["desc"], "source": "my_api"}
            for r in data.get("results", [])
        ]

    async def fetch(self, url, **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return {
                    "url": url,
                    "status_code": resp.status,
                    "content": await resp.text(),
                    "content_type": resp.headers.get("Content-Type", ""),
                }
```

---

## Creating a Storage Plugin

Subclass `StorageBackend` and implement all abstract methods:

```python
# aimon/plugins/redis_storage.py
import json
import aioredis
from aimon.storage.base import StorageBackend

class RedisStorage(StorageBackend):
    async def initialize(self):
        self._redis = await aioredis.create_redis_pool(
            self.config.get("redis_url", "redis://localhost")
        )
        await super().initialize()

    async def save(self, key, data, ttl=None):
        serialized = json.dumps(data)
        if ttl:
            await self._redis.setex(key, ttl, serialized)
        else:
            await self._redis.set(key, serialized)
        return True

    async def get(self, key):
        raw = await self._redis.get(key)
        return json.loads(raw) if raw else None

    async def delete(self, key):
        return bool(await self._redis.delete(key))

    async def query(self, query_filter):
        keys = await self._redis.keys("*")
        results = []
        for k in keys:
            val = await self.get(k.decode())
            if isinstance(val, dict) and all(val.get(fk) == fv for fk, fv in query_filter.items()):
                results.append(val)
        return results

    async def count(self):
        return await self._redis.dbsize()

    async def shutdown(self):
        self._redis.close()
        await self._redis.wait_closed()
        await super().shutdown()
```

---

## Creating a Fingerprint Plugin

Subclass `BaseFingerprinter` and implement `fingerprint` and `compare`:

```python
# aimon/plugins/text_fingerprinter.py
import hashlib
from aimon.fingerprint.engine import BaseFingerprinter

class TextFingerprinter(BaseFingerprinter):
    def __init__(self):
        super().__init__("text_fingerprinting")

    async def fingerprint(self, data):
        text = data if isinstance(data, str) else str(data)
        return hashlib.sha256(text.encode()).hexdigest()

    async def compare(self, fp1, fp2, threshold=0.9):
        if fp1 == fp2:
            return 1.0
        matches = sum(a == b for a, b in zip(fp1, fp2))
        return matches / max(len(fp1), len(fp2)) if max(len(fp1), len(fp2)) > 0 else 0.0
```

---

## Manual Plugin Registration

Plugins can be registered programmatically at any time:

```python
from aimon.core.plugin_engine import PluginEngine
from my_package import MyConnector

plugin_engine = PluginEngine()
await plugin_engine.register_plugin("connector", "my_connector", MyConnector)

# Retrieve later
cls = await plugin_engine.get_plugin("connector", "my_connector")
connector = cls("my_connector", config={})
await connector.initialize()
```

---

## Complete Plugin Example with Event Subscription

```python
"""
custom_alert_plugin.py — sends a webhook when a threat is detected.
"""
import aiohttp
from aimon.core.base_module import BaseModule

class WebhookAlertPlugin(BaseModule):
    """Sends a POST to a webhook URL for every threat_detected event."""

    async def _initialize_impl(self):
        self.webhook_url = self.config.get(
            "webhook_url", "https://hooks.example.com/alert"
        )

    async def _subscribe_to_events(self):
        await self.subscribe_event("threat_detected", self._on_threat)

    async def _on_threat(self, **data):
        payload = {
            "text": f"[AIMON] Threat detected: {data.get('threat_level', 'unknown')} "
                    f"— source {data.get('source_id', '?')}"
        }
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(self.webhook_url, json=payload)
        except Exception:
            pass  # log and swallow


# Register with the runtime
from aimon.core.runtime import AIMONCoreRuntime

async def setup():
    runtime = AIMONCoreRuntime.get_instance()
    await runtime.initialize()
    await runtime.register_module(
        "webhook_alerts",
        WebhookAlertPlugin("webhook_alerts", config={"webhook_url": "https://..."}),
    )
```
