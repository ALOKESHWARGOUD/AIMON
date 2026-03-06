"""
Configuration Management - Hierarchical configuration system.

Supports environment variables, configuration files, and programmatic config.
"""

import os
from typing import Any, Dict, Optional
from pathlib import Path
import yaml
from dotenv import load_dotenv
import structlog

logger = structlog.get_logger(__name__)


class ConfigManager:
    """
    Hierarchical configuration manager.
    
    Supports:
    - Environment variables
    - Configuration files (YAML, JSON)
    - Programmatic configuration
    - Nested keys with dot notation
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize config manager.
        
        Args:
            config_file: Path to configuration file (YAML or JSON)
        """
        self._config: Dict[str, Any] = {}
        
        # Load .env file
        load_dotenv()
        
        # Load config file if provided
        if config_file and config_file.exists():
            self._load_file(config_file)
    
    def _load_file(self, path: Path) -> None:
        """Load configuration from file."""
        try:
            if path.suffix in [".yaml", ".yml"]:
                with open(path) as f:
                    data = yaml.safe_load(f)
                    if data:
                        self._config.update(data)
            elif path.suffix == ".json":
                import json
                with open(path) as f:
                    data = json.load(f)
                    if data:
                        self._config.update(data)
        except Exception as e:
            logger.error("config_load_failed", path=str(path), error=str(e))
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Supports nested keys: "logging.level"
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        keys = key.split(".")
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Tries in order:
        1. Environment variable (uppercase, underscores)
        2. Configuration dictionary
        3. Default value
        
        Args:
            key: Configuration key (supports nested: "logging.level")
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        # Try environment variable
        env_key = key.upper().replace(".", "_")
        if env_key in os.environ:
            return os.environ[env_key]
        
        # Try config dictionary
        keys = key.split(".")
        config = self._config
        
        for k in keys:
            if isinstance(config, dict) and k in config:
                config = config[k]
            else:
                return default
        
        return config
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self._config.copy()
