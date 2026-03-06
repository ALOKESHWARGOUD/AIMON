"""
DocTutorials Leak Monitor

Monitors the web for leaked documentation and tutorial content using the
AIMON framework.  Searches multiple platforms for unauthorized redistributions
of protected course materials, e-books, and technical guides.

Usage:
    python doctutorials_monitor.py
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List

from aimon import AIMON

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search queries – typical patterns used when uploading tutorial leaks
# ---------------------------------------------------------------------------

SEARCH_QUERIES: List[str] = [
    "tutorial download free",
    "course materials leaked",
    "documentation torrent",
    "tutorial ebook free download",
    "programming course pirated",
    "online course leak reddit",
    "full course free telegram",
    "udemy course download torrent",
    "tutorial series free mirror",
    "documentation pdf download",
]

# Threat-level labels for display
THREAT_LABELS: Dict[str, str] = {
    "critical": "🔴 CRITICAL",
    "high":     "🟠 HIGH    ",
    "medium":   "🟡 MEDIUM  ",
    "low":      "🟢 LOW     ",
    "unknown":  "⚪ UNKNOWN ",
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _label(threat_level: str) -> str:
    """Return a human-readable label for a threat level."""
    return THREAT_LABELS.get(threat_level.lower(), THREAT_LABELS["unknown"])


def _print_banner() -> None:
    """Print the monitor banner."""
    print("=" * 60)
    print("  DocTutorials Leak Monitor")
    print("  Powered by AIMON Framework")
    print("=" * 60)
    print()


def _print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ---------------------------------------------------------------------------
# Core monitoring logic
# ---------------------------------------------------------------------------

async def run_search(framework: AIMON, query: str) -> List[Dict[str, Any]]:
    """
    Run a single search query and return discovered sources.

    Args:
        framework: Initialized AIMON framework instance
        query:     Search query string

    Returns:
        List of discovered source dictionaries
    """
    try:
        sources = await framework.search_sources(query)
        logger.info("search_completed query=%s sources_found=%d", query, len(sources))
        return sources
    except Exception as exc:
        logger.error("search_failed query=%s error=%s", query, exc)
        return []


async def _run_discovery_phase(framework: AIMON) -> List[Dict[str, Any]]:
    """
    Run the discovery phase: execute all search queries and collect sources.

    Args:
        framework: Initialized AIMON framework instance

    Returns:
        List of all discovered source dictionaries
    """
    _print_section("Discovery Phase")
    print(f"Running {len(SEARCH_QUERIES)} search queries …\n")

    all_sources: List[Dict[str, Any]] = []
    for query in SEARCH_QUERIES:
        sources = await run_search(framework, query)
        all_sources.extend(sources)
        if sources:
            for src in sources:
                print(
                    f"  [+] {src.get('name', src.get('title', 'unknown'))}"
                    f"  →  {src.get('url', '')}"
                )

    print(f"\n  Total sources discovered: {len(all_sources)}")
    return all_sources


async def _analyze_threats(framework: AIMON) -> List[Dict[str, Any]]:
    """
    Retrieve and display detected threats.

    Args:
        framework: Initialized AIMON framework instance

    Returns:
        List of detected threat dictionaries
    """
    _print_section("Threat Analysis")

    threats = await framework.get_threats()
    print(f"  Threats detected: {len(threats)}\n")

    for threat in threats:
        level = threat.get("threat_level", "unknown")
        score = threat.get("threat_score", 0.0)
        source_id = threat.get("source_id", "?")
        assets = threat.get("detected_assets", [])

        print(
            f"  {_label(level)}  score={score:.2f}"
            f"  source={source_id}"
            f"  assets={assets}"
        )

    return threats


async def _generate_alerts_report(framework: AIMON) -> List[Dict[str, Any]]:
    """
    Retrieve and display generated alerts.

    Args:
        framework: Initialized AIMON framework instance

    Returns:
        List of alert dictionaries
    """
    _print_section("Generated Alerts")

    alerts = await framework.get_alerts_list()
    print(f"  Alerts generated: {len(alerts)}\n")

    for alert in alerts:
        level = alert.get("threat_level", "unknown")
        alert_id = alert.get("alert_id", "?")
        message = alert.get("message", "")
        timestamp = alert.get("timestamp", "")

        print(
            f"  [{alert_id}] {_label(level)}"
            f"  {message}"
            f"  ({timestamp})"
        )

    return alerts


async def monitor_doctutorials() -> None:
    """
    Main monitoring coroutine.

    Initializes the AIMON framework, runs all search queries, then reports
    discovered threats and generated alerts.
    """
    _print_banner()
    print("Starting DocTutorials Leak Monitor\n")

    config: Dict[str, Any] = {
        "storage.type": "memory",
        "execution.max_concurrent": 5,
        "execution.timeout": 30,
    }

    async with AIMON(config) as framework:
        all_sources = await _run_discovery_phase(framework)
        threats = await _analyze_threats(framework)
        alerts = await _generate_alerts_report(framework)

        # ── Summary ───────────────────────────────────────────────────────
        _print_section("Summary")

        status = await framework.get_status()
        metrics = status.get("metrics", {})

        print(f"  Sources discovered : {len(all_sources)}")
        print(f"  Threats detected   : {len(threats)}")
        print(f"  Alerts generated   : {len(alerts)}")
        print(f"  Events emitted     : {metrics.get('events_emitted', 0)}")
        print(f"  Pages crawled      : {metrics.get('pages_crawled', 0)}")
        print()
        print("  Monitor run completed successfully.")
        print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        asyncio.run(monitor_doctutorials())
    except KeyboardInterrupt:
        print("\n[!] Monitor interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        print(f"\n[!] Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)
