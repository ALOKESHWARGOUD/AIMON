# AIMON Framework — Architecture

## Layer Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1 — Developer API  (AIMON / AIMONSync / CLI)     │
├─────────────────────────────────────────────────────────┤
│  Layer 2 — Core Runtime  (AIMONCoreRuntime singleton)   │
├───────────────────────┬─────────────────────────────────┤
│  Layer 3 — EventBus   │  Layer 4 — ExecutionEngine      │
├───────────────────────┴─────────────────────────────────┤
│  Layer 5 — Module System                                │
│  DiscoveryModule · CrawlerModule · IntelligenceModule   │
│  AlertsModule                                           │
├─────────────────────────────────────────────────────────┤
│  Layer 6 — Connector Layer                              │
│  GoogleConnector · RedditConnector · TelegramConnector  │
│  TorrentConnector                                       │
├─────────────────────────────────────────────────────────┤
│  Layer 7 — Storage Layer                                │
│  MemoryStorage · FileStorage · DatabaseStorage          │
├─────────────────────────────────────────────────────────┤
│  Layer 8 — Fingerprint Layer                            │
│  VideoFingerprinter · AudioFingerprinter                │
│  PerceptualHasher · DocumentHasher · FingerprintEngine  │
├─────────────────────────────────────────────────────────┤
│  Layer 9 — Observability                                │
│  MetricsCollector · HealthChecker                       │
├─────────────────────────────────────────────────────────┤
│  Layer 10 — Plugin System  (PluginEngine + namespace)   │
└─────────────────────────────────────────────────────────┘
```

---

## Layer Descriptions

### Layer 1 — Developer API
`AIMON` (async context manager), `AIMONSync` (blocking wrapper), and the
`aimon` CLI.  This is the only layer end-users interact with directly.

### Layer 2 — Core Runtime
`AIMONCoreRuntime` is a singleton that boots the framework, wires all
components together, and exposes `register_module`, `emit_event`, and
`get_status`.

### Layer 3 — EventBus
Async publish/subscribe bus.  Modules talk to each other exclusively
through typed events — no direct references between modules.  Supports
`subscribe`, `unsubscribe`, `emit`, and `clear`.

### Layer 4 — ExecutionEngine
Priority-based async task queue with configurable concurrency
(`max_concurrent`).  Supports `CRITICAL`, `HIGH`, `NORMAL`, and `LOW`
priorities, per-task timeouts, and result retrieval.

### Layer 5 — Module System
`BaseModule` defines the lifecycle contract.  Built-in modules:
- **DiscoveryModule** — searches connectors for potential leak sources
- **CrawlerModule** — fetches page content for each discovered source
- **IntelligenceModule** — scores and classifies crawled pages
- **AlertsModule** — generates and dispatches alerts for confirmed threats

### Layer 6 — Connector Layer
`BaseConnector` defines `search()` and `fetch()`.  Built-in connectors:
- **GoogleConnector** — Google Custom Search API / DuckDuckGo fallback
- **RedditConnector** — Reddit public JSON API
- **TelegramConnector** — Telegram channel monitoring
- **TorrentConnector** — Torrent search sites

### Layer 7 — Storage Layer
`StorageBackend` defines a key-value interface (`save`, `get`, `delete`,
`query`, `count`).  Built-in backends:
- **MemoryStorage** — in-memory dict (testing / caching)
- **FileStorage** — JSON files on disk (development)
- **DatabaseStorage** — async SQLAlchemy (`sqlite+aiosqlite` or `postgresql+asyncpg`)

### Layer 8 — Fingerprint Layer
`BaseFingerprinter` defines `fingerprint(data)` and `compare(fp1, fp2)`.
- **VideoFingerprinter** — SHA-256 over sampled OpenCV frames
- **AudioFingerprinter** — Mel-spectrogram vector (librosa)
- **PerceptualHasher** — Hamming-distance image similarity
- **DocumentHasher** — SHA-512 of document content
- **FingerprintEngine** — routes to the correct fingerprinter by asset type

### Layer 9 — Observability
`MetricsCollector` aggregates runtime counters.  `HealthChecker` exposes
a `/health` endpoint and summary dict.

### Layer 10 — Plugin System
`PluginEngine` auto-discovers plugins from the `aimon.plugins.*` namespace
and exposes `register_plugin` / `get_plugin` / `get_plugins_by_type`.

---

## Event Flow

```
DiscoveryModule.search()
    └─► emit "source_discovered"
            └─► CrawlerModule._on_source_discovered()
                    └─► crawl URL
                    └─► emit "page_crawled"
                            └─► IntelligenceModule._on_page_crawled()
                                    └─► analyze content
                                    └─► emit "threat_detected"  (if score > threshold)
                                            └─► AlertsModule._on_threat_detected()
                                                    └─► generate + send alert
                                                    └─► emit "alert_generated"
```

---

## Module Lifecycle States

```
UNINITIALIZED
    │
    ▼ initialize()
INITIALIZING
    │
    ▼ (success)
READY  ◄──────────────── normal operation
    │
    ▼ shutdown()
SHUTTING_DOWN
    │
    ▼
STOPPED
```

Errors during initialization transition the module to `ERROR` state.

---

## Plugin Extension Points

| Extension Point    | Base Class          | Registration method              |
|--------------------|---------------------|----------------------------------|
| Connector          | `BaseConnector`     | `PluginEngine.register_plugin("connector", ...)` |
| Storage backend    | `StorageBackend`    | `PluginEngine.register_plugin("storage", ...)`   |
| Fingerprinter      | `BaseFingerprinter` | `PluginEngine.register_plugin("fingerprint", ...)` |
| Module             | `BaseModule`        | `AIMONCoreRuntime.register_module(...)`           |
