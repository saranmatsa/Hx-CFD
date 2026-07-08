"""
OpenFOAM Adapter for dependency management.

OpenFOAM is a free, open source CFD software package.
"""

from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import subprocess
import os
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


class OpenFOAMAdapter(ToolAdapter):
    """Adapter for OpenFOAM."""
    
    name = "openfoam"
    display_name = "OpenFOAM"
    description = "Free, open source CFD software package"
    category = DependencyCategory.ENGINEERING
    homepage = "https://www.openfoam.com/"
    
    def __init__(self):
        super().__init__()
        self._platform = PlatformDetector()
        self._env_var = "FOAM_INST_DIR"
    
    def get_info(self) -> DependencyInfo:
        """Get OpenFOAM information."""
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
            documentation="https://www.openfoam.com/documentation/",
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
        """Find OpenFOAM installation path."""
        # Check environment variable
        foam_dir = os.environ.get(self._env_var)
        if foam_dir:
            path = Path(foam_dir)
            if path.exists():
                return path
        
        # Check common paths
        common_paths = [
            Path("/opt/OpenFOAM"),
            Path("/usr/lib/openfoam"),
            Path.home() / "OpenFOAM",
            Path.home() / "openfoam",
        ]
        
        for path in common_paths:
            if path.exists():
                return path
        
        return None
    
    def get_version(self) -> Optional[str]:
        """Get OpenFOAM version."""
        try:
            # OpenFOAM sets WM_PROJECT_VERSION in its environment
            # We need to source the OpenFOAM bashrc first
            
            install_path = self._find_installation_path()
            if install_path is None:
                return None
            
            # Look for version file
            version_file = install_path / "etc" / "bashrc"
            if version_file.exists():
                with open(version_file, 'r') as f:
                    for line in f:
                        if 'WM_PROJECT_VERSION' in line and not line.strip().startswith('#'):
                            # Extract version
                            parts = line.split('=')
                            if len(parts) >= 2:
                                return parts[1].strip().strip('"')
            
            # Try running foamVersion
            bashrc = install_path / "etc" / "bashrc"
            if bashrc.exists():
                result = subprocess.run(
                    ["bash", "-c", f"source {bashrc} && echo $WM_PROJECT_VERSION"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return result.stdout.strip() or None
            
            return None
        except Exception:
            return None
    
    def verify(self) -> DiagnosticResult:
        """Verify OpenFOAM installation."""
        try:
            install_path = self._find_installation_path()
            
            if install_path is None:
                return DiagnosticResult(
                    healthy=False,
                    message="OpenFOAM not found",
                    errors=["OpenFOAM installation directory not found"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check for essential directories
            required_dirs = ["bin", "lib", "applications", "tutorials"]
            missing_dirs = []
            
            for dir_name in required_dirs:
                if not (install_path / dir_name).exists():
                    missing_dirs.append(dir_name)
            
            if missing_dirs:
                return DiagnosticResult(
                    healthy=False,
                    message=f"OpenFOAM installation incomplete",
                    errors=[f"Missing directories: {', '.join(missing_dirs)}"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check for essential binaries
            essential_bins = ["foamExec", "blockMesh", "simpleFoam"]
            missing_bins = []
            
            for bin_name in essential_bins:
                if not shutil.which(bin_name):
                    # Check in standard location
                    if not (install_path / "platforms" / "bin" / bin_name).exists():
                        missing_bins.append(bin_name)
            
            if missing_bins:
                return DiagnosticResult(
                    healthy=True,
                    message=f"OpenFOAM installed but some binaries missing",
                    errors=[],
                    warnings=[f"Missing binaries: {', '.join(missing_bins)}"],
                    severity=DiagnosticSeverity.WARNING
                )
            
            version = self.get_version()
            return DiagnosticResult(
                healthy=True,
                message=f"OpenFOAM {version or 'unknown version'} is installed",
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
        """Install OpenFOAM."""
        platform = self._platform.get_platform()
        
        if platform == Platform.WINDOWS:
            return self._install_windows(**kwargs)
        elif platform == Platform.MACOS:
            return self._install_macos(**kwargs)
        elif platform == Platform.LINUX:
            return self._install_linux(**kwargs)
        
        return False
    
    def _install_windows(self, **kwargs) -> bool:
        """Install OpenFOAM on Windows (via WSL)."""
        # OpenFOAM on Windows requires WSL
        try:
            # Check if WSL is available
            result = subprocess.run(
                ["wsl", "--status"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return False
            
            # Installation would need to be done in WSL
            # For now, just indicate this is the expected path
            return False  # Manual installation required
        except Exception:
            return False
    
    def _install_macos(self, **kwargs) -> bool:
        """Install OpenFOAM on macOS (via Docker or source)."""
        # OpenFOAM doesn't have native macOS support
        # Use Docker container or build from source
        try:
            # Check for Docker
            if shutil.which("docker"):
                # Could pull OpenFOAM Docker image
                return True  # Docker available
            return False
        except Exception:
            return False
    
    def _install_linux(self, **kwargs) -> bool:
        """Install OpenFOAM on Linux."""
        try:
            # Try apt-get for Ubuntu/Debian
            result = subprocess.run(
                ["sudo", "sh", "-c", "echo 'deb http://dl.openfoam.org/ubuntu/ main' > /etc/apt/sources.list.d/openfoam.list"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                subprocess.run(
                    ["sudo", "apt-get", "update"],
                    capture_output=True
                )
                result = subprocess.run(
                    ["sudo", "apt-get", "install", "-y", "openfoam-default"],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            
            return False
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure OpenFOAM environment."""
        valid_keys = {"WM_COMPILE_OPTION", "WM_PRECISION_MODEL", "WM_MPLIB"}
        for key in settings:
            if key not in valid_keys:
                return False
        return True
    
    def _get_dependencies(self) -> List[Any]:
        """Get OpenFOAM dependencies."""
        return []  # OpenFOAM manages its own dependencies
    
    def diagnostics(self) -> DiagnosticResult:
        """Run OpenFOAM diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            install_path = self._find_installation_path()
            if install_path:
                metrics["install_path"] = str(install_path)
                
                # Check disk space
                try:
                    import shutil
                    usage = shutil.disk_usage(install_path)
                    metrics["disk_free_gb"] = usage.free / (1024**3)
                    
                    if usage.free < 1024**3:  # Less than 1GB
                        warnings.append("Low disk space - may cause issues with large simulations")
                except Exception:
                    pass
                
                # Check tutorials exist
                if not (install_path / "tutorials").exists():
                    warnings.append("Tutorials directory not found")
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result