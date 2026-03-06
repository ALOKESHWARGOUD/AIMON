# AIMON Framework — Quick Start Guide

## Installation

```bash
pip install aimon-framework
```

### Optional extras

```bash
# PostgreSQL async driver
pip install "aimon-framework[storage-postgres]"

# Video/audio fingerprinting (OpenCV + librosa)
pip install "aimon-framework[fingerprint]"

# Everything
pip install "aimon-framework[all]"
```

---

## Async Usage

The recommended way is to use the `async with AIMON()` context manager:

```python
import asyncio
from aimon import AIMON

async def main():
    async with AIMON() as framework:
        # Search for potential leak sources
        sources = await framework.search_sources("my leaked asset")
        print(f"Found {len(sources)} sources")

        # Get detected threats
        threats = await framework.get_threats()
        for t in threats:
            print(t["threat_level"], t["source_id"])

        # Get generated alerts
        alerts = await framework.get_alerts_list()

        # Framework health / metrics
        status = await framework.get_status()
        print(status["metrics"])

asyncio.run(main())
```

---

## Sync Usage

For scripts or contexts where async is not convenient, use the `AIMONSync`
wrapper:

```python
from aimon.sync import AIMONSync

with AIMONSync() as framework:
    sources = framework.search_sources("my leaked asset")
    threats = framework.get_threats()
    status  = framework.get_status()
```

---

## CLI Usage

```bash
# Scan for a specific query
aimon scan "my leaked content"

# Start continuous monitoring
aimon monitor --query "my asset" --interval 60

# Show framework status
aimon status
```

---

## Database Storage Configuration

### SQLite (development / default)

```python
from aimon import AIMON

async with AIMON(config={"storage": {"database_url": "sqlite+aiosqlite:///aimon.db"}}) as fw:
    ...
```

### PostgreSQL (production)

```python
async with AIMON(config={
    "storage": {
        "database_url": "postgresql+asyncpg://user:password@localhost/aimon_db"
    }
}) as fw:
    ...
```

Install the PostgreSQL driver first:

```bash
pip install "aimon-framework[storage-postgres]"
```

---

## Custom Module

Subclass `BaseModule`, override `_initialize_impl` and optionally
`_subscribe_to_events`:

```python
from aimon.core.base_module import BaseModule
import structlog

logger = structlog.get_logger(__name__)

class MyModule(BaseModule):
    async def _initialize_impl(self):
        await logger.ainfo("my_module_ready")

    async def _subscribe_to_events(self):
        await self.subscribe_event("page_crawled", self._on_page_crawled)

    async def _on_page_crawled(self, **data):
        url = data.get("url", "")
        await logger.ainfo("page_seen", url=url)
```

Register and use it:

```python
from aimon.core.runtime import AIMONCoreRuntime

runtime = AIMONCoreRuntime.get_instance()
await runtime.initialize()
await runtime.register_module("my_module", MyModule("my_module"))
```

---

## Environment Variable Configuration

AIMON reads the following environment variables (via `python-dotenv`):

| Variable                     | Description                            | Default                        |
|------------------------------|----------------------------------------|--------------------------------|
| `AIMON_DATABASE_URL`         | Async SQLAlchemy database URL          | `sqlite+aiosqlite:///aimon.db` |
| `AIMON_LOG_LEVEL`            | Log level (`DEBUG`, `INFO`, …)        | `INFO`                         |
| `AIMON_MAX_CONCURRENT`       | Max concurrent execution engine tasks  | `10`                           |
| `AIMON_GOOGLE_API_KEY`       | Google Custom Search API key           | *(none)*                       |
| `AIMON_GOOGLE_SEARCH_ENGINE` | Google Custom Search engine ID         | *(none)*                       |

Create a `.env` file in your project root:

```dotenv
AIMON_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/aimon
AIMON_LOG_LEVEL=DEBUG
AIMON_GOOGLE_API_KEY=AIza...
AIMON_GOOGLE_SEARCH_ENGINE=cx:...
```
