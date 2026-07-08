"""
Core base module for Dependency Manager.

Contains the base interface and models for all tool adapters.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class DependencyStatus(str, Enum):
    """Status of a dependency."""
    INSTALLED = "installed"
    MISSING = "missing"
    BROKEN = "broken"
    WRONG_VERSION = "wrong_version"
    MISCONFIGURED = "misconfigured"
    INSTALLING = "installing"
    UPDATING = "updating"
    UNKNOWN = "unknown"


class DependencyCategory(str, Enum):
    """Category of dependency."""
    PLATFORM = "platform"           # OS-level tools (git, docker, etc.)
    PYTHON_PACKAGE = "python"       # Python packages
    NODE_PACKAGE = "node"           # Node.js packages
    ENGINEERING_TOOL = "engineering" # CFD/FEA tools (OpenFOAM, FreeCAD, etc.)
    GPU_DRIVER = "gpu"              # GPU drivers and CUDA
    RUNTIME = "runtime"             # Runtimes (Python, Node, etc.)


class DependencyPriority(str, Enum):
    """Priority of dependency."""
    CRITICAL = "critical"   # Required for platform to function
    HIGH = "high"           # Required for core CFD functionality
    MEDIUM = "medium"       # Important but not critical
    LOW = "low"             # Optional enhancements


class DependencyInfo(BaseModel):
    """Information about a dependency."""
    name: str
    display_name: str
    category: DependencyCategory
    priority: DependencyPriority
    status: DependencyStatus = DependencyStatus.UNKNOWN
    version: Optional[str] = None
    required_version: Optional[str] = None
    path: Optional[str] = None
    install_method: Optional[str] = None
    last_verified: Optional[datetime] = None
    last_check: Optional[datetime] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    
    model_config = {"from_attributes": True}


class HealthCheckResult(BaseModel):
    """Result of a health check."""
    healthy: bool
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DiagnosticIssue(BaseModel):
    """A diagnostic issue found during scanning."""
    severity: str = Field(..., description="error, warning, info")
    category: str
    message: str
    fix_suggestion: Optional[str] = None
    affected_dependency: Optional[str] = None


class DiagnosticResult(BaseModel):
    """Result of diagnostics scan."""
    issues: List[DiagnosticIssue] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)  # counts by severity
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolAdapter(ABC):
    """
    Base interface for all tool adapters.
    
    All engineering tools must implement this interface.
    The Dependency Manager uses adapters to interact with each tool.
    
    Example:
        class FreeCADAdapter(ToolAdapter):
            def detect(self) -> bool:
                # Detection logic
                pass
            
            def install(self) -> bool:
                # Installation logic
                pass
            
            def verify(self) -> HealthCheckResult:
                # Verification logic
                pass
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the tool."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the tool."""
        pass
    
    @property
    @abstractmethod
    def category(self) -> DependencyCategory:
        """Category of the tool."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> DependencyPriority:
        """Priority of the tool."""
        pass
    
    @property
    def required_version(self) -> Optional[str]:
        """Required version, if any."""
        return None
    
    @abstractmethod
    def detect(self) -> bool:
        """
        Detect if the tool is installed.
        
        Returns:
            True if the tool is detected, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_info(self) -> DependencyInfo:
        """
        Get detailed information about the tool.
        
        Returns:
            DependencyInfo with current state of the tool.
        """
        pass
    
    @abstractmethod
    def verify(self) -> HealthCheckResult:
        """
        Verify the tool is working correctly.
        
        Returns:
            HealthCheckResult with verification details.
        """
        pass
    
    def install(self, **kwargs) -> bool:
        """
        Install the tool.
        
        Args:
            **kwargs: Installation options specific to the tool.
            
        Returns:
            True if installation succeeded, False otherwise.
        """
        raise NotImplementedError(f"{self.name} does not support installation")
    
    def uninstall(self) -> bool:
        """
        Uninstall the tool.
        
        Returns:
            True if uninstallation succeeded, False otherwise.
        """
        raise NotImplementedError(f"{self.name} does not support uninstallation")
    
    def update(self, version: Optional[str] = None) -> bool:
        """
        Update the tool to a specific or latest version.
        
        Args:
            version: Target version, or None for latest.
            
        Returns:
            True if update succeeded, False otherwise.
        """
        raise NotImplementedError(f"{self.name} does not support updates")
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the tool with the given configuration.
        
        Args:
            config: Configuration dictionary.
            
        Returns:
            True if configuration succeeded, False otherwise.
        """
        return True
    
    def get_version(self) -> Optional[str]:
        """
        Get the installed version of the tool.
        
        Returns:
            Version string, or None if not installed.
        """
        return None
    
    def get_path(self) -> Optional[str]:
        """
        Get the installation path of the tool.
        
        Returns:
            Path string, or None if not installed.
        """
        return None
    
    def diagnostics(self) -> List[DiagnosticIssue]:
        """
        Run diagnostics on the tool.
        
        Returns:
            List of diagnostic issues found.
        """
        return []


class PlatformAdapter(ToolAdapter):
    """Base class for platform-level tools."""
    
    @property
    def category(self) -> DependencyCategory:
        return DependencyCategory.PLATFORM


class EngineeringToolAdapter(ToolAdapter):
    """Base class for engineering tools."""
    
    @property
    def category(self) -> DependencyCategory:
        return DependencyCategory.ENGINEERING_TOOL


class PythonPackageAdapter(ToolAdapter):
    """Base class for Python packages."""
    
    @property
    def category(self) -> DependencyCategory:
        return DependencyCategory.PYTHON_PACKAGE
    
    @property
    def install_method(self) -> str:
        return "pip"


class NodePackageAdapter(ToolAdapter):
    """Base class for Node.js packages."""
    
    @property
    def category(self) -> DependencyCategory:
        return DependencyCategory.NODE_PACKAGE
    
    @property
    def install_method(self) -> str:
        return "pnpm"