"""
AIMON Developer API - Main entry point for framework users.

Simple, clean API for building monitoring and leak detection systems.

Example usage:

    from aimon import AIMON
    
    async with AIMON() as framework:
        # Search for sources
        sources = await framework.discovery.search("course download")
        
        # Crawler will automatically process sources via event bus
        # Intelligence module will analyze content
        # Alerts module will generate alerts
        
        # Get results
        threats = await framework.get_threats()
        alerts = await framework.get_alerts()
        
        # Run full brand leak scan
        report = await framework.monitor.brand("DocTutorials")
"""

from typing import Any, Dict, List, Optional
import asyncio
import structlog
from contextlib import asynccontextmanager

from aimon.core.runtime import AIMONCoreRuntime, get_runtime
from aimon.modules import (
    DiscoveryModule,
    CrawlerModule,
    IntelligenceModule,
    AlertsModule,
    TelegramDiscoveryModule,
    LeakSignalModule,
    NetworkMapperModule,
    VerificationModule,
)
from aimon.intelligence.risk_engine import RiskEngineModule
from aimon.storage import MemoryStorage
from aimon.observability import MetricsCollector, HealthMonitor
from aimon.monitor.brand_monitor import BrandMonitor

logger = structlog.get_logger(__name__)


class AIMON:
    """
    Main AIMON framework API.
    
    Provides simple interface to all framework functionality:
    - Source discovery
    - Web crawling
    - Content analysis
    - Threat detection
    - Alert generation
    - Brand leak monitoring
    
    Can be used as context manager or manually.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize AIMON framework.
        
        Args:
            config: Framework configuration
        """
        self.config = config or {}
        self.runtime = AIMONCoreRuntime.get_instance()
        self.metrics = MetricsCollector()
        self.health = HealthMonitor()
        
        # Lazy-load modules
        self.discovery = None
        self.crawler = None
        self.intelligence = None
        self.alerts = None
        self.storage = None

        # New intelligence modules
        self.telegram_discovery = None
        self.leak_signal = None
        self.network_mapper = None
        self.verification = None
        self.risk_engine = None

        # High-level monitor API
        self.monitor: BrandMonitor = BrandMonitor(self)
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the framework."""
        if self._initialized:
            return
        
        try:
            await logger.ainfo("aimon_initializing")
            
            # Initialize runtime
            await self.runtime.initialize(self.config)
            
            # Initialize storage (default to memory)
            storage_type = self.config.get("storage.type", "memory")
            if storage_type == "memory":
                self.storage = MemoryStorage()
            else:
                self.storage = MemoryStorage()  # Default fallback
            
            await self.storage.initialize()
            
            # Register built-in modules
            self.discovery = DiscoveryModule("discovery")
            self.crawler = CrawlerModule("crawler")
            self.intelligence = IntelligenceModule("intelligence")
            self.alerts = AlertsModule("alerts")
            self.telegram_discovery = TelegramDiscoveryModule("telegram_discovery")
            self.leak_signal = LeakSignalModule("leak_signal")
            self.network_mapper = NetworkMapperModule("network_mapper")
            self.verification = VerificationModule("verification")
            self.risk_engine = RiskEngineModule("risk_engine")
            
            await self.runtime.register_module("discovery", self.discovery)
            await self.runtime.register_module("crawler", self.crawler)
            await self.runtime.register_module("intelligence", self.intelligence)
            await self.runtime.register_module("alerts", self.alerts)
            await self.runtime.register_module("telegram_discovery", self.telegram_discovery, self.config)
            await self.runtime.register_module("leak_signal", self.leak_signal)
            await self.runtime.register_module("network_mapper", self.network_mapper, self.config)
            await self.runtime.register_module("verification", self.verification)
            await self.runtime.register_module("risk_engine", self.risk_engine)
            
            # Start runtime
            await self.runtime.start()
            
            self._initialized = True
            await logger.ainfo("aimon_initialized")
            
        except Exception as e:
            await logger.aerror("aimon_init_failed", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the framework."""
        if not self._initialized:
            return
        
        try:
            await logger.ainfo("aimon_shutting_down")
            
            await self.runtime.stop()
            
            if self.storage:
                await self.storage.shutdown()
            
            self._initialized = False
            await logger.ainfo("aimon_shutdown_complete")
            
        except Exception as e:
            await logger.aerror("aimon_shutdown_failed", error=str(e))
    
    async def search_sources(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for data sources matching query.
        
        Args:
            query: Search query
            filters: Optional filters
            
        Returns:
            List of discovered sources
        """
        if not self.discovery:
            raise RuntimeError("Framework not initialized")
        
        sources = await self.discovery.search(query, filters or {})
        return sources
    
    def get_discovery(self):
        """Get discovery module."""
        return self.discovery
    
    def get_crawler(self):
        """Get crawler module."""
        return self.crawler
    
    def get_intelligence(self):
        """Get intelligence module."""
        return self.intelligence
    
    def get_alerts(self):
        """Get alerts module."""
        return self.alerts
    
    async def get_threats(self) -> List[Dict[str, Any]]:
        """Get all detected threats."""
        if not self.intelligence:
            return []
        
        return self.intelligence.get_threats()
    
    async def get_alerts_list(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        if not self.alerts:
            return []
        
        return self.alerts.get_alerts()
    
    async def get_alert_history(self) -> List[Dict[str, Any]]:
        """Get alert history."""
        if not self.alerts:
            return []
        
        return self.alerts.get_alert_history()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get framework metrics."""
        return self.metrics.get_metrics()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get framework status."""
        return {
            "initialized": self._initialized,
            "runtime": self.runtime.get_status(),
            "health": await self.health.get_overall_status(),
            "metrics": self.metrics.get_metrics(),
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        return False


@asynccontextmanager
async def create_framework(config: Optional[Dict[str, Any]] = None):
    """
    Factory function to create and initialize framework.
    
    Usage:
        async with create_framework() as framework:
            sources = await framework.search_sources("query")
    """
    framework = AIMON(config)
    await framework.initialize()
    try:
        yield framework
    finally:
        await framework.shutdown()
