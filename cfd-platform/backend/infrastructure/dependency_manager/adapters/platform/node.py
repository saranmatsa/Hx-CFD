"""
Node.js Adapter for dependency management.

Node.js is a JavaScript runtime built on Chrome's V8 engine.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import subprocess
import shutil

from ..core.base import (
    ToolAdapter,
    DependencyInfo,
    DependencyStatus,
    DependencyCategory,
    DiagnosticResult,
    DiagnosticSeverity
)
from ..core.platform import Platform, PlatformDetector


class NodeAdapter(ToolAdapter):
    """Adapter for Node.js."""
    
    name = "node"
    display_name = "Node.js"
    description = "JavaScript runtime built on Chrome's V8 engine"
    category = DependencyCategory.PLATFORM
    homepage = "https://nodejs.org/"
    
    def __init__(self):
        super().__init__()
        self._platform = PlatformDetector()
    
    def get_info(self) -> DependencyInfo:
        """Get Node.js information."""
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
            documentation="https://nodejs.org/docs/",
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
        """Find Node.js installation path."""
        node_path = shutil.which("node")
        if node_path:
            return Path(node_path).parent
        return None
    
    def get_version(self) -> Optional[str]:
        """Get Node.js version."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip().lstrip('v')
            
            return None
        except Exception:
            return None
    
    def verify(self) -> DiagnosticResult:
        """Verify Node.js installation."""
        try:
            version = self.get_version()
            if version is None:
                return DiagnosticResult(
                    healthy=False,
                    message="Node.js not found",
                    errors=["Node.js executable not found"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check if npm is available
            npm_result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            warnings = []
            if npm_result.returncode != 0:
                warnings.append("npm not found - package management may be limited")
            
            return DiagnosticResult(
                healthy=True,
                message=f"Node.js {version} is installed",
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
        """Install Node.js."""
        platform = self._platform.get_platform()
        
        if platform == Platform.WINDOWS:
            return self._install_windows(**kwargs)
        elif platform == Platform.MACOS:
            return self._install_macos(**kwargs)
        elif platform == Platform.LINUX:
            return self._install_linux(**kwargs)
        
        return False
    
    def _install_windows(self, **kwargs) -> bool:
        """Install Node.js on Windows."""
        try:
            # Try winget first
            result = subprocess.run(
                ["winget", "install", "--id", "OpenJS.NodeJS.LTS", "-e"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try Chocolatey
            result = subprocess.run(
                ["choco", "install", "nodejs", "-y"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_macos(self, **kwargs) -> bool:
        """Install Node.js on macOS."""
        try:
            # Try Homebrew
            result = subprocess.run(
                ["brew", "install", "node"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_linux(self, **kwargs) -> bool:
        """Install Node.js on Linux."""
        try:
            # Try apt-get
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "nodejs"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try NodeSource repository for newer versions
            result = subprocess.run(
                ["curl", "-fsSL", "https://deb.nodesource.com/setup_lts.x", "-o", "nodesource_setup.sh"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                subprocess.run(
                    ["sudo", "bash", "nodesource_setup.sh"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                subprocess.run(
                    ["sudo", "apt-get", "install", "-y", "nodejs"],
                    capture_output=True,
                    text=True
                )
                return True
            
            return False
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure Node.js."""
        valid_keys = {"registry", "prefix", "cache"}
        for key in settings:
            if key not in valid_keys:
                return False
        
        # Apply configuration
        try:
            if "registry" in settings:
                subprocess.run(
                    ["npm", "config", "set", "registry", settings["registry"]],
                    check=True
                )
            if "prefix" in settings:
                subprocess.run(
                    ["npm", "config", "set", "prefix", settings["prefix"]],
                    check=True
                )
            return True
        except Exception:
            return False
    
    def _get_dependencies(self) -> List[Any]:
        """Get Node.js dependencies."""
        return []
    
    def diagnostics(self) -> DiagnosticResult:
        """Run Node.js diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            # Get npm version
            try:
                npm_result = subprocess.run(
                    ["npm", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if npm_result.returncode == 0:
                    metrics["npm_version"] = npm_result.stdout.strip()
            except Exception:
                warnings.append("Could not get npm version")
            
            # Check global packages
            try:
                list_result = subprocess.run(
                    ["npm", "list", "-g", "--depth=0"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if list_result.returncode == 0:
                    packages = list_result.stdout.strip().split('\n')
                    metrics["global_packages"] = len([p for p in packages if p.startswith('├──') or p.startswith('└──')])
            except Exception:
                warnings.append("Could not list global packages")
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result