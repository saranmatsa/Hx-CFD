"""
Dependency Manager - Core Module

A comprehensive dependency management system for the CFD engineering platform.
Automatically detects, installs, verifies, configures, updates, and monitors
all required dependencies.

Architecture:
    DependencyManager
    ├── Tool Registry
    ├── Platform Detector
    ├── Installer Engine
    ├── Version Manager
    ├── Health Checker
    ├── Configuration Manager
    ├── Update Manager
    └── Diagnostics Engine

Each dependency is represented by an adapter implementing the ToolAdapter interface.
"""

from .core.base import ToolAdapter, DependencyStatus, DependencyInfo, HealthCheckResult
from .core.platform import PlatformDetector, Platform, PlatformInfo
from .core.registry import ToolRegistry
from .core.installer import InstallerEngine, InstallResult
from .core.config_manager import ConfigurationManager
from .core.diagnostics import DiagnosticsEngine, DiagnosticResult
from .core.manager import DependencyManager

__all__ = [
    # Base interfaces
    "ToolAdapter",
    "DependencyStatus",
    "DependencyInfo",
    "HealthCheckResult",
    # Platform detection
    "PlatformDetector",
    "Platform",
    "PlatformInfo",
    # Registry
    "ToolRegistry",
    # Installer
    "InstallerEngine",
    "InstallResult",
    # Configuration
    "ConfigurationManager",
    # Diagnostics
    "DiagnosticsEngine",
    "DiagnosticResult",
    # Main manager
    "DependencyManager",
]