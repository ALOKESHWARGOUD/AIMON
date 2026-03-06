"""
BaseModule - Abstract base class for all AIMON modules.

All modules must inherit from BaseModule and implement lifecycle methods.
Modules communicate through the EventBus.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ModuleState(Enum):
    """Module lifecycle states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"


class BaseModule(ABC):
    """
    Abstract base class for all framework modules.
    
    Modules are initialized, handle events, and can be shutdown.
    All module communication is through the EventBus.
    """
    
    def __init__(self, name: str, event_bus: Optional[Any] = None):
        """
        Initialize a module.
        
        Args:
            name: Unique module name
            event_bus: EventBus instance (injected by runtime)
        """
        self.name = name
        self.event_bus = event_bus
        self.state = ModuleState.UNINITIALIZED
        self._subscriptions: List[tuple[str, Callable]] = []
        self._initialized = False
        self._config: Dict[str, Any] = {}
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the module.
        
        Args:
            config: Module configuration
        """
        if self.state != ModuleState.UNINITIALIZED:
            await logger.awarning("module_already_initialized", module=self.name)
            return
        
        self.state = ModuleState.INITIALIZING
        self._config = config or {}
        
        try:
            await self._initialize_impl()
            await self._subscribe_to_events()
            self.state = ModuleState.READY
            self._initialized = True
            await logger.ainfo("module_initialized", module=self.name)
        except Exception as e:
            self.state = ModuleState.ERROR
            await logger.aerror("module_init_failed", module=self.name, error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the module."""
        if self.state == ModuleState.STOPPED:
            return
        
        self.state = ModuleState.SHUTTING_DOWN
        
        try:
            # Unsubscribe from all events
            for event_type, handler in self._subscriptions:
                if self.event_bus:
                    await self.event_bus.unsubscribe(event_type, handler)
            
            await self._shutdown_impl()
            self.state = ModuleState.STOPPED
            await logger.ainfo("module_shutdown", module=self.name)
        except Exception as e:
            await logger.aerror("module_shutdown_failed", module=self.name, error=str(e))
            raise
    
    @abstractmethod
    async def _initialize_impl(self) -> None:
        """
        Module-specific initialization logic.
        
        Subclasses override to perform initialization.
        """
        pass
    
    async def _shutdown_impl(self) -> None:
        """
        Module-specific shutdown logic.
        
        Override to perform cleanup.
        """
        pass
    
    async def _subscribe_to_events(self) -> None:
        """
        Subscribe to events.
        
        Subclasses override to subscribe to relevant events.
        """
        pass
    
    async def subscribe_event(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Async or sync callable to handle event
        """
        if not self.event_bus:
            raise RuntimeError(f"Module {self.name} has no event bus")
        
        await self.event_bus.subscribe(event_type, handler)
        self._subscriptions.append((event_type, handler))
    
    async def emit_event(self, event_type: str, **data) -> None:
        """
        Emit an event.
        
        Args:
            event_type: Type of event
            **data: Event data
        """
        if not self.event_bus:
            raise RuntimeError(f"Module {self.name} has no event bus")
        
        await self.event_bus.emit(event_type, self.name, **data)
    
    def is_ready(self) -> bool:
        """Check if module is ready."""
        return self.state == ModuleState.READY
    
    def get_status(self) -> Dict[str, Any]:
        """Get module status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "initialized": self._initialized,
            "subscriptions": len(self._subscriptions),
        }
