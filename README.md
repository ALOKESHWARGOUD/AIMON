# AIMON - Enterprise-Grade AI Monitoring Framework

**AIMON** is a production-ready, distributed systems framework for building intelligent monitoring, leak detection, and intelligence analysis platforms. It's designed like Scrapy and Airflow—providing a true developer framework, not just a monitoring script.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Features

### Core Framework
- **Modular Architecture**: Plug-and-play modules for discovery, crawling, analysis, and alerts
- **Event-Driven Communication**: All modules communicate via async EventBus (loose coupling)
- **Async-First**: Full asyncio-based execution for high concurrency
- **Plugin Ecosystem**: Extensible connector, storage, and fingerprint systems
- **Service Container**: Built-in dependency injection
- **Execution Engine**: Priority-based async task queue with retries and timeouts

### Key Capabilities
- **Source Discovery**: Find data sources across multiple platforms (Google, Reddit, Telegram, Torrents)
- **Web Crawling**: Extract content from discovered sources
- **Intelligent Analysis**: Detect leaked digital assets using fingerprinting
- **Threat Detection**: Identify potential security risks
- **Alert Generation**: Automatic notifications and reporting
- **Observable**: Structured logging, metrics collection, health monitoring

### Extensibility
- **Custom Modules**: Build domain-specific modules inheriting from BaseModule
- **Pluggable Connectors**: Add new data source integrations
- **Storage Backends**: Switch between memory, file, or database storage
- **Fingerprinting Algorithms**: Implement custom asset identification
- **CLI Tool**: Full command-line interface

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/aimon.git
cd aimon
pip install -e ".[dev]"
```

### Basic Usage (Async)

```python
from aimon import AIMON
import asyncio

async def main():
    async with AIMON() as framework:
        # Search for sources
        sources = await framework.search_sources("course download")
        
        # Crawler, intelligence, and alerts automatically process
        # Get results
        threats = await framework.get_threats()
        alerts = await framework.get_alerts_list()
        
        print(f"Found {len(threats)} threats in {len(sources)} sources")

asyncio.run(main())
```

### Synchronous Usage

```python
from aimon.sync import AIMONSync

fw = AIMONSync()
fw.initialize()

# Use synchronously
sources = fw.search_sources("movie download")
threats = fw.get_threats()

fw.shutdown()
```

### CLI Tool

```bash
# Scan for sources
aimon scan "course download" --limit 20 --output results.json

# Monitor continuously
aimon monitor --duration 3600 --interval 60

# Show status
aimon status

# Show alerts
aimon alerts

# Show threats
aimon threats
```

## Architecture Layers

```
Developer Application Layer
          ↓
Developer API Layer (AIMON class)
          ↓
Framework Runtime Layer (AIMONCoreRuntime)
          ↓
Service Container Layer (Dependency Injection)
          ↓
Execution Engine (Async Task Queue)
          ↓
Event Bus (Pub/Sub Communication)
          ↓
Module System (DiscoveryModule, CrawlerModule, etc.)
          ↓
Connector Layer (Data Source Integration)
          ↓
Storage Layer (Persistence backends)
          ↓
Fingerprint Layer (Asset Identification)
          ↓
Observability Layer (Metrics, Logging, Health)
```

## Key Components

### Core Runtime
- **AIMONCoreRuntime**: Central orchestrator managing modules, events, and execution
- **BaseModule**: Abstract base for all framework modules
- **EventBus**: Pub/sub system for module communication
- **ExecutionEngine**: Priority-based async task scheduler
- **ServiceContainer**: Dependency injection container

### Built-in Modules
- **DiscoveryModule**: Search for sources
- **CrawlerModule**: Extract content from sources
- **IntelligenceModule**: Analyze content and detect threats
- **AlertsModule**: Generate and send alerts

### Connectors
- **GoogleConnector**: Search engine integration
- **RedditConnector**: Subreddit monitoring
- **TelegramConnector**: Channel monitoring
- **TorrentConnector**: Torrent network monitoring

### Storage Backends
- **MemoryStorage**: In-memory (testing, caching)
- **FileStorage**: File-based JSON storage
- **DatabaseStorage**: SQL database support

### Fingerprinting
- **VideoFingerprinter**: Video identification
- **AudioFingerprinter**: Audio identification
- **PerceptualHasher**: Image similarity
- **DocumentHasher**: Content hashing

## Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific module
pytest tests/test_modules.py -v

# With coverage
pytest tests/ --cov=aimon

# Run specific test
pytest tests/test_framework_core.py::test_event_bus_creation -v
```

## Building Custom Modules

```python
from aimon.core.base_module import BaseModule

class MyModule(BaseModule):
    async def _initialize_impl(self):
        """Initialize the module."""
        pass
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        await self.subscribe_event("page_crawled", self._on_page_crawled)
    
    async def _on_page_crawled(self, **data):
        """Handle events."""
        page = data.get("page")
        # Process content
        await self.emit_event("custom_event", result="data")

# Register with framework
async with AIMON() as framework:
    module = MyModule("my_module")
    await framework.runtime.register_module("my_module", module)
```

## Project Structure

```
aimon/
├── __init__.py              # Package entry point
├── framework_api.py         # Developer API (AIMON class)
├── core/                    # Core framework
│   ├── runtime.py          # AIMONCoreRuntime
│   ├── base_module.py      # BaseModule abstract class
│   ├── event_bus.py        # EventBus pub/sub
│   ├── execution_engine.py # Async task engine
│   ├── service_container.py # DI container
│   ├── config_manager.py   # Configuration
│   └── module_registry.py  # Module tracking
├── modules/                 # Built-in modules
│   ├── discovery.py        # Source discovery
│   ├── crawler.py          # Web crawling
│   ├── intelligence.py     # Content analysis
│   └── alerts.py           # Alert generation
├── connectors/             # Data source connectors
│   ├── base.py            # BaseConnector
│   ├── google_connector.py
│   ├── reddit_connector.py
│   ├── telegram_connector.py
│   └── torrent_connector.py
├── storage/               # Storage backends
│   ├── base.py
│   ├── memory_storage.py
│   ├── file_storage.py
│   └── database_storage.py
├── fingerprint/          # Asset fingerprinting
│   └── engine.py
├── observability/        # Monitoring
│   ├── metrics.py
│   └── health.py
├── sync/                # Synchronous wrapper
│   └── sync_api.py
└── cli/                 # Command-line interface
    └── main.py

tests/
├── test_framework_core.py      # Runtime, EventBus, ExecutionEngine
├── test_modules.py             # Module tests
└── test_storage_connectors.py  # Storage and connector tests

examples/
├── basic_monitoring.py    # Simple async example
├── sync_example.py       # Synchronous usage
└── custom_module.py      # Building custom modules

pyproject.toml            # Project configuration
README.md                # This file
```

## Configuration

Configuration can come from:
1. Environment variables (highest priority)
2. Configuration files (YAML/JSON)
3. Programmatic config passed to AIMON()

```python
config = {
    "execution.max_concurrent": 20,
    "execution.timeout": 120,
    "storage.type": "file",
    "logging.level": "INFO",
}

async with AIMON(config) as fw:
    ...
```

## Framework Patterns

### Simple Search
```python
async with AIMON() as fw:
    sources = await fw.search_sources("query")
    threats = await fw.get_threats()
```

### Custom Module Integration
```python
class CustomAnalyzer(BaseModule):
    async def _initialize_impl(self):
        pass
    
    async def _subscribe_to_events(self):
        await self.subscribe_event("threat_detected", self._analyze)

async with AIMON() as fw:
    analyzer = CustomAnalyzer("analyzer")
    await fw.runtime.register_module("analyzer", analyzer)
```

### Direct Runtime Control
```python
from aimon.core.runtime import get_runtime

runtime = get_runtime()
await runtime.initialize()

module = MyModule("test")
await runtime.register_module("test", module)

await runtime.emit_event("custom", data="value")
```

## Performance Characteristics

- **Concurrency**: Configurable worker threads via semaphore
- **Memory**: Efficient event-driven design
- **Latency**: Sub-second event propagation
- **Scalability**: Horizontal scaling via multiple instances

## Production Deployment

For production:

1. Use `FileStorage` or `DatabaseStorage` instead of `MemoryStorage`
2. Enable structured logging with JSON output
3. Configure metrics collection for monitoring
4. Use health checks for service orchestration
5. Set appropriate concurrency limits based on resources

```python
config = {
    "storage.type": "database",
    "storage.database_url": "postgresql://user:pass@host/db",
    "execution.max_concurrent": 50,
    "logging.level": "WARNING",
    "logging.format": "json",
}

async with AIMON(config) as fw:
    status = await fw.get_status()
    # Integrate with monitoring systems
```

## 🧪 Test Coverage

AIMON v1 includes **196 automated tests** covering the full framework lifecycle, event pipeline, connectors, fingerprinting, and monitoring engine.

### Test Files

| File                                     | Coverage                                                                                  |
| ---------------------------------------- | ----------------------------------------------------------------------------------------- |
| `tests/conftest.py`                      | Shared fixtures: event_bus, runtime, fresh_runtime, memory_storage, all_modules           |
| `tests/test_runtime_startup.py`          | AIMONCoreRuntime singleton lifecycle, service container registration, start/stop          |
| `tests/test_module_lifecycle.py`         | UNINITIALIZED → INITIALIZING → READY → SHUTTING_DOWN → STOPPED lifecycle                  |
| `tests/test_event_pipeline.py`           | Full async pipeline: source_discovered → page_crawled → threat_detected → alert_generated |
| `tests/test_connectors_real.py`          | Google, Reddit, Telegram, Torrent connectors with fallback                                |
| `tests/test_crawler.py`                  | Page crawling, event emission, deduplication                                              |
| `tests/test_database_storage.py`         | MemoryStorage TTL expiry, SQLite CRUD, FileStorage JSON persistence                       |
| `tests/test_fingerprint.py`              | VideoFingerprinter, AudioFingerprinter determinism & hashing                              |
| `tests/test_cli.py`                      | CLI commands via CliRunner                                                                |
| `tests/test_sync_api.py`                 | AIMONSync lifecycle validation                                                            |
| `tests/test_real_monitoring_pipeline.py` | Multi-query monitoring and event verification                                             |
| `tests/test_validation_report.py`        | Full subsystem validation report                                                          |

---

## ⚙ Key Design Notes

* `asyncio_mode = "auto"` configured in `pyproject.toml`
* Singleton isolation via `AIMONCoreRuntime.reset_instance()`
* Async validation runs inside `ThreadPoolExecutor`
* Framework core files were **not modified**, existing APIs were reused

---

## 📊 Validation Report (Sample)

```
AIMON v1 Validation Report

Total Systems Checked: 14
Passed: 14
Failed: 0

Performance Metrics
EventBus: 4132.2 ev/s
ExecutionEngine: 197.3 t/s
Pipeline Latency: 9.0 ms

AIMON v1: PRODUCTION READY ✓
```

<img width="889" height="587" alt="image" src="https://github.com/user-attachments/assets/7b417865-f7d8-4ccb-a18e-af2b4c18594e" />


## 🖥 AIMON Monitoring Dashboard

The AIMON dashboard provides a real-time visualization of the monitoring pipeline, module status, and threat detection activity.

### Framework Architecture View

![AIMON Architecture](assets/dashboard/aimon-dashboard-architecture.png)

The architecture graph visualizes the AIMON runtime pipeline:

Runtime → Event Bus → Discovery → Crawler → Intelligence → Alerts

---

### Monitoring & Metrics Panel

![AIMON Metrics](assets/dashboard/aimon-dashboard-metrics.png)

The monitoring panel displays:

* Live event stream
* Threat detection alerts
* Module health status
* Framework performance metrics
* Events per second
* Task execution latency

* <img width="1906" height="916" alt="image" src="https://github.com/user-attachments/assets/f75101b1-e8ba-41d3-bb0e-be3856aa0fef" />
* <img width="1886" height="892" alt="image" src="https://github.com/user-attachments/assets/95e95430-f1a3-426e-879b-f2a9554cf442" />





## Contributing

Contributions welcome! Areas for enhancement:

- Additional connector integrations
- Fingerprinting algorithm improvements
- Database storage implementations
- Frontend dashboard
- Kubernetes operator

## License

MIT License - See LICENSE file

## Documentation

- [FRAMEWORK_DESIGN.md](docs/FRAMEWORK_DESIGN.md) - Complete architecture
- [QUICKSTART.md](docs/QUICKSTART.md) - Getting started guide
- [API.md](docs/API.md) - API reference

## Contact & Support

For issues, questions, or contributions, visit the GitHub repository.

---

**AIMON**: Building intelligent monitoring platforms that scale.


