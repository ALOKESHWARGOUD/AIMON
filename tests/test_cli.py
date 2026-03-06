"""
SECTION 9 — CLI TEST

Tests commands:
  aimon scan "movie download"
  aimon status
  aimon threats
  aimon alerts

Verifies commands run successfully (exit code 0 or 0/2).
"""

import pytest
from click.testing import CliRunner
from aimon.cli.main import cli
from aimon.core.runtime import AIMONCoreRuntime


@pytest.fixture(autouse=True)
def reset_runtime_singleton():
    """Reset singleton before each CLI test to avoid cross-test contamination."""
    AIMONCoreRuntime.reset_instance()
    yield
    AIMONCoreRuntime.reset_instance()


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "AIMON" in result.output


def test_scan_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0


def test_scan_command_exits_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "movie download"])
    assert result.exit_code == 0


def test_scan_output_contains_scanning():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "movie download"])
    assert "Scanning" in result.output or "scanning" in result.output.lower()


def test_scan_output_contains_sources():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "movie download"])
    output_lower = result.output.lower()
    assert "sources" in output_lower or "found" in output_lower or "scanning" in output_lower


def test_status_command_exits_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0


def test_status_output_has_content():
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert len(result.output) > 0


def test_threats_command_exits_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["threats"])
    assert result.exit_code == 0


def test_alerts_command_exits_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["alerts"])
    assert result.exit_code == 0


def test_scan_with_course_torrent_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "course torrent"])
    assert result.exit_code == 0


def test_scan_with_software_crack_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "software crack"])
    assert result.exit_code == 0
