# AIMON Framework Design & Architecture

## Overview

AIMON is an enterprise-grade, event-driven distributed systems framework for building intelligent monitoring and leak detection applications. It follows design principles from Scrapy, Airflow, and TensorFlow, providing a complete extension platform rather than a single-purpose tool.

## Core Design Principles

### 1. **Modularity**
Every component is pluggable and can be replaced:
- Modules can be added, removed, or updated without affecting others
- Connectors are interchangeable
- Storage backends are swappable
- Fingerprinting algorithms can be extended

### 2. **Event-Driven Architecture**
All module communication happens through an EventBus:
- Modules never call each other directly
- Events are the contract between components
- Adding new modules doesn't require changes to existing ones
- Enables complex workflows with minimal coupling

### 3. **Async-First**
The entire framework uses asyncio:
- Handles thousands of concurrent operations
- Non-blocking I/O throughout
- Efficient resource utilization
- Natural fit for network-heavy workloads

### 4. **Observability**
Built-in monitoring throughout:
- Structured logging at every layer
- Metrics collection
- Health checks
- Status reporting

### 5. **Extensibility**
Everything can be extended:
- Custom modules inherit from BaseModule
- Custom connectors inherit from BaseConnector
- Custom storage backends inherit from StorageBackend
- Plugin system for auto-discovery

## Architecture Layers

### Layer 1: Developer Application Layer
**Responsibility**: User code that builds monitoring systems

**Examples**:
- Custom leak detection app
- Brand protection monitoring system
- Content management tracking

**Interaction**: Uses AIMON class from Developer API Layer

---

### Layer 2: Developer API Layer
**Responsibility**: Clean, simple interface for developers

**Key Components**:
- `AIMON` class: Main entry point
- `AIMONSync`: Synchronous wrapper
- Factory functions

**Provides**:
```python
# Async usage
async with AIMON() as fw:
    sources = await fw.search_sources("query")
    threats = await fw.get_threats()

# Sync usage
fw = AIMONSync()
sources = fw.search_sources("query")
```

**Philosophy**: Hide complexity behind a simple interface

---

### Layer 3: Framework Runtime Layer
**Responsibility**: Orchestration and lifecycle management

**Key Component**: `AIMONCoreRuntime` (Singleton)

**Manages**:
- Module registration and initialization
- Module shutdown and cleanup
- Event bus coordination
- Execution engine lifecycle
- Plugin loading

**Lifecycle**:
1. Initialize runtime
2. Register modules
3. Start execution engines
4. Process events and tasks
5. Stop components on shutdown

---

### Layer 4: Service Container Layer
**Responsibility**: Dependency injection

**Key Component**: `ServiceContainer`

**Features**:
- Register services by name
- Lazy instantiation with factories
- Singleton pattern
- Simple API

**Usage**:
```python
container.register("db", database_instance)
service = container.get("db")

# Or with factory
container.register_factory("cache", lambda: RedisCache())
cache = container.get("cache")  # Instantiated on demand
```

---

### Layer 5: Execution Engine Layer
**Responsibility**: Async task scheduling and execution

**Key Component**: `ExecutionEngine`

**Features**:
- Priority-based task queue
- Concurrency limiting via semaphore
- Automatic retries with exponential backoff
- Timeout enforcement
- Result tracking

**Priority Levels**:
- `CRITICAL` (0) - System critical
- `HIGH` (1) - High priority
- `NORMAL` (2) - Default
- `LOW` (3) - Background tasks

**Usage**:
```python
task_id = await engine.submit(
    coro=crawl_url(url),
    priority=TaskPriority.HIGH,
    timeout=30,
    max_retries=3
)

result = await engine.get_result(task_id)
```

---

### Layer 6: Event Bus Layer
**Responsibility**: Pub/sub communication between modules

**Key Component**: `EventBus`

**Features**:
- Async handlers
- Sync handler support (runs in thread pool)
- Error isolation (one failing handler doesn't crash others)
- Event logging

**Event Flow**:
1. Module emits event: `await self.emit_event("event_type", data=...)`
2. EventBus queries handlers for event type
3. EventBus calls all handlers concurrently
4. Returns after all handlers complete

**Example Events**:
- `source_discovered` - New source found
- `page_crawled` - Content extracted
- `threat_detected` - Threat identified
- `alert_generated` - Alert created
- `custom_event` - User-defined events

---

### Layer 7: Module System Layer
**Responsibility**: Pluggable modules implementing business logic

**Base Class**: `BaseModule`

**Lifecycle States**:
```
UNINITIALIZED → INITIALIZING → READY
                    ↓
                  ERROR
                    ↓
         SHUTTING_DOWN → STOPPED
```

**Built-in Modules**:

1. **DiscoveryModule**
   - Finds sources matching a query
   - Emits `source_discovered` events
   - Uses connectors to search

2. **CrawlerModule**
   - Subscribes to `source_discovered` events
   - Extracts content from sources
   - Emits `page_crawled` events

3. **IntelligenceModule**
   - Subscribes to `page_crawled` events
   - Analyzes content for threats
   - Emits `threat_detected` events if threats found

4. **AlertsModule**
   - Subscribes to `threat_detected` events
   - Generates alert notifications
   - Can integrate with external systems

**Custom Module Example**:
```python
class MyModule(BaseModule):
    async def _initialize_impl(self):
        """Module-specific setup"""
        self.data = []
    
    async def _subscribe_to_events(self):
        """Subscribe to events"""
        await self.subscribe_event("page_crawled", self._on_page)
    
    async def _on_page(self, **data):
        """Handle event"""
        self.data.append(data)
        await self.emit_event("processed", count=len(self.data))
```

---

### Layer 8: Connector Layer
**Responsibility**: Integration with external data sources

**Base Class**: `BaseConnector`

**Features**:
- Async search and fetch
- Configuration support
- Credential management
- Error handling

**Built-in Connectors**:
- `GoogleConnector` - Search engine
- `RedditConnector` - Social platform
- `TelegramConnector` - Messaging
- `TorrentConnector` - P2P network

**Custom Connector Example**:
```python
class CustomConnector(BaseConnector):
    async def initialize(self):
        # Setup API credentials
        await super().initialize()
    
    async def search(self, query: str, **kwargs):
        # Call API and return results
        return []
    
    async def fetch(self, url: str, **kwargs):
        # Fetch content from URL
        return {}
```

---

### Layer 9: Storage Layer
**Responsibility**: Persistent data storage

**Base Class**: `StorageBackend`

**Operations**:
- `save(key, data, ttl)` - Persist data
- `get(key)` - Retrieve data
- `delete(key)` - Remove data
- `query(filter)` - Search data
- `count()` - Count items

**Implementations**:
1. **MemoryStorage**
   - In-memory dictionary
   - No persistence
   - Fast
   - Use for: testing, caching

2. **FileStorage**
   - JSON files on disk
   - Persistent
   - Human-readable
   - Use for: development, small deployments

3. **DatabaseStorage**
   - SQL database (PostgreSQL, MySQL, SQLite)
   - Scalable
   - Queryable
   - Use for: production

**Usage**:
```python
storage = MemoryStorage()
await storage.save("key", {"data": "value"})
result = await storage.get("key")

# Query
threats = await storage.query({"type": "threat"})
```

---

### Layer 10: Fingerprint Layer
**Responsibility**: Digital asset identification

**Base Class**: `BaseFingerprinter`

**Components**:
1. **VideoFingerprinter** - Frame-based matching
2. **AudioFingerprinter** - Spectral analysis
3. **PerceptualHasher** - Image similarity
4. **DocumentHasher** - Content hashing

**Usage**:
```python
engine = FingerprintEngine()

# Generate fingerprint
fp = await engine.fingerprint("video", video_data)

# Compare fingerprints
result = await engine.match("video", fp1, fp2, threshold=0.9)
# Returns: {"match": True/False, "similarity": 0.0-1.0}
```

---

### Layer 11: Observability Layer
**Responsibility**: Monitoring and metrics

**Components**:
1. **MetricsCollector**
   - Tracks framework metrics
   - Events, tasks, threats, alerts
   
2. **HealthMonitor**
   - Component health status
   - Error tracking
   - Overall system health

**Usage**:
```python
metrics = await framework.get_metrics()
# {
#   "events_emitted": 150,
#   "pages_crawled": 42,
#   "threats_detected": 5,
#   "alerts_generated": 5,
#   ...
# }

status = await framework.get_status()
# {
#   "initialized": True,
#   "runtime": {...},
#   "health": {...},
#   "metrics": {...}
# }
```

---

### Layer 12: Plugin Ecosystem Layer
**Responsibility**: Plugin auto-discovery and loading

**Features**:
- Auto-discover plugins in `aimon/plugins/` namespace
- Both built-in and third-party plugins
- No registration required

**Plugin Structure**:
```python
# aimon/plugins/my_plugin/__init__.py
class MyConnector(BaseConnector):
    ...

class MyModule(BaseModule):
    ...
```

**Plugins are automatically discovered and loaded** during runtime initialization.

## Design Patterns

### 1. Singleton Pattern
**Used for**: `AIMONCoreRuntime`

```python
runtime = AIMONCoreRuntime.get_instance()  # Always same object
```

**Reason**: Single source of truth, framework coordination

### 2. Observer Pattern
**Used for**: `EventBus` (pub/sub)

```python
await bus.subscribe("event", handler)
await bus.emit("event", value=123)
```

**Reason**: Loose coupling between modules

### 3. Registry Pattern
**Used for**: `ModuleRegistry`, `ServiceRegistry`

```python
registry.register(name, module)
module = registry.get(name)
```

**Reason**: Dynamic lookup, plugin support

### 4. Producer-Consumer Pattern
**Used for**: `ExecutionEngine` with task queue

```python
task_id = await engine.submit(coro)
# Producer: submits tasks
# Consumer: executor loop processes tasks
```

**Reason**: Async task processing, backpressure handling

### 5. Context Manager Pattern
**Used for**: `AIMON`, `create_framework()`

```python
async with AIMON() as fw:
    # Guaranteed cleanup
```

**Reason**: Resource management, clean initialization/shutdown

### 6. Strategy Pattern
**Used for**: Storage backends, connectors, fingerprinters

All inherit from base class, swap implementations:
```python
# Can switch storage without changing code
storage = MemoryStorage() or FileStorage() or DatabaseStorage()
```

**Reason**: Extensibility, testability

### 7. Factory Pattern
**Used for**: Service container

```python
container.register_factory("cache", lambda: RedisCache())
cache = container.get("cache")  # Creates on demand
```

**Reason**: Lazy instantiation, dependency injection

### 8. Pipeline Pattern
**Used for**: Module chain (Discovery → Crawler → Intelligence → Alerts)

```
DiscoveryModule emits source_discovered
    ↓
CrawlerModule receives → crawls → emits page_crawled
    ↓
IntelligenceModule receives → analyzes → emits threat_detected
    ↓
AlertsModule receives → generates alert
```

**Reason**: Clean data flow, composable workflows

## Event-Driven Workflow Example

### Scenario: Search for leaked courses

```python
async with AIMON() as fw:
    sources = await fw.search_sources("course download")
```

**What happens**:

1. **DiscoveryModule.search()** is called
2. Searches for sources (simulated or via connectors)
3. For each source found:
   - Emits `source_discovered` event with source data

4. **EventBus** receives `source_discovered` event
5. **EventBus** calls all subscribed handlers

6. **CrawlerModule._on_source_discovered()** receives event
7. Calls `crawler.crawl(source)`
8. Extracts content, emits `page_crawled` event

9. **EventBus** receives `page_crawled` event
10. **IntelligenceModule._on_page_crawled()** receives event
11. Analyzes content for threats
12. If threat detected: emits `threat_detected` event

13. **EventBus** receives `threat_detected` event
14. **AlertsModule._on_threat_detected()** receives event
15. Generates alert, emits `alert_generated` event

16. User retrieves results:
    - `fw.get_threats()` → Threats detected
    - `fw.get_alerts_list()` → Alerts generated

## Concurrency Model

### Async Everywhere
- All I/O is non-blocking
- No thread pools (except for executor service)
- Natural concurrency with asyncio

### ExecutionEngine Limits
```python
# Semaphore limits concurrent tasks
config = {
    "execution.max_concurrent": 50,  # Max 50 simultaneous tasks
    "execution.timeout": 60,         # 60 second default timeout
}
```

### Event Handling
```python
# All handlers for an event run concurrently
# gather() waits for all handlers
await bus.emit("event")  # Waits for all handlers
```

## Error Handling

### Module Errors
- Module goes to ERROR state
- Module operations fail gracefully
- Other modules continue

### Event Handler Errors
- Individual handler errors are caught and logged
- Other handlers for same event continue
- Event processing completes successfully

### Task Errors
- Task goes to FAILED state
- Retries occur if configured
- Result is available for inspection

## Configuration Management

### Sources (Priority Order)
1. **Environment Variables** (highest)
   - `EXECUTION_MAX_CONCURRENT=100`
2. **Configuration Dictionary**
   - `{"execution.max_concurrent": 50}`
3. **Default Values** (lowest)

### Usage
```python
# Environment variable
export EXECUTION_MAX_CONCURRENT=100

# Code
config = {"storage.type": "file"}
async with AIMON(config) as fw:
    # execution.max_concurrent = 100 (from env)
    # storage.type = "file" (from config)
```

## Performance Considerations

### Memory
- Event-driven = low overhead
- MemoryStorage should be sized appropriately
- Store large results in FileStorage/DatabaseStorage

### CPU
- Async execution = efficient use of cores
- Increase `max_concurrent` for I/O-bound work
- CPU-bound tasks should be offloaded

### Throughput
- Typical: 100s of sources per search
- Can process 1000s of events per second
- Bottleneck usually at data sources (crawl speed)

## Testing Strategy

### Unit Tests
- Test individual components (modules, connectors, storage)
- Mock event bus and runtime
- Use async test fixtures

### Integration Tests
- Test complete workflows
- Multiple modules interacting
- Event chain verification

### Performance Tests
- Task throughput
- Memory usage
- Concurrent handler execution

## Extension Points

### Where to Add Functionality

1. **New Module**: Inherit from `BaseModule`
   - Logic for new processing step
   - Emit custom events

2. **New Connector**: Inherit from `BaseConnector`
   - New data source

3. **New Storage**: Inherit from `StorageBackend`
   - Persistence mechanism

4. **New Fingerprinter**: Inherit from `BaseFingerprinter`
   - Asset matching algorithm

5. **Custom Module Chain**:
   - Register modules in specific order
   - Subscribe to appropriate events

## Best Practices

### For Framework Users

1. **Use context managers**
   ```python
   async with AIMON() as fw:
       # Guaranteed cleanup
   ```

2. **Configure appropriately**
   ```python
   config = {
       "execution.max_concurrent": 50,  # Based on resources
       "storage.type": "file",          # Persistent
   }
   ```

3. **Monitor status**
   ```python
   status = await fw.get_status()
   if status["health"]["status"] == "critical":
       # Handle issue
   ```

4. **Use appropriate storage for scale**
   - Development: MemoryStorage
   - Staging: FileStorage
   - Production: DatabaseStorage

### For Framework Developers

1. **Extend via plugins, not core**
   - Add in `aimon/plugins/`
   - Auto-discovered

2. **Follow async patterns**
   - All I/O is async
   - Use `await` for async calls
   - Never block the event loop

3. **Emit meaningful events**
   - Describe what happened
   - Include relevant data
   - Allow other modules to react

4. **Handle errors gracefully**
   - Log errors
   - Continue processing
   - Don't crash the framework

## Summary

AIMON is built on solid architectural principles:

- **Modularity** through plugins and service container
- **Decoupling** through event bus
- **Concurrency** through async-first design
- **Extensibility** through inheritance and composition
- **Observability** through built-in metrics
- **Simplicity** through clean API

This makes it suitable for building everything from small monitoring scripts to large-scale intelligence platforms.
