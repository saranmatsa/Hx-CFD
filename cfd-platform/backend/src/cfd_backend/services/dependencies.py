"""
Dependency detection service for CFD Backend.

Provides detection and validation of external CFD tools:
- OpenFOAM
- Gmsh
- ParaView
"""

import asyncio
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from cfd_backend.core.config import Settings, get_settings
from cfd_backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolInfo:
    """Information about a detected external tool."""
    name: str
    version: Optional[str] = None
    path: Optional[Path] = None
    available: bool = False
    details: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class DependencyReport:
    """Complete dependency detection report."""
    tools: Dict[str, ToolInfo] = field(default_factory=dict)
    all_available: bool = False
    missing_tools: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.all_available = all(tool.available for tool in self.tools.values())
        self.missing_tools = [name for name, tool in self.tools.items() if not tool.available]


class DependencyDetectionService:
    """Service for detecting and validating external CFD tool dependencies."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._cache: Optional[DependencyReport] = None
        self._cache_valid = False
    
    async def detect_openfoam(self) -> ToolInfo:
        """Detect OpenFOAM installation and version."""
        tool_info = ToolInfo(name="OpenFOAM")
        
        # Try configured path first
        if self.settings.openfoam_path:
            bashrc = self.settings.openfoam_path / "etc" / "bashrc"
            if bashrc.exists():
                version = await self._run_openfoam_version(bashrc)
                if version:
                    tool_info.version = version
                    tool_info.path = self.settings.openfoam_path
                    tool_info.available = True
                    tool_info.details["bashrc"] = str(bashrc)
                    return tool_info
        
        # Try common installation paths
        common_paths = [
            Path("/opt/openfoam"),
            Path("/usr/lib/openfoam"),
            Path("C:/Program Files/OpenFOAM"),
            Path("C:/OpenFOAM"),
            Path.home() / "OpenFOAM",
        ]
        
        for path in common_paths:
            bashrc = path / "etc" / "bashrc"
            if bashrc.exists():
                version = await self._run_openfoam_version(bashrc)
                if version:
                    tool_info.version = version
                    tool_info.path = path
                    tool_info.available = True
                    tool_info.details["bashrc"] = str(bashrc)
                    return tool_info
        
        # Try foamVersion in PATH
        version = await self._run_openfoam_version(None)
        if version:
            tool_info.version = version
            tool_info.available = True
            tool_info.details["detection"] = "PATH"
            return tool_info
        
        tool_info.error = "OpenFOAM not found in configured path, common locations, or PATH"
        return tool_info
    
    async def _run_openfoam_version(self, bashrc: Optional[Path]) -> Optional[str]:
        """Run foamVersion command to get OpenFOAM version."""
        try:
            if bashrc:
                cmd = ["bash", "-c", f"source {bashrc} && foamVersion"]
            else:
                cmd = ["bash", "-c", "foamVersion"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
        except Exception as e:
            logger.debug("OpenFOAM version detection failed", error=str(e))
        return None
    
    async def detect_gmsh(self) -> ToolInfo:
        """Detect Gmsh installation and version."""
        tool_info = ToolInfo(name="Gmsh")
        
        # Try configured path first
        gmsh_cmd = str(self.settings.gmsh_path) if self.settings.gmsh_path else "gmsh"
        
        # If configured path doesn't exist, try common locations
        if self.settings.gmsh_path and not Path(self.settings.gmsh_path).exists():
            common_paths = [
                Path("/usr/bin/gmsh"),
                Path("/usr/local/bin/gmsh"),
                Path("C:/Program Files/Gmsh/gmsh.exe"),
                Path("C:/Gmsh/gmsh.exe"),
            ]
            for path in common_paths:
                if path.exists():
                    gmsh_cmd = str(path)
                    break
        
        try:
            process = await asyncio.create_subprocess_exec(
                gmsh_cmd, "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                version = stdout.decode().strip()
                tool_info.version = version
                tool_info.path = Path(gmsh_cmd)
                tool_info.available = True
                tool_info.details["command"] = gmsh_cmd
                return tool_info
        except Exception as e:
            logger.debug("Gmsh version detection failed", error=str(e))
        
        tool_info.error = f"Gmsh not found at {gmsh_cmd} or in PATH"
        return tool_info
    
    async def detect_paraview(self) -> ToolInfo:
        """Detect ParaView installation and version."""
        tool_info = ToolInfo(name="ParaView")
        
        # Try configured path first
        pv_cmd = str(self.settings.paraview_path) if self.settings.paraview_path else "pvpython"
        
        # If configured path doesn't exist, try common locations
        if self.settings.paraview_path and not Path(self.settings.paraview_path).exists():
            common_paths = [
                Path("/usr/bin/pvpython"),
                Path("/usr/local/bin/pvpython"),
                Path("C:/Program Files/ParaView 5.12.0/bin/pvpython.exe"),
                Path("C:/Program Files/ParaView/bin/pvpython.exe"),
            ]
            for path in common_paths:
                if path.exists():
                    pv_cmd = str(path)
                    break
        
        try:
            process = await asyncio.create_subprocess_exec(
                pv_cmd, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                version = stdout.decode().strip()
                tool_info.version = version
                tool_info.path = Path(pv_cmd)
                tool_info.available = True
                tool_info.details["command"] = pv_cmd
                return tool_info
        except Exception as e:
            logger.debug("ParaView version detection failed", error=str(e))
        
        tool_info.error = f"ParaView (pvpython) not found at {pv_cmd} or in PATH"
        return tool_info
    
    async def detect_python_packages(self) -> Dict[str, ToolInfo]:
        """Detect required Python packages."""
        packages = {
            "numpy": "numpy",
            "scipy": "scipy",
            "pandas": "pandas",
            "matplotlib": "matplotlib",
            "vtk": "vtk",
            "meshio": "meshio",
            "pyvista": "pyvista",
        }
        
        results = {}
        for name, import_name in packages.items():
            tool_info = ToolInfo(name=name)
            try:
                module = __import__(import_name)
                version = getattr(module, "__version__", "unknown")
                tool_info.version = version
                tool_info.available = True
                tool_info.details["import_name"] = import_name
            except ImportError:
                tool_info.error = f"Python package '{import_name}' not installed"
            results[name] = tool_info
        
        return results
    
    async def detect_all(self, force_refresh: bool = False) -> DependencyReport:
        """Detect all external dependencies."""
        if self._cache and self._cache_valid and not force_refresh:
            return self._cache
        
        report = DependencyReport()
        
        # Detect CFD tools
        report.tools["openfoam"] = await self.detect_openfoam()
        report.tools["gmsh"] = await self.detect_gmsh()
        report.tools["paraview"] = await self.detect_paraview()
        
        # Detect Python packages
        python_packages = await self.detect_python_packages()
        report.tools.update(python_packages)
        
        # Post-process
        report.__post_init__()
        
        # Add warnings
        if not report.tools["openfoam"].available:
            report.warnings.append("OpenFOAM not detected - CFD simulations will not be available")
        if not report.tools["gmsh"].available:
            report.warnings.append("Gmsh not detected - mesh generation will not be available")
        if not report.tools["paraview"].available:
            report.warnings.append("ParaView not detected - post-processing will be limited")
        
        missing_python = [name for name, tool in python_packages.items() if not tool.available]
        if missing_python:
            report.warnings.append(f"Missing Python packages: {', '.join(missing_python)}")
        
        self._cache = report
        self._cache_valid = True
        
        logger.info(
            "Dependency detection completed",
            all_available=report.all_available,
            missing=report.missing_tools,
        )
        
        return report
    
    def invalidate_cache(self) -> None:
        """Invalidate the detection cache."""
        self._cache = None
        self._cache_valid = False
    
    async def validate_openfoam_case(self, case_path: Path) -> Dict[str, any]:
        """Validate an OpenFOAM case directory structure."""
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "files_found": [],
            "files_missing": [],
        }
        
        required_files = [
            "system/controlDict",
            "system/fvSchemes",
            "system/fvSolution",
            "constant/transportProperties",
        ]
        
        optional_files = [
            "constant/turbulenceProperties",
            "0/U",
            "0/p",
            "0/k",
            "0/epsilon",
            "0/omega",
            "0/nut",
        ]
        
        for req_file in required_files:
            file_path = case_path / req_file
            if file_path.exists():
                result["files_found"].append(req_file)
            else:
                result["files_missing"].append(req_file)
                result["errors"].append(f"Required file missing: {req_file}")
        
        for opt_file in optional_files:
            file_path = case_path / opt_file
            if file_path.exists():
                result["files_found"].append(opt_file)
            else:
                result["warnings"].append(f"Optional file missing: {opt_file}")
        
        result["valid"] = len(result["errors"]) == 0
        return result
    
    async def get_openfoam_solvers(self) -> List[str]:
        """Get list of available OpenFOAM solvers."""
        solvers = []
        
        if self.settings.openfoam_path:
            bashrc = self.settings.openfoam_path / "etc" / "bashrc"
            if bashrc.exists():
                try:
                    process = await asyncio.create_subprocess_exec(
                        "bash", "-c", f"source {bashrc} && foamSolverList",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await process.communicate()
                    if process.returncode == 0:
                        solvers = stdout.decode().strip().split()
                except Exception as e:
                    logger.debug("Failed to get OpenFOAM solvers", error=str(e))
        
        # Fallback to common solvers
        if not solvers:
            solvers = [
                "simpleFoam", "pimpleFoam", "pisoFoam",
                "rhoSimpleFoam", "rhoPimpleFoam",
                "buoyantSimpleFoam", "buoyantPimpleFoam",
                "chtMultiRegionFoam", "reactingFoam",
            ]
        
        return solvers
    
    async def get_gmsh_version_info(self) -> Dict[str, str]:
        """Get detailed Gmsh version information."""
        tool_info = await self.detect_gmsh()
        if not tool_info.available:
            return {"error": tool_info.error or "Gmsh not available"}
        
        try:
            process = await asyncio.create_subprocess_exec(
                str(tool_info.path), "-info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            if process.returncode == 0:
                return {"version": tool_info.version, "info": stdout.decode().strip()}
        except Exception as e:
            logger.debug("Failed to get Gmsh info", error=str(e))
        
        return {"version": tool_info.version, "info": "Version info unavailable"}
    
    async def get_paraview_version_info(self) -> Dict[str, str]:
        """Get detailed ParaView version information."""
        tool_info = await self.detect_paraview()
        if not tool_info.available:
            return {"error": tool_info.error or "ParaView not available"}
        
        try:
            process = await asyncio.create_subprocess_exec(
                str(tool_info.path), "--version-full",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            if process.returncode == 0:
                return {"version": tool_info.version, "info": stdout.decode().strip()}
        except Exception as e:
            logger.debug("Failed to get ParaView info", error=str(e))
        
        return {"version": tool_info.version, "info": "Version info unavailable"}