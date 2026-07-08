"""
Configuration Manager for storing and retrieving dependency configurations.

The configuration manager handles:
- Storage of tool paths and settings
- Environment variable management
- Configuration persistence
- Default configurations
"""

import os
import json
import shutil
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel

from .base import DependencyInfo


class ToolConfig(BaseModel):
    """Configuration for a single tool."""
    name: str
    path: Optional[str] = None
    version: Optional[str] = None
    enabled: bool = True
    settings: Dict[str, Any] = {}
    environment: Dict[str, str] = {}
    last_updated: datetime = None
    
    def __init__(self, **data):
        if data.get("last_updated") is None:
            data["last_updated"] = datetime.utcnow()
        super().__init__(**data)


class ConfigurationManager:
    """
    Manages configuration for all dependencies.
    
    Configuration is stored in:
    - Windows: %APPDATA%/cfd-platform/config.json
    - Linux/macOS: ~/.config/cfd-platform/config.json
    
    Also supports environment variable overrides:
    - CFD_<TOOL>_PATH: Override path for a tool
    - CFD_<TOOL>_ENABLED: Enable/disable a tool
    """
    
    _instance: Optional["ConfigurationManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._config_dir = self._get_config_dir()
        self._config_file = self._config_dir / "dependencies.json"
        self._config: Dict[str, ToolConfig] = {}
        self._env_overrides: Dict[str, Dict[str, str]] = {}
        
        self._load_config()
        self._initialized = True
    
    def _get_config_dir(self) -> Path:
        """Get the configuration directory."""
        if os.name == "nt":  # Windows
            base = Path(os.getenv("APPDATA", os.path.expanduser("~")))
        else:  # Linux/macOS
            base = Path(os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config")))
        
        config_dir = base / "cfd-platform"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r") as f:
                    data = json.load(f)
                    for name, tool_data in data.items():
                        self._config[name] = ToolConfig(**tool_data)
            except Exception:
                pass  # Start with empty config on error
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            data = {
                name: tool.model_dump()
                for name, tool in self._config.items()
            }
            with open(self._config_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass  # Ignore save errors
    
    def _get_env_overrides(self, name: str) -> Dict[str, str]:
        """Get environment variable overrides for a tool."""
        if name in self._env_overrides:
            return self._env_overrides[name]
        
        prefix = f"CFD_{name.upper().replace('-', '_')}_"
        overrides = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                setting = key[len(prefix):].lower()
                overrides[setting] = value
        
        self._env_overrides[name] = overrides
        return overrides
    
    def get(self, name: str) -> Optional[ToolConfig]:
        """
        Get configuration for a tool.
        
        Args:
            name: Name of the tool.
            
        Returns:
            ToolConfig, or None if not configured.
        """
        # Check environment overrides first
        env_overrides = self._get_env_overrides(name)
        
        if name in self._config:
            config = self._config[name]
            # Apply environment overrides
            if "path" in env_overrides:
                config.path = env_overrides["path"]
            if "enabled" in env_overrides:
                config.enabled = env_overrides["enabled"].lower() in ("true", "1", "yes")
            return config
        
        # Create default config from environment
        if env_overrides:
            config = ToolConfig(
                name=name,
                path=env_overrides.get("path"),
                enabled="enabled" not in env_overrides or env_overrides["enabled"].lower() in ("true", "1", "yes"),
                settings={k: v for k, v in env_overrides.items() if k not in ("path", "enabled")}
            )
            return config
        
        return None
    
    def set(self, name: str, config: ToolConfig) -> None:
        """
        Set configuration for a tool.
        
        Args:
            name: Name of the tool.
            config: Configuration to set.
        """
        config.name = name
        config.last_updated = datetime.utcnow()
        self._config[name] = config
        self._save_config()
    
    def update(self, name: str, **kwargs) -> None:
        """
        Update specific configuration values.
        
        Args:
            name: Name of the tool.
            **kwargs: Values to update.
        """
        if name in self._config:
            config = self._config[name]
        else:
            config = ToolConfig(name=name)
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        self.set(name, config)
    
    def delete(self, name: str) -> bool:
        """
        Delete configuration for a tool.
        
        Args:
            name: Name of the tool.
            
        Returns:
            True if deleted, False if not found.
        """
        if name in self._config:
            del self._config[name]
            self._save_config()
            return True
        return False
    
    def get_all(self) -> Dict[str, ToolConfig]:
        """
        Get all configurations.
        
        Returns:
            Dictionary of all tool configurations.
        """
        return dict(self._config)
    
    def get_enabled(self) -> List[str]:
        """
        Get list of enabled tool names.
        
        Returns:
            List of enabled tool names.
        """
        return [
            name for name, config in self._config.items()
            if config.enabled
        ]
    
    def get_disabled(self) -> List[str]:
        """
        Get list of disabled tool names.
        
        Returns:
            List of disabled tool names.
        """
        return [
            name for name, config in self._config.items()
            if not config.enabled
        ]
    
    def get_path(self, name: str) -> Optional[str]:
        """
        Get the configured path for a tool.
        
        Args:
            name: Name of the tool.
            
        Returns:
            Path string, or None if not configured.
        """
        config = self.get(name)
        return config.path if config else None
    
    def set_path(self, name: str, path: str) -> None:
        """
        Set the path for a tool.
        
        Args:
            name: Name of the tool.
            path: Path to set.
        """
        self.update(name, path=path)
    
    def get_setting(self, name: str, key: str, default: Any = None) -> Any:
        """
        Get a specific setting for a tool.
        
        Args:
            name: Name of the tool.
            key: Setting key.
            default: Default value if not found.
            
        Returns:
            Setting value or default.
        """
        config = self.get(name)
        if config:
            return config.settings.get(key, default)
        return default
    
    def set_setting(self, name: str, key: str, value: Any) -> None:
        """
        Set a specific setting for a tool.
        
        Args:
            name: Name of the tool.
            key: Setting key.
            value: Value to set.
        """
        config = self.get(name)
        if config is None:
            config = ToolConfig(name=name)
        
        config.settings[key] = value
        self.set(name, config)
    
    def get_environment(self, name: str) -> Dict[str, str]:
        """
        Get environment variables for a tool.
        
        Args:
            name: Name of the tool.
            
        Returns:
            Dictionary of environment variables.
        """
        config = self.get(name)
        return dict(config.environment) if config else {}
    
    def set_environment(self, name: str, env: Dict[str, str]) -> None:
        """
        Set environment variables for a tool.
        
        Args:
            name: Name of the tool.
            env: Environment variables to set.
        """
        config = self.get(name)
        if config is None:
            config = ToolConfig(name=name)
        
        config.environment = env
        self.set(name, config)
    
    def apply_environment(self, name: str) -> None:
        """
        Apply environment variables for a tool to the current process.
        
        Args:
            name: Name of the tool.
        """
        env = self.get_environment(name)
        for key, value in env.items():
            os.environ[key] = value
    
    def reset(self) -> None:
        """Reset all configuration to defaults."""
        self._config.clear()
        self._save_config()
    
    def export_config(self) -> str:
        """
        Export configuration as JSON string.
        
        Returns:
            JSON string of configuration.
        """
        data = {
            name: tool.model_dump()
            for name, tool in self._config.items()
        }
        return json.dumps(data, indent=2, default=str)
    
    def import_config(self, json_str: str) -> bool:
        """
        Import configuration from JSON string.
        
        Args:
            json_str: JSON configuration string.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            data = json.loads(json_str)
            self._config.clear()
            for name, tool_data in data.items():
                self._config[name] = ToolConfig(**tool_data)
            self._save_config()
            return True
        except Exception:
            return False


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager