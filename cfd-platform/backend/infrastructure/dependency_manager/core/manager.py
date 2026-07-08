"""
Main Dependency Manager that orchestrates all components.

The DependencyManager provides a unified interface for:
- Tool registration and discovery
- Installation and uninstallation
- Configuration management
- Diagnostics and health monitoring
- Dependency resolution
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

from .base import (
    ToolAdapter,
    DependencyInfo,
    DependencyStatus,
    DependencyCategory,
    DiagnosticResult,
    DiagnosticSeverity
)
from .platform import PlatformDetector, Platform, PackageManager
from .registry import ToolRegistry, get_registry
from .installer import InstallerEngine, InstallResult, InstallProgress
from .config_manager import ConfigurationManager, ToolConfig, get_config_manager
from .diagnostics import DiagnosticsEngine, DiagnosticReport, ToolDiagnostic


class DependencyManager:
    """
    Main dependency management orchestrator.
    
    This class provides the unified API for all dependency operations:
    - Tool management (register, unregister, list)
    - Installation operations
    - Configuration management
    - Diagnostics and health monitoring
    - Dependency resolution
    """
    
    _instance: Optional["DependencyManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._registry = get_registry()
        self._config_manager = get_config_manager()
        self._installer = InstallerEngine()
        self._diagnostics = DiagnosticsEngine()
        self._platform_detector = PlatformDetector()
        
        self._initialized = True
    
    # ==================== Platform Information ====================
    
    def get_platform_info(self) -> Dict[str, Any]:
        """Get information about the current platform."""
        return self._platform_detector.detect()
    
    def get_platform(self) -> Platform:
        """Get the current platform."""
        return self._platform_detector.get_platform()
    
    # ==================== Tool Registration ====================
    
    def register_tool(self, adapter: ToolAdapter) -> None:
        """
        Register a tool adapter.
        
        Args:
            adapter: The tool adapter to register.
        """
        self._registry.register(adapter)
    
    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool.
        
        Args:
            name: Name of the tool to unregister.
            
        Returns:
            True if unregistered, False if not found.
        """
        return self._registry.unregister(name)
    
    def get_tool(self, name: str) -> Optional[ToolAdapter]:
        """
        Get a tool by name.
        
        Args:
            name: Name of the tool.
            
        Returns:
            ToolAdapter, or None if not found.
        """
        return self._registry.get(name)
    
    def list_tools(
        self,
        category: Optional[DependencyCategory] = None,
        status: Optional[DependencyStatus] = None
    ) -> List[DependencyInfo]:
        """
        List all tools, optionally filtered.
        
        Args:
            category: Filter by category.
            status: Filter by status.
            
        Returns:
            List of DependencyInfo for matching tools.
        """
        if category:
            tools = self._registry.get_by_category(category)
        else:
            tools = self._registry.get_all()
        
        results = []
        for tool in tools:
            info = tool.get_info()
            if status is None or info.status == status:
                results.append(info)
        
        return results
    
    def get_tool_count(self) -> int:
        """Get the total number of registered tools."""
        return len(self._registry)
    
    # ==================== Installation Operations ====================
    
    def install(
        self,
        name: str,
        **kwargs
    ) -> tuple[bool, str]:
        """
        Install a tool.
        
        Args:
            name: Name of the tool to install.
            **kwargs: Additional installation options.
            
        Returns:
            Tuple of (success, message).
        """
        adapter = self._registry.get(name)
        if adapter is None:
            return False, f"Tool '{name}' not found"
        
        result, message = self._installer.install(adapter, **kwargs)
        
        # Clear cache after installation
        self._registry.clear_cache(name)
        
        return result in (InstallResult.SUCCESS, InstallResult.ALREADY_INSTALLED), message
    
    def install_python_package(
        self,
        package: str,
        version: Optional[str] = None,
        extras: Optional[List[str]] = None,
        upgrade: bool = False
    ) -> tuple[bool, str]:
        """
        Install a Python package.
        
        Args:
            package: Package name.
            version: Specific version.
            extras: Extra requirements.
            upgrade: Whether to upgrade.
            
        Returns:
            Tuple of (success, message).
        """
        result, message = self._installer.install_python_package(
            package, version, extras, upgrade
        )
        return result == InstallResult.SUCCESS, message
    
    def uninstall(self, name: str) -> tuple[bool, str]:
        """
        Uninstall a tool.
        
        Args:
            name: Name of the tool to uninstall.
            
        Returns:
            Tuple of (success, message).
        """
        adapter = self._registry.get(name)
        if adapter is None:
            return False, f"Tool '{name}' not found"
        
        try:
            result = adapter.uninstall()
            if result:
                self._registry.clear_cache(name)
                return True, f"Successfully uninstalled {name}"
            else:
                return False, f"Failed to uninstall {name}"
        except NotImplementedError:
            return False, f"{name} does not support uninstallation"
        except Exception as e:
            return False, f"Uninstallation failed: {str(e)}"
    
    def update(self, name: str) -> tuple[bool, str]:
        """
        Update a tool to the latest version.
        
        Args:
            name: Name of the tool to update.
            
        Returns:
            Tuple of (success, message).
        """
        adapter = self._registry.get(name)
        if adapter is None:
            return False, f"Tool '{name}' not found"
        
        try:
            result = adapter.update()
            if result:
                self._registry.clear_cache(name)
                return True, f"Successfully updated {name}"
            else:
                return False, f"No update available for {name}"
        except NotImplementedError:
            return False, f"{name} does not support updates"
        except Exception as e:
            return False, f"Update failed: {str(e)}"
    
    def add_progress_callback(self, callback: Callable[[InstallProgress], None]) -> None:
        """Add a callback for installation progress."""
        self._installer.add_progress_callback(callback)
    
    def remove_progress_callback(self, callback: Callable[[InstallProgress], None]) -> None:
        """Remove a progress callback."""
        self._installer.remove_progress_callback(callback)
    
    # ==================== Configuration ====================
    
    def get_config(self, name: str) -> Optional[ToolConfig]:
        """
        Get configuration for a tool.
        
        Args:
            name: Name of the tool.
            
        Returns:
            ToolConfig, or None if not configured.
        """
        return self._config_manager.get(name)
    
    def set_config(self, name: str, config: ToolConfig) -> None:
        """
        Set configuration for a tool.
        
        Args:
            name: Name of the tool.
            config: Configuration to set.
        """
        self._config_manager.set(name, config)
    
    def update_config(self, name: str, **kwargs) -> None:
        """
        Update specific configuration values.
        
        Args:
            name: Name of the tool.
            **kwargs: Values to update.
        """
        self._config_manager.update(name, **kwargs)
    
    def get_all_configs(self) -> Dict[str, ToolConfig]:
        """Get all tool configurations."""
        return self._config_manager.get_all()
    
    def configure(self, name: str, **settings) -> tuple[bool, str]:
        """
        Configure a tool.
        
        Args:
            name: Name of the tool.
            **settings: Settings to apply.
            
        Returns:
            Tuple of (success, message).
        """
        adapter = self._registry.get(name)
        if adapter is None:
            return False, f"Tool '{name}' not found"
        
        try:
            result = adapter.configure(**settings)
            if result:
                # Update config manager
                self._config_manager.update(name, settings=settings)
                return True, f"Successfully configured {name}"
            else:
                return False, f"Failed to configure {name}"
        except NotImplementedError:
            return False, f"{name} does not support configuration"
        except Exception as e:
            return False, f"Configuration failed: {str(e)}"
    
    # ==================== Diagnostics ====================
    
    def diagnose(self, name: str, deep: bool = False) -> Optional[ToolDiagnostic]:
        """
        Run diagnostics on a tool.
        
        Args:
            name: Name of the tool.
            deep: Whether to run deep diagnostics.
            
        Returns:
            ToolDiagnostic, or None if not found.
        """
        return self._diagnostics.diagnose_tool(name, deep)
    
    def diagnose_all(self, deep: bool = False) -> DiagnosticReport:
        """
        Run diagnostics on all tools.
        
        Args:
            deep: Whether to run deep diagnostics.
            
        Returns:
            DiagnosticReport for the system.
        """
        return self._diagnostics.diagnose_all(deep)
    
    def get_health(self) -> Dict[str, Any]:
        """
        Get system health summary.
        
        Returns:
            Dictionary with health summary.
        """
        return self._diagnostics.get_health_summary()
    
    def check_dependencies(self, name: str) -> List[Dict[str, Any]]:
        """
        Check if a tool's dependencies are satisfied.
        
        Args:
            name: Name of the tool.
            
        Returns:
            List of dependency status dictionaries.
        """
        return self._diagnostics.check_dependencies(name)
    
    # ==================== Discovery ====================
    
    def detect_all(self) -> List[DependencyInfo]:
        """
        Detect all registered tools.
        
        Returns:
            List of DependencyInfo with detection results.
        """
        return self._registry.get_all_info()
    
    def detect_tool(self, name: str) -> Optional[DependencyInfo]:
        """
        Detect a specific tool.
        
        Args:
            name: Name of the tool.
            
        Returns:
            DependencyInfo, or None if not found.
        """
        return self._registry.get_info(name)
    
    def verify_installation(self, name: str) -> tuple[bool, str]:
        """
        Verify a tool's installation.
        
        Args:
            name: Name of the tool.
            
        Returns:
            Tuple of (valid, message).
        """
        adapter = self._registry.get(name)
        if adapter is None:
            return False, f"Tool '{name}' not found"
        
        result = adapter.verify()
        return result.healthy, result.message
    
    # ==================== Summary ====================
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the dependency system.
        
        Returns:
            Dictionary with summary information.
        """
        health = self.get_health()
        platform = self.get_platform_info()
        
        return {
            "platform": platform,
            "health": health,
            "tools": {
                "total": len(self._registry),
                "by_category": self._get_category_counts(),
                "by_status": self._registry.get_status_summary()
            },
            "configuration": {
                "total_configs": len(self._config_manager.get_all()),
                "enabled": len(self._config_manager.get_enabled())
            }
        }
    
    def _get_category_counts(self) -> Dict[str, int]:
        """Get counts of tools by category."""
        counts = {}
        for category in DependencyCategory:
            tools = self._registry.get_by_category(category)
            if tools:
                counts[category.value] = len(tools)
        return counts
    
    # ==================== Cache Management ====================
    
    def clear_cache(self, name: Optional[str] = None) -> None:
        """
        Clear detection cache.
        
        Args:
            name: Specific tool to clear, or None for all.
        """
        self._registry.clear_cache(name)


# Global dependency manager instance
_dependency_manager: Optional[DependencyManager] = None


def get_dependency_manager() -> DependencyManager:
    """Get the global dependency manager instance."""
    global _dependency_manager
    if _dependency_manager is None:
        _dependency_manager = DependencyManager()
    return _dependency_manager


# Convenience functions
def register(adapter: ToolAdapter) -> None:
    """Register a tool adapter."""
    get_dependency_manager().register_tool(adapter)


def install(name: str, **kwargs) -> tuple[bool, str]:
    """Install a tool."""
    return get_dependency_manager().install(name, **kwargs)


def uninstall(name: str) -> tuple[bool, str]:
    """Uninstall a tool."""
    return get_dependency_manager().uninstall(name)


def diagnose(name: str, deep: bool = False) -> Optional[ToolDiagnostic]:
    """Diagnose a tool."""
    return get_dependency_manager().diagnose(name, deep)


def health() -> Dict[str, Any]:
    """Get system health."""
    return get_dependency_manager().get_health()


def summary() -> Dict[str, Any]:
    """Get system summary."""
    return get_dependency_manager().get_summary()