"""
Metrics Collector - Framework metrics and instrumentation.

Collects framework metrics like:
- Modules initialized
- Events emitted
- Tasks executed
- Pages crawled
- Threats detected
- Alerts generated
"""

from typing import Any, Dict, List
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Central metrics collection point."""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "modules_initialized": 0,
            "events_emitted": 0,
            "events_by_type": {},
            "pages_crawled": 0,
            "sources_discovered": 0,
            "threats_detected": 0,
            "alerts_generated": 0,
            "tasks_executed": 0,
            "tasks_failed": 0,
            "uptime_seconds": 0,
            "start_time": datetime.utcnow().isoformat(),
        }
    
    async def record_module_init(self, module_name: str) -> None:
        """Record module initialization."""
        self.metrics["modules_initialized"] += 1
    
    async def record_event(self, event_type: str) -> None:
        """Record event emission."""
        self.metrics["events_emitted"] += 1
        self.metrics["events_by_type"][event_type] = \
            self.metrics["events_by_type"].get(event_type, 0) + 1
    
    async def record_page_crawled(self) -> None:
        """Record page crawl."""
        self.metrics["pages_crawled"] += 1
    
    async def record_source_discovered(self) -> None:
        """Record source discovery."""
        self.metrics["sources_discovered"] += 1
    
    async def record_threat(self) -> None:
        """Record threat detection."""
        self.metrics["threats_detected"] += 1
    
    async def record_alert(self) -> None:
        """Record alert generation."""
        self.metrics["alerts_generated"] += 1
    
    async def record_task_executed(self, success: bool) -> None:
        """Record task execution."""
        self.metrics["tasks_executed"] += 1
        if not success:
            self.metrics["tasks_failed"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        return self.metrics.copy()
    
    async def reset(self) -> None:
        """Reset metrics."""
        self.metrics = {
            "modules_initialized": 0,
            "events_emitted": 0,
            "events_by_type": {},
            "pages_crawled": 0,
            "sources_discovered": 0,
            "threats_detected": 0,
            "alerts_generated": 0,
            "tasks_executed": 0,
            "tasks_failed": 0,
            "uptime_seconds": 0,
            "start_time": datetime.utcnow().isoformat(),
        }
