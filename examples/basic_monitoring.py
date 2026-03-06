"""
Basic AIMON Usage Example

Demonstrates the async context-manager API, searching for sources,
inspecting threats and alerts, and reading framework metrics.
"""

import asyncio
from aimon import AIMON


async def main():
    """Basic example."""
    print("[*] AIMON Basic Example")
    print("[*] Initializing framework...")

    async with AIMON() as framework:
        # Search for sources
        print("\n[*] Searching for sources...")
        sources = await framework.search_sources("course download")

        print(f"[+] Found {len(sources)} sources")
        for source in sources:
            print(f"  - {source.get('name', source.get('title', '?'))}: {source.get('url', '')}")

        # Get detected threats
        print("\n[*] Detected Threats:")
        threats = await framework.get_threats()
        print(f"[+] {len(threats)} threats detected")

        for threat in threats:
            print(f"  - {threat.get('threat_level', 'unknown').upper()}: {threat.get('source_id', '?')}")

        # Get alerts
        print("\n[*] Generated Alerts:")
        alerts = await framework.get_alerts_list()
        print(f"[+] {len(alerts)} alerts generated")
        for alert in alerts:
            print(f"  - [{alert.get('threat_level', '?').upper()}] {alert.get('message', '')}")

        # Get framework status / metrics
        print("\n[*] Framework Status:")
        status = await framework.get_status()
        metrics = status.get("metrics", {})

        print(f"  Events emitted:       {metrics.get('events_emitted', 0)}")
        print(f"  Pages crawled:        {metrics.get('pages_crawled', 0)}")
        print(f"  Modules initialized:  {metrics.get('modules_initialized', 0)}")
        print(f"  Threats detected:     {metrics.get('threats_detected', 0)}")
        print(f"  Alerts generated:     {metrics.get('alerts_generated', 0)}")

    print("\n[+] Example complete")


if __name__ == "__main__":
    asyncio.run(main())
