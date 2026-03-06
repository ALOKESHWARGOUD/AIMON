"""
Alerts Module - Generates and sends alerts based on detected threats.

Subscribes to: threat_detected, match_found
Emits: alert_generated, alert_sent
"""

from typing import Dict, Any, List
import asyncio
from datetime import datetime
from aimon.core.base_module import BaseModule
import structlog

logger = structlog.get_logger(__name__)


class AlertsModule(BaseModule):
    """
    Generates and manages alerts for detected threats.
    
    Processes threat_detected events from IntelligenceModule.
    Generates alerts and notifies users.
    """
    
    async def _initialize_impl(self) -> None:
        """Initialize the alerts module."""
        self.alerts = []
        self.alert_history = []
        await logger.ainfo("alerts_module_initialized")
    
    async def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events."""
        await self.subscribe_event("threat_detected", self._on_threat_detected)
    
    async def _shutdown_impl(self) -> None:
        """Shutdown the alerts module."""
        await logger.ainfo("alerts_module_shutdown")
    
    async def generate_alert(self, threat: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an alert from a threat.
        
        Args:
            threat: Threat data
            
        Returns:
            Generated alert
        """
        try:
            alert = {
                "alert_id": f"alert_{len(self.alerts) + 1}",
                "threat_id": threat.get("source_id"),
                "threat_level": threat.get("threat_level", "unknown"),
                "threat_score": threat.get("threat_score", 0),
                "message": f"Threat detected: {threat.get('threat_level')} severity",
                "detected_assets": threat.get("detected_assets", []),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "new",
            }
            
            self.alerts.append(alert)
            self.alert_history.append(alert)
            
            # Emit alert_generated event
            await self.emit_event("alert_generated", alert=alert)
            
            await logger.ainfo("alert_generated", alert_id=alert["alert_id"])
            
            return alert
            
        except Exception as e:
            await logger.aerror("alert_generation_failed", error=str(e))
            raise
    
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Send an alert to configured channels.
        
        Args:
            alert: Alert to send
            
        Returns:
            True if successful
        """
        try:
            alert_id = alert.get("alert_id", "unknown")
            await logger.ainfo("sending_alert", alert_id=alert_id)
            
            # Simulate sending alert (real implementation would integrate with
            # email, Slack, webhook, etc.)
            alert["status"] = "sent"
            
            await self.emit_event("alert_sent", alert=alert)
            
            await logger.ainfo("alert_sent", alert_id=alert_id)
            
            return True
            
        except Exception as e:
            await logger.aerror("alert_send_failed", alert_id=alert.get("alert_id"), error=str(e))
            return False
    
    async def _on_threat_detected(self, **data) -> None:
        """Handle threat_detected event."""
        threat = data.get("threat", {})
        
        # Generate alert
        alert = await self.generate_alert(threat)
        
        # Send alert
        await self.send_alert(alert)
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return self.alerts.copy()
    
    def get_alert_history(self) -> List[Dict[str, Any]]:
        """Get alert history."""
        return self.alert_history.copy()
