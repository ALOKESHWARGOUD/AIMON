# AIMON Framework — Quick Start Guide

## Installation

```bash
pip install aimon-framework
```

---

## 30-Second Demo

After installing, run the included demo:

```bash
git clone https://github.com/ALOKESHWARGOUD/AIMON.git
cd AIMON
pip install -e .
python examples/demo_leak_monitor.py
```

No API keys needed. The demo uses memory storage and shows the full pipeline.

---

## Optional Extras

| Extra                 | Installs              | Enables                              |
|-----------------------|-----------------------|--------------------------------------|
| `[telegram]`          | telethon              | Telegram channel scanning            |
| `[neo4j]`             | neo4j, networkx       | Graph-based leak network storage     |
| `[fingerprint]`       | opencv, librosa, PIL  | Video/audio/image fingerprinting     |
| `[postgres]`          | asyncpg, sqlalchemy   | PostgreSQL storage backend           |
| `[redis]`             | redis                 | Redis storage backend                |
| `[monitoring]`        | prometheus-client     | Prometheus metrics export            |
| `[storage-postgres]`  | asyncpg               | Lightweight async PostgreSQL driver  |
| `[dev]`               | pytest, black, ruff   | Development and testing tools        |
| `[all]`               | Everything above      | Full installation                    |

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

Copy `.env.example` to `.env` and fill in the values you need.

| Variable                        | Description                         | Required For          |
|---------------------------------|-------------------------------------|-----------------------|
| `AIMON_GOOGLE_API_KEY`          | Google Custom Search API key        | Web discovery         |
| `AIMON_GOOGLE_SEARCH_ENGINE_ID` | Google Custom Search engine ID      | Web discovery         |
| `AIMON_TELEGRAM_API_ID`         | Telegram API ID (from my.telegram)  | Telegram scanning     |
| `AIMON_TELEGRAM_API_HASH`       | Telegram API hash                   | Telegram scanning     |
| `AIMON_NEO4J_URI`               | Neo4j connection URI                | Graph storage         |
| `AIMON_NEO4J_USER`              | Neo4j username                      | Graph storage         |
| `AIMON_NEO4J_PASSWORD`          | Neo4j password                      | Graph storage         |
| `AIMON_REDIS_URL`               | Redis connection URL                | Redis storage         |
| `AIMON_DATABASE_URL`            | Async SQLAlchemy database URL       | All (default: SQLite) |
| `AIMON_LOG_LEVEL`               | Logging level (DEBUG/INFO/WARNING)  | All                   |
| `AIMON_MAX_CONCURRENT`          | Max concurrent execution tasks      | All (default: 10)     |

Create a `.env` file in your project root:

```dotenv
AIMON_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/aimon
AIMON_LOG_LEVEL=DEBUG
AIMON_GOOGLE_API_KEY=AIza...
AIMON_GOOGLE_SEARCH_ENGINE_ID=cx:...
```
