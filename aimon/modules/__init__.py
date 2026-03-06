"""
AIMON Modules - Core framework modules.

- DiscoveryModule: Discovers data sources
- CrawlerModule: Crawls web pages and content
- IntelligenceModule: Analyzes content for threats
- AlertsModule: Generates alerts and notifies
"""

from aimon.modules.discovery import DiscoveryModule
from aimon.modules.crawler import CrawlerModule
from aimon.modules.intelligence import IntelligenceModule
from aimon.modules.alerts import AlertsModule

__all__ = [
    "DiscoveryModule",
    "CrawlerModule",
    "IntelligenceModule",
    "AlertsModule",
]
