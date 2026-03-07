"""
AIMON Modules - Core framework modules.

- DiscoveryModule: Discovers data sources
- CrawlerModule: Crawls web pages and content
- IntelligenceModule: Analyzes content for threats
- AlertsModule: Generates alerts and notifies
- TelegramDiscoveryModule: Scans Telegram channels
- LeakSignalModule: Detects leak signals in content
- NetworkMapperModule: Builds piracy ecosystem graph
- VerificationModule: Multi-technique content verification
"""

from aimon.modules.discovery import DiscoveryModule
from aimon.modules.crawler import CrawlerModule
from aimon.modules.intelligence import IntelligenceModule
from aimon.modules.alerts import AlertsModule
from aimon.modules.telegram_discovery_module import TelegramDiscoveryModule
from aimon.modules.leak_signal_module import LeakSignalModule
from aimon.modules.network_mapper_module import NetworkMapperModule
from aimon.modules.verification_module import VerificationModule

__all__ = [
    "DiscoveryModule",
    "CrawlerModule",
    "IntelligenceModule",
    "AlertsModule",
    "TelegramDiscoveryModule",
    "LeakSignalModule",
    "NetworkMapperModule",
    "VerificationModule",
]
