"""
Module Registry - Manages module registration and lifecycle.
"""

from typing import Any, Dict, Optional, Type
from aimon.core.base_module import BaseModule
import structlog

logger = structlog.get_logger(__name__)


class ModuleRegistry:
    """Manages registration and lifecycle of modules."""
    
    def __init__(self):
        self._modules: Dict[str, BaseModule] = {}
    
    async def register(self, module: BaseModule) -> None:
        """Register a module."""
        self._modules[module.name] = module
        await logger.ainfo("module_registered", module_name=module.name)
    
    async def get(self, name: str) -> Optional[BaseModule]:
        """Get a module by name."""
        return self._modules.get(name)
    
    async def get_all(self) -> Dict[str, BaseModule]:
        """Get all modules."""
        return self._modules.copy()
    
    async def unregister(self, name: str) -> bool:
        """Unregister a module."""
        if name in self._modules:
            del self._modules[name]
            await logger.ainfo("module_unregistered", module_name=name)
            return True
        return False
    
    async def get_ready_modules(self) -> Dict[str, BaseModule]:
        """Get all ready modules."""
        from aimon.core.base_module import ModuleState
        return {
            name: mod for name, mod in self._modules.items()
            if mod.state == ModuleState.READY
        }
