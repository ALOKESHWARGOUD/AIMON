"""
Event Bus - Core pub/sub system for module communication.

All modules communicate through events to maintain loose coupling.
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Event:
    """Represents an event emitted by a module."""
    
    event_type: str
    source: str  # module name that emitted
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"Event({self.event_type} from {self.source} at {self.timestamp})"


class EventBus:
    """
    Central event pub/sub system.
    
    Handlers can be sync or async. All handlers are isolated - exceptions
    in one handler don't affect others.
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._event_log: List[Event] = []
        self._max_log_size = 10000
    
    async def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Async or sync callable that handles the event
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        await logger.ainfo("handler_subscribed", event_type=event_type, handler=handler.__name__)
    
    async def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            await logger.ainfo("handler_unsubscribed", event_type=event_type)
    
    async def emit(self, event_type: str, source: str, **data) -> Event:
        """
        Emit an event and invoke all subscribed handlers.
        
        Args:
            event_type: Type of event
            source: Module that emitted the event
            **data: Event data
            
        Returns:
            The Event object that was emitted
        """
        event = Event(event_type=event_type, source=source, data=data)
        
        # Log event
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log.pop(0)
        
        await logger.ainfo("event_emitted", event=str(event), handlers_count=len(self._handlers.get(event_type, [])))
        
        # Invoke handlers
        handlers = self._handlers.get(event_type, [])
        tasks = []
        
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    tasks.append(handler(event))
                else:
                    tasks.append(asyncio.to_thread(handler, event))
            except Exception as e:
                await logger.aerror("handler_error", handler=handler.__name__, error=str(e))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return event
    
    async def get_event_log(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """
        Retrieve recent events.
        
        Args:
            event_type: Filter by event type (None = all)
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        events = self._event_log
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    async def clear_history(self) -> None:
        """Clear event log."""
        self._event_log.clear()
