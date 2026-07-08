"""
Gmsh Adapter for dependency management.

Gmsh is a free 3D finite element mesh generator.
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


class GmshAdapter(ToolAdapter):
    """Adapter for Gmsh."""
    
    name = "gmsh"
    display_name = "Gmsh"
    description = "3D finite element mesh generator"
    category = DependencyCategory.ENGINEERING
    homepage = "https://gmsh.info/"
    
    def __init__(self):
        super().__init__()
        self._platform = PlatformDetector()
        self._install_paths = self._get_default_paths()
    
    def _get_default_paths(self) -> Dict[str, List[Path]]:
        """Get default installation paths for each platform."""
        return {
            "windows": [
                Path("C:/Program Files/gmsh/bin"),
                Path("C:/Program Files (x86)/gmsh/bin"),
            ],
            "macos": [
                Path("/Applications/gmsh.app"),
                Path("/usr/local/bin/gmsh"),
                Path("/opt/homebrew/bin/gmsh"),
            ],
            "linux": [
                Path("/usr/bin/gmsh"),
                Path("/usr/local/bin/gmsh"),
                Path("~/.local/bin/gmsh"),
            ]
        }
    
    def get_info(self) -> DependencyInfo:
        """Get Gmsh information."""
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
            documentation="https://gmsh.info/doc/",
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
        """Find Gmsh installation path."""
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
                    ["where", "gmsh"],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["which", "gmsh"],
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
        """Get Gmsh version."""
        try:
            gmsh_cmd = self._find_executable()
            if gmsh_cmd is None:
                return None
            
            result = subprocess.run(
                [str(gmsh_cmd), "--version"],
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
        """Find Gmsh executable."""
        install_path = self._find_installation_path()
        if install_path:
            # Look for gmsh executable in bin directory
            if install_path.name == "bin":
                for exe in ["gmsh", "gmsh.exe"]:
                    exe_path = install_path / exe
                    if exe_path.exists():
                        return exe_path
            # Check if install_path itself is the executable
            for exe in ["gmsh", "gmsh.exe"]:
                exe_path = install_path / exe
                if exe_path.exists():
                    return exe_path
        
        # Try using shutil.which
        exe = shutil.which("gmsh")
        if exe:
            return Path(exe)
        
        return None
    
    def _parse_version(self, output: str) -> Optional[str]:
        """Parse version from output."""
        import re
        
        # Look for version pattern
        patterns = [
            r"gmsh\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
            r"([0-9]+\.[0-9]+(?:\.[0-9]+)?)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def verify(self) -> DiagnosticResult:
        """Verify Gmsh installation."""
        try:
            version = self.get_version()
            if version is None:
                return DiagnosticResult(
                    healthy=False,
                    message="Gmsh not found",
                    errors=["Gmsh executable not found"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check if we can run gmsh
            gmsh_cmd = self._find_executable()
            if gmsh_cmd is None:
                return DiagnosticResult(
                    healthy=False,
                    message="Gmsh executable not accessible",
                    errors=["Cannot find Gmsh executable"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            return DiagnosticResult(
                healthy=True,
                message=f"Gmsh {version} is installed",
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
        """Install Gmsh."""
        platform = self._platform.get_platform()
        
        if platform == Platform.WINDOWS:
            return self._install_windows(**kwargs)
        elif platform == Platform.MACOS:
            return self._install_macos(**kwargs)
        elif platform == Platform.LINUX:
            return self._install_linux(**kwargs)
        
        return False
    
    def _install_windows(self, **kwargs) -> bool:
        """Install Gmsh on Windows."""
        try:
            # Try winget first
            result = subprocess.run(
                ["winget", "install", "--id", "Gmsh.Gmsh", "-e"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try chocolatey
            result = subprocess.run(
                ["choco", "install", "gmsh", "-y"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_macos(self, **kwargs) -> bool:
        """Install Gmsh on macOS."""
        try:
            # Try Homebrew
            result = subprocess.run(
                ["brew", "install", "--cask", "gmsh"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_linux(self, **kwargs) -> bool:
        """Install Gmsh on Linux."""
        try:
            # Try apt-get
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "gmsh"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try snap
            result = subprocess.run(
                ["sudo", "snap", "install", "gmsh"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure Gmsh."""
        valid_keys = {"element_size", "algorithm", "optimize", "mesh_format"}
        for key in settings:
            if key not in valid_keys:
                return False
        return True
    
    def _get_dependencies(self) -> List[Any]:
        """Get Gmsh dependencies."""
        return []  # Gmsh is self-contained
    
    def diagnostics(self) -> DiagnosticResult:
        """Run Gmsh diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            install_path = self._find_installation_path()
            if install_path:
                metrics["install_path"] = str(install_path)
                
                # Check for shared libraries
                if install_path.name == "bin":
                    lib_path = install_path.parent / "lib"
                    if not lib_path.exists():
                        warnings.append("Library directory not found")
                
                # Check for documentation
                doc_path = install_path.parent / "share" / "gmsh" / "doc"
                if not doc_path.exists():
                    warnings.append("Documentation not found")
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result