"""
Intelligence Module - Analyzes crawled content for threats and matches.

Subscribes to: page_crawled
Emits: content_analyzed, threat_detected, match_found
"""

from typing import Dict, Any, List
import asyncio
from aimon.core.base_module import BaseModule
import structlog

logger = structlog.get_logger(__name__)


class IntelligenceModule(BaseModule):
    """
    Analyzes crawled content for indicators of leaked assets.
    
    Processes page_crawled events from CrawlerModule.
    Performs analysis and threat detection.
    Emits threat_detected events for AlertsModule.
    """
    
    async def _initialize_impl(self) -> None:
        """Initialize the intelligence module."""
        self.analyzed_pages = []
        self.threats_detected = []
        await logger.ainfo("intelligence_module_initialized")
    
    async def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events."""
        await self.subscribe_event("page_crawled", self._on_page_crawled)
    
    async def _shutdown_impl(self) -> None:
        """Shutdown the intelligence module."""
        await logger.ainfo("intelligence_module_shutdown")
    
    async def analyze(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a crawled page for threats.
        
        Args:
            page: Page data to analyze
            
        Returns:
            Analysis results
        """
        source_id = page.get("source_id", "unknown")
        
        try:
            await logger.ainfo("analysis_started", source_id=source_id)
            
            # Simulate analysis
            analysis = {
                "source_id": source_id,
                "content_length": len(page.get("content", "")),
                "threat_score": 0.45,  # Simulated threat score
                "threat_level": "medium",
                "detected_assets": ["asset_1", "asset_2"],
                "analysis_type": "content_matching",
                "confidence": 0.92,
            }
            
            self.analyzed_pages.append(analysis)
            
            # Emit content_analyzed event
            await self.emit_event("content_analyzed", analysis=analysis)
            
            # Check if threats detected
            if analysis["threat_score"] > 0.3:
                self.threats_detected.append(analysis)
                await self.emit_event("threat_detected", threat=analysis)
                await logger.awarning("threat_detected", source_id=source_id, 
                                     threat_level=analysis["threat_level"])
            
            await logger.ainfo("analysis_completed", source_id=source_id)
            
            return analysis
            
        except Exception as e:
            await logger.aerror("analysis_failed", source_id=source_id, error=str(e))
            raise
    
    async def _on_page_crawled(self, **data) -> None:
        """Handle page_crawled event."""
        page = data.get("page", {})
        await self.analyze(page)
    
    def get_threats(self) -> List[Dict[str, Any]]:
        """Get all detected threats."""
        return self.threats_detected.copy()
