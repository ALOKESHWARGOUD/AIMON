"""
Service Container - Dependency injection and service management.

Manages service registration, resolution, and lifecycle.
"""

from typing import Any, Dict, Optional, Type, TypeVar
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class ServiceContainer:
    """
    Simple but powerful service container for dependency injection.
    
    Services are registered as singletons and can be resolved by name or registration.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any) -> None:
        """
        Register a service instance.
        
        Args:
            name: Service identifier
            service: Service instance
        """
        self._services[name] = service
        # Remove from singleton cache if it exists
        self._singletons.pop(name, None)
    
    def register_factory(self, name: str, factory: callable) -> None:
        """
        Register a service factory function.
        
        Args:
            name: Service identifier
            factory: Callable that creates the service
        """
        self._factories[name] = factory
        self._singletons.pop(name, None)
    
    def get(self, name: str) -> Optional[Any]:
        """
        Get a service by name.
        
        Args:
            name: Service identifier
            
        Returns:
            Service instance or None if not found
        """
        # Check singletons first
        if name in self._singletons:
            return self._singletons[name]
        
        # Check registered services
        if name in self._services:
            return self._services[name]
        
        # Check factories
        if name in self._factories:
            service = self._factories[name]()
            self._singletons[name] = service
            return service
        
        return None
    
    def has(self, name: str) -> bool:
        """Check if service is registered."""
        return name in self._services or name in self._factories or name in self._singletons
    
    async def clear(self) -> None:
        """Clear all services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
