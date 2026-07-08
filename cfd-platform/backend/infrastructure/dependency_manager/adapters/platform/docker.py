"""
Docker Adapter for dependency management.

Docker is a containerization platform.
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


class DockerAdapter(ToolAdapter):
    """Adapter for Docker."""
    
    name = "docker"
    display_name = "Docker"
    description = "Containerization platform"
    category = DependencyCategory.PLATFORM
    homepage = "https://www.docker.com/"
    
    def __init__(self):
        super().__init__()
        self._platform = PlatformDetector()
    
    def get_info(self) -> DependencyInfo:
        """Get Docker information."""
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
            documentation="https://docs.docker.com/",
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
        """Find Docker installation path."""
        docker_path = shutil.which("docker")
        if docker_path:
            return Path(docker_path).parent
        return None
    
    def get_version(self) -> Optional[str]:
        """Get Docker version."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return self._parse_version(result.stdout)
            
            return None
        except Exception:
            return None
    
    def _parse_version(self, output: str) -> Optional[str]:
        """Parse version from output."""
        import re
        match = re.search(r"Docker version ([0-9]+\.[0-9]+(?:\.[0-9]+)?)", output)
        if match:
            return match.group(1)
        return None
    
    def verify(self) -> DiagnosticResult:
        """Verify Docker installation."""
        try:
            version = self.get_version()
            if version is None:
                return DiagnosticResult(
                    healthy=False,
                    message="Docker not found",
                    errors=["Docker executable not found"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check if Docker daemon is running
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return DiagnosticResult(
                    healthy=False,
                    message="Docker daemon not running",
                    errors=["Docker daemon is not running or user lacks permission"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            return DiagnosticResult(
                healthy=True,
                message=f"Docker {version} is installed and running",
                errors=[],
                warnings=[],
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
        """Install Docker."""
        platform = self._platform.get_platform()
        
        if platform == Platform.WINDOWS:
            return self._install_windows(**kwargs)
        elif platform == Platform.MACOS:
            return self._install_macos(**kwargs)
        elif platform == Platform.LINUX:
            return self._install_linux(**kwargs)
        
        return False
    
    def _install_windows(self, **kwargs) -> bool:
        """Install Docker on Windows."""
        try:
            # Try winget first
            result = subprocess.run(
                ["winget", "install", "--id", "Docker.DockerDesktop", "-e"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_macos(self, **kwargs) -> bool:
        """Install Docker on macOS."""
        try:
            # Try Homebrew
            result = subprocess.run(
                ["brew", "install", "--cask", "docker"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_linux(self, **kwargs) -> bool:
        """Install Docker on Linux."""
        try:
            # Use Docker's official install script
            result = subprocess.run(
                ["curl", "-fsSL", "https://get.docker.com", "-o", "get-docker.sh"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                return False
            
            result = subprocess.run(
                ["sudo", "sh", "get-docker.sh"],
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure Docker."""
        valid_keys = {"registry", "storage_driver", "log_driver"}
        for key in settings:
            if key not in valid_keys:
                return False
        return True
    
    def _get_dependencies(self) -> List[Any]:
        """Get Docker dependencies."""
        return []
    
    def diagnostics(self) -> DiagnosticResult:
        """Run Docker diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            # Get Docker info
            try:
                info_result = subprocess.run(
                    ["docker", "info", "--format", "{{json .}}"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if info_result.returncode == 0:
                    import json
                    info = json.loads(info_result.stdout)
                    metrics["containers"] = info.get("Containers", 0)
                    metrics["images"] = info.get("Images", 0)
                    metrics["server_version"] = info.get("ServerVersion", "unknown")
            except Exception:
                warnings.append("Could not get Docker info")
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result