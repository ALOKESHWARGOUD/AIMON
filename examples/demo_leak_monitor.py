"""
AIMON Framework — Live Demo
============================
Demonstrates the full AIMON leak intelligence pipeline.

Run:
    python examples/demo_leak_monitor.py

No API keys required for demo mode.
Set environment variables for real scanning (see docs/QUICKSTART.md).

Note: This file supersedes the legacy ``doctutorials_monitor.py`` that was
previously located at the repository root.
"""

import asyncio
import sys
from aimon import AIMON

BANNER = """
╔══════════════════════════════════════════════════════╗
║          AIMON Leak Intelligence Framework           ║
║          github.com/ALOKESHWARGOUD/AIMON             ║
╚══════════════════════════════════════════════════════╝
"""

DEMO_CONFIG = {
    "storage.type": "memory",
    # Tip: Set these env vars for real scanning:
    # AIMON_GOOGLE_API_KEY, AIMON_GOOGLE_SEARCH_ENGINE_ID
    # AIMON_TELEGRAM_API_ID, AIMON_TELEGRAM_API_HASH
}

async def run_demo():
    print(BANNER)
    brand = "DocTutorials"
    print(f"  Starting leak intelligence scan for: '{brand}'")
    print(f"  Mode: Demo (memory storage, no external APIs required)")
    print()

    try:
        async with AIMON(DEMO_CONFIG) as fw:
            print("  [1/4] Framework initialized ✓")
            print("  [2/4] Running discovery pipeline...")

            report = await fw.monitor.brand(brand)

            print("  [3/4] Pipeline complete ✓")
            print("  [4/4] Building report...\n")

            # ── Report Output ──────────────────────────────────────────
            print("━" * 56)
            print("  LEAK INTELLIGENCE REPORT")
            print("━" * 56)
            print(f"  Brand:           {report.brand}")
            print(f"  Scan Duration:   {report.scan_duration_seconds:.2f}s")
            print(f"  Sources Found:   {report.sources_found}")
            print(f"  Leaks Confirmed: {report.leaks_confirmed}")
            print(f"  Risk Score:      {report.risk_score:.4f}")
            print(f"  Risk Level:      {report.risk_level.upper()}")
            print()

            # Leak network (graph structure: nodes + edges)
            network = report.leak_network
            node_count = len(network.get("nodes", []))
            edge_count = len(network.get("edges", []))
            print(f"  Leak Network:    {node_count} nodes / {edge_count} edges")
            if node_count > 0:
                for node in network["nodes"][:5]:  # show first 5 nodes
                    label = node.get("label") or node.get("url") or str(node)
                    print(f"    → {label}")
                if node_count > 5:
                    print(f"    ... and {node_count - 5} more nodes")
            else:
                print("    (No network data — run with API keys for real results)")

            print()

            # Alerts
            if report.alerts:
                print(f"  Alerts ({len(report.alerts)}):")
                for alert in report.alerts[:10]:
                    platform = alert.get("platform", "unknown")
                    url      = alert.get("url", "")
                    score    = alert.get("risk_score", 0)
                    print(f"    [{platform}] score={score:.2f}  {url}")
            else:
                print("  Alerts: None in demo mode")
                print("  (Configure API keys to scan real sources)")

            print()
            print("━" * 56)
            print()
            print("  Next steps:")
            print("  1. Read docs/QUICKSTART.md for configuration")
            print("  2. Set API keys in .env for real-world scanning")
            print("  3. Explore examples/ for more usage patterns")
            print()

    except KeyboardInterrupt:
        print("\n  Demo interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\n  [ERROR] {e}")
        print("  Run 'pip install -e .' to ensure the package is installed.")
        print("  See docs/QUICKSTART.md for setup instructions.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_demo())
