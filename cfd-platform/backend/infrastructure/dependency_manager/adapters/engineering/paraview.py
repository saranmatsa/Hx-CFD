"""
ParaView Adapter for dependency management.

ParaView is an open-source, multi-platform data analysis and visualization application.
"""

from typing import Dict, List, Optional, Any, Tuple
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


class ParaViewAdapter(ToolAdapter):
    """Adapter for ParaView."""
    
    name = "paraview"
    display_name = "ParaView"
    description = "Data analysis and visualization application"
    category = DependencyCategory.ENGINEERING
    homepage = "https://www.paraview.org/"
    
    def __init__(self):
        super().__init__()
        self._platform = PlatformDetector()
        self._install_paths = self._get_default_paths()
    
    def _get_default_paths(self) -> Dict[str, List[Path]]:
        """Get default installation paths for each platform."""
        return {
            "windows": [
                Path("C:/Program Files/ParaView"),
                Path("C:/Program Files (x86)/ParaView"),
            ],
            "macos": [
                Path("/Applications/ParaView.app"),
                Path("/opt/paraview"),
            ],
            "linux": [
                Path("/usr/bin/paraview"),
                Path("/usr/local/bin/paraview"),
                Path("/opt/paraview"),
                Path.home() / "paraview",
            ]
        }
    
    def get_info(self) -> DependencyInfo:
        """Get ParaView information."""
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
            documentation="https://docs.paraview.org/",
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
        """Find ParaView installation path."""
        platform = self._platform.get_platform()
        
        # Check common paths
        paths = self._install_paths.get(platform.value, [])
        for path in paths:
            if path.exists():
                return path
        
        # Try to find using which/where
        try:
            if platform == Platform.WINDOWS:
                result = subprocess.run(
                    ["where", "paraview"],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["which", "paraview"],
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0:
                path = Path(result.stdout.strip().split('\n')[0])
                if path.exists():
                    return path.parent if path.is_file() else path
        except Exception:
            pass
        
        return None
    
    def get_version(self) -> Optional[str]:
        """Get ParaView version."""
        try:
            paraview_cmd = self._find_executable()
            if paraview_cmd is None:
                return None
            
            # ParaView --version outputs to stderr
            result = subprocess.run(
                [str(paraview_cmd), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return self._parse_version(result.stdout + result.stderr)
            
            return None
        except Exception:
            return None
    
    def _find_executable(self) -> Optional[Path]:
        """Find ParaView executable."""
        install_path = self._find_installation_path()
        if install_path:
            # Look for paraview executable
            if install_path.name == "bin":
                for exe in ["paraview", "paraview.exe", "pvpython"]:
                    exe_path = install_path / exe
                    if exe_path.exists():
                        return exe_path
            # Check if install_path itself is the executable
            for exe in ["paraview", "paraview.exe"]:
                exe_path = install_path / exe
                if exe_path.exists():
                    return exe_path
        
        # Try using shutil.which
        exe = shutil.which("paraview") or shutil.which("pvpython")
        if exe:
            return Path(exe)
        
        return None
    
    def _parse_version(self, output: str) -> Optional[str]:
        """Parse version from output."""
        import re
        
        # Look for version pattern
        patterns = [
            r"paraview\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
            r"([0-9]+\.[0-9]+(?:\.[0-9]+)?)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def verify(self) -> DiagnosticResult:
        """Verify ParaView installation."""
        try:
            version = self.get_version()
            if version is None:
                return DiagnosticResult(
                    healthy=False,
                    message="ParaView not found",
                    errors=["ParaView executable not found"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check if we can run paraview
            paraview_cmd = self._find_executable()
            if paraview_cmd is None:
                return DiagnosticResult(
                    healthy=False,
                    message="ParaView executable not accessible",
                    errors=["Cannot find ParaView executable"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            return DiagnosticResult(
                healthy=True,
                message=f"ParaView {version} is installed",
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
        """Install ParaView."""
        platform = self._platform.get_platform()
        
        if platform == Platform.WINDOWS:
            return self._install_windows(**kwargs)
        elif platform == Platform.MACOS:
            return self._install_macos(**kwargs)
        elif platform == Platform.LINUX:
            return self._install_linux(**kwargs)
        
        return False
    
    def _install_windows(self, **kwargs) -> bool:
        """Install ParaView on Windows."""
        try:
            # Try winget first
            result = subprocess.run(
                ["winget", "install", "--id", "Kitware.ParaView", "-e"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_macos(self, **kwargs) -> bool:
        """Install ParaView on macOS."""
        try:
            # Try Homebrew
            result = subprocess.run(
                ["brew", "install", "--cask", "paraview"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_linux(self, **kwargs) -> bool:
        """Install ParaView on Linux."""
        try:
            # Try apt-get
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "paraview"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try snap
            result = subprocess.run(
                ["sudo", "snap", "install", "paraview", "--classic"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure ParaView."""
        valid_keys = {"render_view", "background_color", "cache_size", "number_of_threads"}
        for key in settings:
            if key not in valid_keys:
                return False
        return True
    
    def _get_dependencies(self) -> List[Any]:
        """Get ParaView dependencies."""
        return []  # ParaView is self-contained
    
    def diagnostics(self) -> DiagnosticResult:
        """Run ParaView diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            install_path = self._find_installation_path()
            if install_path:
                metrics["install_path"] = str(install_path)
                
                # Check for plugins directory
                plugins_dir = install_path / "lib" / "paraview" / "plugins"
                if not plugins_dir.exists():
                    warnings.append("Plugins directory not found")
                
                # Check for Python modules
                python_dir = install_path / "lib" / "paraview" / "site-packages"
                if not python_dir.exists():
                    warnings.append("Python modules directory not found")
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result