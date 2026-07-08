"""
FreeCAD Adapter for dependency management.

FreeCAD is a free and open-source general-purpose parametric 3D CAD modeler.
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


class FreeCADAdapter(ToolAdapter):
    """Adapter for FreeCAD."""
    
    name = "freecad"
    display_name = "FreeCAD"
    description = "General-purpose parametric 3D CAD modeler"
    category = DependencyCategory.ENGINEERING
    homepage = "https://www.freecad.org/"
    
    def __init__(self):
        super().__init__()
        self._platform = PlatformDetector()
        self._install_paths = self._get_default_paths()
    
    def _get_default_paths(self) -> Dict[str, List[Path]]:
        """Get default installation paths for each platform."""
        return {
            "windows": [
                Path("C:/Program Files/FreeCAD/bin"),
                Path("C:/Program Files (x86)/FreeCAD/bin"),
            ],
            "macos": [
                Path("/Applications/FreeCAD.app/Contents/MacOS"),
                Path("~/Applications/FreeCAD.app/Contents/MacOS"),
            ],
            "linux": [
                Path("/usr/bin/freecad"),
                Path("/usr/local/bin/freecad"),
                Path("~/.local/bin/freecad"),
            ]
        }
    
    def get_info(self) -> DependencyInfo:
        """Get FreeCAD information."""
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
            documentation="https://wiki.freecad.org/",
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
        """Find FreeCAD installation path."""
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
                    ["where", "FreeCAD"],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["which", "freecad"],
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
        """Get FreeCAD version."""
        try:
            freecad_cmd = self._find_executable()
            if freecad_cmd is None:
                return None
            
            result = subprocess.run(
                [str(freecad_cmd), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # FreeCAD outputs version info to stderr typically
                output = result.stderr or result.stdout
                return self._parse_version(output)
            
            return None
        except Exception:
            return None
    
    def _find_executable(self) -> Optional[Path]:
        """Find FreeCAD executable."""
        install_path = self._find_installation_path()
        if install_path:
            # Look for FreeCAD executable in bin directory
            if install_path.name == "bin":
                for exe in ["FreeCAD", "FreeCAD.exe"]:
                    exe_path = install_path / exe
                    if exe_path.exists():
                        return exe_path
        
        # Try using shutil.which
        exe = shutil.which("FreeCAD") or shutil.which("freecad")
        if exe:
            return Path(exe)
        
        return None
    
    def _parse_version(self, output: str) -> Optional[str]:
        """Parse version from output."""
        import re
        
        # Look for version pattern
        patterns = [
            r"FreeCAD\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
            r"Version\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
            r"([0-9]+\.[0-9]+(?:\.[0-9]+)?)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def verify(self) -> DiagnosticResult:
        """Verify FreeCAD installation."""
        try:
            version = self.get_version()
            if version is None:
                return DiagnosticResult(
                    healthy=False,
                    message="FreeCAD not found",
                    errors=["FreeCAD executable not found"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check if we can run FreeCAD
            freecad_cmd = self._find_executable()
            if freecad_cmd is None:
                return DiagnosticResult(
                    healthy=False,
                    message="FreeCAD executable not accessible",
                    errors=["Cannot find FreeCAD executable"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            return DiagnosticResult(
                healthy=True,
                message=f"FreeCAD {version} is installed",
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
        """Install FreeCAD."""
        platform = self._platform.get_platform()
        
        if platform == Platform.WINDOWS:
            return self._install_windows(**kwargs)
        elif platform == Platform.MACOS:
            return self._install_macos(**kwargs)
        elif platform == Platform.LINUX:
            return self._install_linux(**kwargs)
        
        return False
    
    def _install_windows(self, **kwargs) -> bool:
        """Install FreeCAD on Windows."""
        # On Windows, typically use installer or winget
        try:
            # Try winget first
            result = subprocess.run(
                ["winget", "install", "--id", "FreeCAD.FreeCAD", "-e"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_macos(self, **kwargs) -> bool:
        """Install FreeCAD on macOS."""
        try:
            # Try Homebrew
            result = subprocess.run(
                ["brew", "install", "--cask", "freecad"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_linux(self, **kwargs) -> bool:
        """Install FreeCAD on Linux."""
        try:
            # Try apt-get
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "freecad"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            
            # Try snap
            result = subprocess.run(
                ["sudo", "snap", "install", "freecad"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure FreeCAD."""
        # FreeCAD configuration is typically done via preferences
        # For now, just validate settings
        valid_keys = {"workbench", "theme", "units", "precision"}
        for key in settings:
            if key not in valid_keys:
                return False
        return True
    
    def _get_dependencies(self) -> List[Any]:
        """Get FreeCAD dependencies."""
        return []  # FreeCAD is self-contained
    
    def diagnostics(self) -> DiagnosticResult:
        """Run FreeCAD diagnostics."""
        result = self.verify()
        
        if result.healthy:
            # Additional checks
            warnings = []
            install_path = self._find_installation_path()
            
            if install_path and not (install_path / "Mod").exists():
                warnings.append("Mod directory not found - may be incomplete installation")
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics={"install_path": str(install_path) if install_path else None}
            )
        
        return result