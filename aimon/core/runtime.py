"""
AIMONCoreRuntime - Central orchestrator and kernel of the AIMON framework.

The runtime manages:
- Module lifecycle and registry
- Event bus coordination
- Service container
- Execution engine
- Plugin loading
- Framework health and metrics
"""

import asyncio
from typing import Any, Dict, Optional, Type
from datetime import datetime
import structlog

from aimon.core.base_module import BaseModule, ModuleState
from aimon.core.event_bus import EventBus
from aimon.core.execution_engine import ExecutionEngine
from aimon.core.service_container import ServiceContainer
from aimon.core.module_registry import ModuleRegistry
from aimon.core.config_manager import ConfigManager

logger = structlog.get_logger(__name__)


class RuntimeState:
    """Runtime metrics and state tracking."""
    
    def __init__(self):
        self.started_at: Optional[datetime] = None
        self.modules_initialized = 0
        self.events_emitted = 0
        self.tasks_executed = 0
        self.errors_count = 0


class AIMONCoreRuntime:
    """
    Singleton runtime that orchestrates the entire AIMON framework.
    
    Responsibilities:
    - Initialize and manage modules
    - Coordinate event bus
    - Run execution engine
    - Manage service container
    - Load plugins
    - Track metrics and health
    """
    
    _instance: Optional['AIMONCoreRuntime'] = None
    
    def __init__(self):
        """Initialize the runtime."""
        self.event_bus = EventBus()
        self.service_container = ServiceContainer()
        self.execution_engine = ExecutionEngine()
        self.module_registry = ModuleRegistry()
        self.config = ConfigManager()
        
        self.state = RuntimeState()
        self._initialized = False
        self._modules: Dict[str, BaseModule] = {}
        self._running = False
    
    @classmethod
    def get_instance(cls) -> 'AIMONCoreRuntime':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton (for testing)."""
        cls._instance = None
    
    async def initialize(self, config_dict: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the entire runtime.
        
        Args:
            config_dict: Configuration dictionary
        """
        if self._initialized:
            await logger.awarning("runtime_already_initialized")
            return
        
        try:
            await logger.ainfo("runtime_initializing")
            
            # Load configuration
            if config_dict:
                for key, value in config_dict.items():
                    self.config.set(key, value)
            
            # Start event bus
            await self.event_bus.initialize()
            
            # Start execution engine
            await self.execution_engine.initialize(
                max_concurrent=self.config.get("execution.max_concurrent", 10),
                default_timeout=self.config.get("execution.timeout", 60)
            )
            
            # Register built-in services
            await self._register_builtin_services()
            
            # Load plugins
            await self._load_plugins()
            
            self.state.started_at = datetime.now()
            self._initialized = True
            await logger.ainfo("runtime_initialized")
            
        except Exception as e:
            await logger.aerror("runtime_init_failed", error=str(e))
            raise
    
    async def _register_builtin_services(self) -> None:
        """Register built-in framework services."""
        self.service_container.register("event_bus", self.event_bus)
        self.service_container.register("execution_engine", self.execution_engine)
        self.service_container.register("config", self.config)
        self.service_container.register("runtime", self)
    
    async def _load_plugins(self) -> None:
        """Load discoverable plugins."""
        try:
            import importlib.util
            import pkgutil
            
            # Dynamic plugin discovery from aimon.plugins
            try:
                import aimon.plugins as plugins_module
                plugins_path = plugins_module.__path__
                
                for importer, modname, ispkg in pkgutil.iter_modules(plugins_path):
                    try:
                        module = importer.find_module(modname).load_module(modname)
                        await logger.ainfo("plugin_loaded", module=modname)
                    except Exception as e:
                        await logger.aerror("plugin_load_failed", module=modname, error=str(e))
            except ImportError:
                # plugins module doesn't exist yet, that's OK
                pass
        except Exception as e:
            await logger.awarning("plugin_loading_failed", error=str(e))
    
    async def register_module(self, name: str, module: BaseModule, 
                             config: Optional[Dict[str, Any]] = None) -> None:
        """
        Register and initialize a module.
        
        Args:
            name: Module name
            module: BaseModule instance
            config: Module configuration
        """
        if not isinstance(module, BaseModule):
            raise TypeError(f"Module must inherit from BaseModule, got {type(module)}")
        
        if name in self._modules:
            raise ValueError(f"Module {name} already registered")
        
        try:
            # Inject event bus
            module.event_bus = self.event_bus
            
            # Initialize module
            await module.initialize(config or {})
            
            # Register in registry
            self.module_registry.register(name, module)
            
            # Store reference
            self._modules[name] = module
            self.state.modules_initialized += 1
            
            await logger.ainfo("module_registered", name=name)
            
        except Exception as e:
            await logger.aerror("module_registration_failed", name=name, error=str(e))
            raise
    
    async def unregister_module(self, name: str) -> None:
        """
        Unregister and shutdown a module.
        
        Args:
            name: Module name
        """
        if name not in self._modules:
            raise ValueError(f"Module {name} not found")
        
        module = self._modules[name]
        await module.shutdown()
        self.module_registry.unregister(name)
        del self._modules[name]
        
        await logger.ainfo("module_unregistered", name=name)
    
    def get_module(self, name: str) -> Optional[BaseModule]:
        """Get a registered module."""
        return self._modules.get(name)
    
    def get_all_modules(self) -> Dict[str, BaseModule]:
        """Get all registered modules."""
        return self._modules.copy()
    
    async def emit_event(self, event_type: str, **data) -> None:
        """Emit an event through the bus."""
        self.state.events_emitted += 1
        await self.event_bus.emit(event_type, **data)
    
    async def submit_task(self, coro, priority: int = 0, timeout: Optional[float] = None):
        """
        Submit a task to the execution engine.
        
        Args:
            coro: Coroutine to execute
            priority: Task priority (higher = more important)
            timeout: Task timeout in seconds
        
        Returns:
            Task ID
        """
        self.state.tasks_executed += 1
        return await self.execution_engine.submit(coro, priority=priority, timeout=timeout)
    
    async def start(self) -> None:
        """Start the runtime execution."""
        if not self._initialized:
            await self.initialize()
        
        self._running = True
        await logger.ainfo("runtime_started")
        
        # Start execution engine loop
        await self.execution_engine.start()
    
    async def stop(self) -> None:
        """Stop the runtime."""
        self._running = False
        await logger.ainfo("runtime_stopping")
        
        # Shutdown all modules
        for name in list(self._modules.keys()):
            try:
                await self.unregister_module(name)
            except Exception as e:
                await logger.aerror("module_shutdown_error", name=name, error=str(e))
        
        # Stop execution engine
        await self.execution_engine.stop()
        
        await logger.ainfo("runtime_stopped")
    
    def is_ready(self) -> bool:
        """Check if runtime is ready."""
        return self._initialized and all(m.is_ready() for m in self._modules.values())
    
    def get_status(self) -> Dict[str, Any]:
        """Get runtime status."""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "modules": len(self._modules),
            "modules_ready": sum(1 for m in self._modules.values() if m.is_ready()),
            "uptime": (datetime.now() - self.state.started_at).total_seconds() 
                      if self.state.started_at else None,
            "events_emitted": self.state.events_emitted,
            "tasks_executed": self.state.tasks_executed,
            "errors": self.state.errors_count,
            "module_statuses": {
                name: module.get_status() 
                for name, module in self._modules.items()
            }
        }


def get_runtime() -> AIMONCoreRuntime:
    """Get the singleton runtime instance."""
    return AIMONCoreRuntime.get_instance()
