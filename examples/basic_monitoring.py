"""
Basic AIMON Usage Example

This is the simplest way to use AIMON - search for sources  
and get results.
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
            print(f"  - {source['name']}: {source['url']}")
        
        # Get detected threats
        print("\n[*] Detected Threats:")
        threats = await framework.get_threats()
        print(f"[+] {len(threats)} threats detected")
        
        for threat in threats:
            print(f"  - {threat['threat_level'].upper()}: {threat['source_id']}")
        
        # Get alerts
        print("\n[*] Generated Alerts:")
        alerts = await framework.get_alerts_list()
        print(f"[+] {len(alerts)} alerts generated")
        
        # Get framework status
        print("\n[*] Framework Status:")
        status = await framework.get_status()
        metrics = status.get("metrics", {})
        
        print(f"  Events emitted: {metrics.get('events_emitted', 0)}")
        print(f"  Pages crawled: {metrics.get('pages_crawled', 0)}")
        print(f"  Modules initialized: {metrics.get('modules_initialized', 0)}")
    
    print("\n[+] Example complete")


if __name__ == "__main__":
    asyncio.run(main())
