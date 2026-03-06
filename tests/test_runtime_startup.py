"""
SECTION 1 — FRAMEWORK STARTUP TEST

Tests that AIMONCoreRuntime initializes correctly.
Verifies:
  - event_bus running
  - execution_engine running
  - service_container active
  - module_registry initialized
  - All services accessible
  - No exceptions during startup
"""

import pytest
from aimon.core.runtime import AIMONCoreRuntime
from aimon.core.base_module import BaseModule, ModuleState


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before and after each test."""
    AIMONCoreRuntime.reset_instance()
    yield
    AIMONCoreRuntime.reset_instance()


async def test_runtime_initializes_without_exception():
    """Runtime should initialize without raising any exception."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    assert rt._initialized is True


async def test_runtime_event_bus_is_not_none():
    """event_bus should be available after initialize()."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    assert rt.event_bus is not None


async def test_runtime_execution_engine_is_not_none():
    """execution_engine should be available after initialize()."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    assert rt.execution_engine is not None


async def test_runtime_service_container_is_not_none():
    """service_container should be available after initialize()."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    assert rt.service_container is not None


async def test_runtime_module_registry_is_not_none():
    """module_registry should be available after initialize()."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    assert rt.module_registry is not None


async def test_runtime_state_started_at_is_set():
    """state.started_at should be set after initialize()."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    assert rt.state.started_at is not None


async def test_runtime_service_container_has_event_bus():
    """service_container should have 'event_bus' registered."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    eb = rt.service_container.get("event_bus")
    assert eb is not None


async def test_runtime_is_ready_with_ready_modules():
    """is_ready() should return True when all registered modules are ready."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()

    class ReadyModule(BaseModule):
        async def _initialize_impl(self):
            pass

    module = ReadyModule("ready_module")
    await rt.register_module("ready", module)

    assert rt.is_ready() is True


async def test_runtime_start_completes():
    """start() should complete without exception."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    await rt.start()
    assert rt._running is True
    await rt.stop()


async def test_runtime_stop_completes_gracefully():
    """stop() should complete without exception."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    await rt.start()
    await rt.stop()
    assert rt._running is False


async def test_runtime_singleton_behavior():
    """get_instance() returns the same object each time."""
    rt1 = AIMONCoreRuntime.get_instance()
    rt2 = AIMONCoreRuntime.get_instance()
    assert rt1 is rt2


async def test_runtime_reset_instance_creates_new_instance():
    """reset_instance() causes next get_instance() to return a fresh object."""
    rt1 = AIMONCoreRuntime.get_instance()
    AIMONCoreRuntime.reset_instance()
    rt2 = AIMONCoreRuntime.get_instance()
    assert rt1 is not rt2


async def test_runtime_double_initialize_is_noop():
    """Calling initialize() twice should not raise — second call is no-op."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    await rt.initialize()  # should not raise
    assert rt._initialized is True


async def test_runtime_get_status_returns_dict():
    """get_status() should return a dict with 'initialized' key."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize()
    status = rt.get_status()
    assert isinstance(status, dict)
    assert "initialized" in status
    assert status["initialized"] is True


async def test_runtime_with_config():
    """initialize() should accept a config_dict without error."""
    rt = AIMONCoreRuntime.get_instance()
    await rt.initialize(config_dict={"execution.max_concurrent": 5})
    assert rt._initialized is True
