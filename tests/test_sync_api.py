"""
SECTION 10 — SYNC API TEST

Tests AIMONSync() synchronous wrapper.
Example:
  fw = AIMONSync()
  sources = fw.search_sources("movie download")

Verifies results returned correctly.
"""

import pytest
from aimon.sync import AIMONSync
from aimon.core.runtime import AIMONCoreRuntime


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test."""
    AIMONCoreRuntime.reset_instance()
    yield
    AIMONCoreRuntime.reset_instance()


def test_aimon_sync_can_be_instantiated():
    fw = AIMONSync()
    assert fw is not None


def test_aimon_sync_initialize():
    fw = AIMONSync()
    fw.initialize()  # should not raise
    fw.shutdown()


def test_search_sources_returns_non_empty_list():
    fw = AIMONSync()
    fw.initialize()
    try:
        sources = fw.search_sources("movie download")
        assert isinstance(sources, list)
        assert len(sources) > 0
    finally:
        fw.shutdown()


def test_search_sources_items_have_id_key():
    fw = AIMONSync()
    fw.initialize()
    try:
        sources = fw.search_sources("movie download")
        for source in sources:
            assert "id" in source
    finally:
        fw.shutdown()


def test_get_threats_returns_list():
    fw = AIMONSync()
    fw.initialize()
    try:
        fw.search_sources("movie download")
        threats = fw.get_threats()
        assert isinstance(threats, list)
    finally:
        fw.shutdown()


def test_get_alerts_returns_list():
    fw = AIMONSync()
    fw.initialize()
    try:
        fw.search_sources("movie download")
        alerts = fw.get_alerts()
        assert isinstance(alerts, list)
    finally:
        fw.shutdown()


def test_get_status_returns_dict_with_initialized_key():
    fw = AIMONSync()
    fw.initialize()
    try:
        status = fw.get_status()
        assert isinstance(status, dict)
        assert "initialized" in status
    finally:
        fw.shutdown()


def test_shutdown_runs_without_exception():
    fw = AIMONSync()
    fw.initialize()
    fw.shutdown()  # should not raise


def test_full_lifecycle():
    """initialize → search → get_threats → get_alerts → get_status → shutdown"""
    fw = AIMONSync()
    fw.initialize()

    sources = fw.search_sources("course torrent")
    assert isinstance(sources, list)

    threats = fw.get_threats()
    assert isinstance(threats, list)

    alerts = fw.get_alerts()
    assert isinstance(alerts, list)

    status = fw.get_status()
    assert isinstance(status, dict)
    assert status["initialized"] is True

    fw.shutdown()


def test_double_initialize_is_handled():
    """Second initialize() on an already-initialized instance should not raise."""
    fw = AIMONSync()
    fw.initialize()
    fw.initialize()  # should be a no-op
    fw.shutdown()


def test_search_sources_different_queries():
    fw = AIMONSync()
    fw.initialize()
    try:
        for query in ["movie download", "software crack", "leaked course"]:
            results = fw.search_sources(query)
            assert isinstance(results, list)
            assert len(results) > 0
    finally:
        fw.shutdown()


def test_no_async_await_in_tests():
    """All AIMONSync methods are sync — confirm they don't return coroutines."""
    import inspect
    fw = AIMONSync()
    fw.initialize()
    try:
        result = fw.search_sources("test")
        assert not inspect.iscoroutine(result)

        threats = fw.get_threats()
        assert not inspect.iscoroutine(threats)

        alerts = fw.get_alerts()
        assert not inspect.iscoroutine(alerts)

        status = fw.get_status()
        assert not inspect.iscoroutine(status)
    finally:
        fw.shutdown()
