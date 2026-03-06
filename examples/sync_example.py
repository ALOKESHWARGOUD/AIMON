"""
Synchronous AIMON Usage Example

Uses the sync wrapper for traditional synchronous code.
"""

from aimon.sync import AIMONSync


def main():
    """Synchronous example."""
    print("[*] AIMON Sync Example")
    print("[*] Initializing framework...")
    
    fw = AIMONSync()
    fw.initialize()
    
    try:
        # Search for sources (sync)
        print("\n[*] Searching for sources...")
        sources = fw.search_sources("movie download")
        
        print(f"[+] Found {len(sources)} sources")
        
        # Get threats (sync)
        print("\n[*] Detected Threats:")
        threats = fw.get_threats()
        print(f"[+] {len(threats)} threats detected")
        
        for threat in threats:
            print(f"  - Level: {threat.get('threat_level')} (Score: {threat.get('threat_score')})")
        
        # Get alerts (sync)
        print("\n[*] Generated Alerts:")
        alerts = fw.get_alerts()
        print(f"[+] {len(alerts)} alerts")
        
        # Get status
        print("\n[*] Framework Status:")
        status = fw.get_status()
        print(f"Status: {status['initialized']}")
    
    finally:
        fw.shutdown()
    
    print("\n[+] Sync example complete")


if __name__ == "__main__":
    main()
