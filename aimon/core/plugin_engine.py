"""
Plugin Engine - Auto-discoverable plugin system.

Plugins are auto-discovered from aimon.plugins namespace.
"""

import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
import structlog

logger = structlog.get_logger(__name__)


class PluginEngine:
    """
    Plugin system with auto-discovery.
    
    Plugins are automatically discovered from:
    - aimon.plugins.* namespace
    - External plugin packages (if configured)
    
    Plugins can extend:
    - Connectors
    - Storage backends
    - Fingerprint algorithms
    - Analysis engines
    """
    
    def __init__(self):
        self._plugins: Dict[str, Any] = {}
        self._plugin_types: Dict[str, Dict[str, Type]] = {}
    
    async def discover_plugins(self, namespace: str = "aimon.plugins") -> List[str]:
        """
        Auto-discover plugins from a namespace.
        
        Args:
            namespace: Python namespace to search
            
        Returns:
            List of discovered plugin names
        """
        discovered = []
        
        try:
            # Try to import the namespace package
            pkg = importlib.import_module(namespace)
            
            if hasattr(pkg, "__path__"):
                # Scan for modules in the package
                for path in pkg.__path__:
                    plugin_path = Path(path)
                    for file_path in plugin_path.glob("*.py"):
                        if file_path.name.startswith("_"):
                            continue
                        
                        module_name = f"{namespace}.{file_path.stem}"
                        try:
                            mod = importlib.import_module(module_name)
                            discovered.append(module_name)
                            await logger.ainfo("plugin_discovered", plugin=module_name)
                        except Exception as e:
                            await logger.awarning("plugin_discovery_failed", plugin=module_name, error=str(e))
        except ImportError:
            await logger.awarning("namespace_not_found", namespace=namespace)
        
        return discovered
    
    async def register_plugin(self, plugin_type: str, name: str, plugin_class: Type) -> None:
        """
        Register a plugin class.
        
        Args:
            plugin_type: Type of plugin (e.g., "connector", "storage")
            name: Plugin name
            plugin_class: Plugin class
        """
        if plugin_type not in self._plugin_types:
            self._plugin_types[plugin_type] = {}
        
        self._plugin_types[plugin_type][name] = plugin_class
        await logger.ainfo("plugin_registered", plugin_type=plugin_type, name=name)
    
    async def get_plugin(self, plugin_type: str, name: str) -> Optional[Type]:
        """
        Get a plugin class by type and name.
        
        Args:
            plugin_type: Type of plugin
            name: Plugin name
            
        Returns:
            Plugin class or None
        """
        if plugin_type in self._plugin_types:
            return self._plugin_types[plugin_type].get(name)
        return None
    
    async def get_plugins_by_type(self, plugin_type: str) -> Dict[str, Type]:
        """
        Get all plugins of a given type.
        
        Args:
            plugin_type: Type of plugin
            
        Returns:
            Dictionary of plugin name -> plugin class
        """
        return self._plugin_types.get(plugin_type, {}).copy()
