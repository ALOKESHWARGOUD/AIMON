"""
Example: Brand Leak Monitoring with AIMON

Demonstrates how to use AIMON to detect content leaks for a brand.
"""
import asyncio
from aimon import AIMON


async def main():
    config = {
        "storage.type": "memory",  # use "postgres" in production
        # Uncomment for real Telegram scanning:
        # "telegram.api_id": 12345,
        # "telegram.api_hash": "your_api_hash",
        # Uncomment for Google Custom Search:
        # "google.api_key": "your_key",
        # "google.search_engine_id": "your_cx",
    }

    async with AIMON(config) as fw:
        # Run full brand leak scan
        report = await fw.monitor.brand("DocTutorials")

        print(f"Brand:           {report.brand}")
        print(f"Risk Level:      {report.risk_level}")
        print(f"Risk Score:      {report.risk_score:.2f}")
        print(f"Sources Found:   {report.sources_found}")
        print(f"Leaks Confirmed: {report.leaks_confirmed}")
        print(f"Scan Duration:   {report.scan_duration_seconds:.1f}s")
        print()
        print("Leak Network:")
        print(report.leak_network)
        print()
        print("Alerts:")
        for alert in report.alerts:
            print(f"  [{alert.get('platform', 'unknown')}] {alert.get('url', '')} — score: {alert.get('risk_score', 0):.2f}")


if __name__ == "__main__":
    asyncio.run(main())
