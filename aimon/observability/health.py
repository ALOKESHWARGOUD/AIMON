"""
Health Monitor - Framework and module health checks.

Monitors:
- Module health status
- Memory usage
- Task queue depth
- Error rates
"""

from typing import Any, Dict
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthMonitor:
    """Monitors framework and component health."""
    
    def __init__(self):
        self._component_health: Dict[str, Dict[str, Any]] = {}
        self._error_counts: Dict[str, int] = {}
    
    async def check_component(self, component_name: str, 
                             is_healthy: bool, details: Dict[str, Any] = None) -> None:
        """
        Check component health.
        
        Args:
            component_name: Name of component
            is_healthy: Whether component is healthy
            details: Additional health details
        """
        self._component_health[component_name] = {
            "healthy": is_healthy,
            "status": HealthStatus.HEALTHY.value if is_healthy else HealthStatus.DEGRADED.value,
            "details": details or {},
        }
    
    async def record_error(self, component_name: str) -> None:
        """Record error for component."""
        self._error_counts[component_name] = \
            self._error_counts.get(component_name, 0) + 1
    
    async def get_overall_status(self) -> Dict[str, Any]:
        """Get overall framework health status."""
        if not self._component_health:
            return {"status": HealthStatus.UNKNOWN.value}
        
        unhealthy = sum(1 for h in self._component_health.values() if not h.get("healthy"))
        total = len(self._component_health)
        
        if unhealthy == 0:
            status = HealthStatus.HEALTHY.value
        elif unhealthy < total / 2:
            status = HealthStatus.DEGRADED.value
        else:
            status = HealthStatus.CRITICAL.value
        
        return {
            "status": status,
            "healthy_components": total - unhealthy,
            "total_components": total,
            "components": self._component_health,
            "errors": self._error_counts,
        }
    
    async def get_component_status(self, component_name: str) -> Dict[str, Any]:
        """Get status of specific component."""
        return self._component_health.get(component_name, {})
