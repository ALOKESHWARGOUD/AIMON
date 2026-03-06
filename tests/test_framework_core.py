"""
Tests for AIMON Framework Core - Runtime, EventBus, ExecutionEngine.
"""

import pytest
import asyncio
from aimon.core.runtime import AIMONCoreRuntime
from aimon.core.event_bus import EventBus, Event
from aimon.core.execution_engine import ExecutionEngine, TaskPriority, TaskState
from aimon.core.base_module import BaseModule, ModuleState


# Setup
@pytest.fixture
def event_loop():
    """Create event loop for tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
async def runtime():
    """Create test runtime."""
    AIMONCoreRuntime.reset_instance()
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    yield rt
    await rt.stop()


# Test EventBus
@pytest.mark.asyncio
async def test_event_bus_creation():
    """Test event bus creation."""
    bus = EventBus()
    await bus.initialize()
    assert bus is not None


@pytest.mark.asyncio
async def test_event_bus_subscribe():
    """Test event subscription."""
    bus = EventBus()
    await bus.initialize()
    
    received_events = []
    
    async def handler(event: Event):
        received_events.append(event)
    
    await bus.subscribe("test_event", handler)
    await bus.emit("test_event", source="test")
    
    await asyncio.sleep(0.1)
    assert len(received_events) == 1
    assert received_events[0].event_type == "test_event"


@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    """Test event unsubscription."""
    bus = EventBus()
    await bus.initialize()
    
    received = []
    
    async def handler(event: Event):
        received.append(event)
    
    await bus.subscribe("test", handler)
    await bus.unsubscribe("test", handler)
    await bus.emit("test", source="test")
    
    await asyncio.sleep(0.1)
    assert len(received) == 0


# Test ExecutionEngine
@pytest.mark.asyncio
async def test_execution_engine_submit_task():
    """Test task submission."""
    engine = ExecutionEngine(max_concurrent=2)
    await engine.start()
    
    async def dummy_task():
        await asyncio.sleep(0.1)
        return "done"
    
    task_id = await engine.submit(dummy_task(), priority=TaskPriority.NORMAL)
    assert task_id is not None
    
    await asyncio.sleep(0.5)
    result = await engine.get_result(task_id)
    assert result.state == TaskState.COMPLETED
    assert result.result == "done"
    
    await engine.stop()


@pytest.mark.asyncio
async def test_execution_engine_priority():
    """Test task priority ordering."""
    engine = ExecutionEngine(max_concurrent=1)
    await engine.start()
    
    results = []
    
    async def task(name, delay=0.1):
        await asyncio.sleep(delay)
        results.append(name)
        return name
    
    # Submit tasks in order: normal, low, high
    await engine.submit(task("normal", 0.1), priority=TaskPriority.NORMAL)
    await engine.submit(task("low", 0.1), priority=TaskPriority.LOW)
    await engine.submit(task("high", 0.1), priority=TaskPriority.HIGH)
    
    await asyncio.sleep(1)
    
    # High priority should execute first
    assert results[0] == "high"
    
    await engine.stop()


# Test Runtime
@pytest.mark.asyncio
async def test_runtime_initialization(runtime):
    """Test runtime initialization."""
    assert runtime is not None
    assert runtime.is_ready()


@pytest.mark.asyncio
async def test_runtime_register_module(runtime):
    """Test module registration."""
    class TestModule(BaseModule):
        async def _initialize_impl(self):
            pass
    
    module = TestModule("test_module")
    await runtime.register_module("test", module)
    
    registered = runtime.get_module("test")
    assert registered is not None
    assert registered.name == "test_module"


@pytest.mark.asyncio
async def test_runtime_emit_event(runtime):
    """Test event emission."""
    received = []
    
    async def handler(**data):
        received.append(data)
    
    bus = runtime.event_bus
    await bus.subscribe("test_event", handler)
    
    await runtime.emit_event("test_event", test_data="test_value")
    
    await asyncio.sleep(0.1)
    assert len(received) > 0


# Test BaseModule
@pytest.mark.asyncio
async def test_base_module_lifecycle():
    """Test module lifecycle."""
    init_called = []
    shutdown_called = []
    
    class TestModule(BaseModule):
        async def _initialize_impl(self):
            init_called.append(True)
        
        async def _shutdown_impl(self):
            shutdown_called.append(True)
    
    module = TestModule("test")
    bus = EventBus()
    await bus.initialize()
    module.event_bus = bus
    
    assert module.state == ModuleState.UNINITIALIZED
    
    await module.initialize()
    assert module.state == ModuleState.READY
    assert len(init_called) == 1
    
    await module.shutdown()
    assert module.state == ModuleState.STOPPED
    assert len(shutdown_called) == 1


@pytest.mark.asyncio
async def test_module_event_subscription():
    """Test module event subscription."""
    received = []
    
    class TestModule(BaseModule):
        async def _initialize_impl(self):
            pass
        
        async def _subscribe_to_events(self):
            await self.subscribe_event("test_event", self._on_test_event)
        
        async def _on_test_event(self, **data):
            received.append(data)
    
    module = TestModule("test")
    bus = EventBus()
    await bus.initialize()
    module.event_bus = bus
    
    await module.initialize()
    
    await module.emit_event("test_event", value="test")
    await asyncio.sleep(0.1)
    
    assert len(received) == 1
    assert received[0].get("value") == "test"


# Test ServiceContainer
@pytest.mark.asyncio
async def test_service_container():
    """Test service container."""
    from aimon.core.service_container import ServiceContainer
    
    container = ServiceContainer()
    
    class Service:
        def __init__(self, name):
            self.name = name
    
    service = Service("test_service")
    container.register("service", service)
    
    retrieved = container.get("service")
    assert retrieved is service
    assert retrieved.name == "test_service"


# Test ConfigManager
@pytest.mark.asyncio
async def test_config_manager():
    """Test configuration manager."""
    from aimon.core.config_manager import ConfigManager
    
    config = ConfigManager()
    
    config.set("test.key", "value")
    assert config.get("test.key") == "value"
    
    config.set("logging.level", "DEBUG")
    assert config.get("logging.level") == "DEBUG"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
