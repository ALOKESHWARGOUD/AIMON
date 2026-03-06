"""
AIMON Sync - Synchronous API wrapper for AIMON framework.

Allows using AIMON from synchronous code without async/await.

Example usage:

    from aimon.sync import AIMONSync
    
    fw = AIMONSync()
    sources = fw.search_sources("course download")
    threats = fw.get_threats()
    fw.shutdown()
"""

from aimon.sync.sync_api import AIMONSync

__all__ = ["AIMONSync"]
