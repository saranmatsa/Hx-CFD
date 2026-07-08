"""
Python Adapter for dependency management.

Python is a high-level programming language.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import subprocess
import shutil
import sys

from ..core.base import (
    ToolAdapter,
    DependencyInfo,
    DependencyStatus,
    DependencyCategory,
    DiagnosticResult,
    DiagnosticSeverity
)
from ..core.platform import Platform, PlatformDetector


class PythonAdapter(ToolAdapter):
    """Adapter for Python."""
    
    name = "python"
    display_name = "Python"
    description = "High-level programming language"
    category = DependencyCategory.PLATFORM
    homepage = "https://www.python.org/"
    
    def __init__(self):
        super().__init__()
        self._platform = PlatformDetector()
    
    def get_info(self) -> DependencyInfo:
        """Get Python information."""
        version = self.get_version()
        status = self._determine_status(version)
        
        return DependencyInfo(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            category=self.category,
            status=status,
            installed_version=version,
            required_version=None,
            install_path=self._find_installation_path(),
            homepage=self.homepage,
            documentation="https://docs.python.org/",
            dependencies=self._get_dependencies()
        )
    
    def _determine_status(self, version: Optional[str]) -> DependencyStatus:
        """Determine status based on version."""
        if version is None:
            return DependencyStatus.MISSING
        if self.verify().healthy:
            return DependencyStatus.INSTALLED
        return DependencyStatus.BROKEN
    
    def _find_installation_path(self) -> Optional[Path]:
        """Find Python installation path."""
        python_path = sys.executable
        if python_path:
            return Path(python_path).parent
        return None
    
    def get_version(self) -> Optional[str]:
        """Get Python version."""
        try:
            version = sys.version_info
            return f"{version.major}.{version.minor}.{version.micro}"
        except Exception:
            return None
    
    def verify(self) -> DiagnosticResult:
        """Verify Python installation."""
        try:
            version = self.get_version()
            if version is None:
                return DiagnosticResult(
                    healthy=False,
                    message="Python not found",
                    errors=["Python executable not found"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check if pip is available
            pip_result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            warnings = []
            if pip_result.returncode != 0:
                warnings.append("pip not found - package management may be limited")
            
            return DiagnosticResult(
                healthy=True,
                message=f"Python {version} is installed",
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO
            )
        except Exception as e:
            return DiagnosticResult(
                healthy=False,
                message=f"Verification failed: {str(e)}",
                errors=[str(e)],
                warnings=[],
                severity=DiagnosticSeverity.ERROR
            )
    
    def install(self, **kwargs) -> bool:
        """Install Python."""
        platform = self._platform.get_platform()
        
        if platform == Platform.WINDOWS:
            return self._install_windows(**kwargs)
        elif platform == Platform.MACOS:
            return self._install_macos(**kwargs)
        elif platform == Platform.LINUX:
            return self._install_linux(**kwargs)
        
        return False
    
    def _install_windows(self, **kwargs) -> bool:
        """Install Python on Windows."""
        try:
            # Try winget first
            result = subprocess.run(
                ["winget", "install", "--id", "Python.Python.3.12", "-e"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try Chocolatey
            result = subprocess.run(
                ["choco", "install", "python", "-y"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_macos(self, **kwargs) -> bool:
        """Install Python on macOS."""
        try:
            # Try Homebrew
            result = subprocess.run(
                ["brew", "install", "python"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_linux(self, **kwargs) -> bool:
        """Install Python on Linux."""
        try:
            # Try apt-get
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "python3", "python3-pip"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try yum/dnf
            result = subprocess.run(
                ["sudo", "yum", "install", "-y", "python3", "python3-pip"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try dnf
            result = subprocess.run(
                ["sudo", "dnf", "install", "-y", "python3", "python3-pip"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure Python."""
        valid_keys = {"pip_index_url", "pip_trusted_host", "venv_path"}
        for key in settings:
            if key not in valid_keys:
                return False
        
        # Apply configuration
        try:
            if "pip_index_url" in settings:
                subprocess.run(
                    [sys.executable, "-m", "pip", "config", "set", "global.index-url", settings["pip_index_url"]],
                    check=True
                )
            if "pip_trusted_host" in settings:
                subprocess.run(
                    [sys.executable, "-m", "pip", "config", "set", "global.trusted-host", settings["pip_trusted_host"]],
                    check=True
                )
            return True
        except Exception:
            return False
    
    def _get_dependencies(self) -> List[Any]:
        """Get Python dependencies."""
        return []
    
    def diagnostics(self) -> DiagnosticResult:
        """Run Python diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            # Get pip version
            try:
                pip_result = subprocess.run(
                    [sys.executable, "-m", "pip", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if pip_result.returncode == 0:
                    metrics["pip_version"] = pip_result.stdout.strip()
            except Exception:
                warnings.append("Could not get pip version")
            
            # Check installed packages count
            try:
                list_result = subprocess.run(
                    [sys.executable, "-m", "pip", "list", "--format=freeze"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if list_result.returncode == 0:
                    packages = list_result.stdout.strip().split('\n')
                    metrics["installed_packages"] = len(packages)
            except Exception:
                warnings.append("Could not list installed packages")
            
            # Check virtual environment
            if sys.prefix != sys.base_prefix:
                metrics["virtual_env"] = True
                metrics["venv_path"] = sys.prefix
            else:
                metrics["virtual_env"] = False
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result