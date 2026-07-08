"""
MeshIO Adapter for dependency management.

MeshIO is a library for reading and writing various mesh formats.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import subprocess
import sys

from ..core.base import (
    ToolAdapter,
    DependencyInfo,
    DependencyStatus,
    DependencyCategory,
    DiagnosticResult,
    DiagnosticSeverity
)


class MeshIOAdapter(ToolAdapter):
    """Adapter for meshio."""
    
    name = "meshio"
    display_name = "meshio"
    description = "Library for reading and writing various mesh formats"
    category = DependencyCategory.PYTHON_PACKAGE
    homepage = "https://github.com/nschloe/meshio"
    
    def __init__(self):
        super().__init__()
    
    def get_info(self) -> DependencyInfo:
        """Get meshio information."""
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
            documentation="https://meshio.readthedocs.io/",
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
        """Find meshio installation path."""
        try:
            import meshio
            return Path(meshio.__file__).parent
        except ImportError:
            return None
    
    def get_version(self) -> Optional[str]:
        """Get meshio version."""
        try:
            import meshio
            return meshio.__version__
        except ImportError:
            return None
    
    def verify(self) -> DiagnosticResult:
        """Verify meshio installation."""
        try:
            import meshio
            
            # Check if we can import and use basic functionality
            supported_formats = meshio.extension_to_filetypes
            if supported_formats:
                return DiagnosticResult(
                    healthy=True,
                    message=f"meshio {meshio.__version__} is installed with {len(supported_formats)} formats",
                    errors=[],
                    warnings=[],
                    severity=DiagnosticSeverity.INFO
                )
            
            return DiagnosticResult(
                healthy=True,
                message=f"meshio {meshio.__version__} is installed",
                errors=[],
                warnings=[],
                severity=DiagnosticSeverity.INFO
            )
        except ImportError:
            return DiagnosticResult(
                healthy=False,
                message="meshio not found",
                errors=["meshio package not installed"],
                warnings=[],
                severity=DiagnosticSeverity.ERROR
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
        """Install meshio."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "meshio"],
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure meshio."""
        valid_keys = {"default_extension", "file_format"}
        for key in settings:
            if key not in valid_keys:
                return False
        return True
    
    def _get_dependencies(self) -> List[Any]:
        """Get meshio dependencies."""
        return []
    
    def diagnostics(self) -> DiagnosticResult:
        """Run meshio diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            try:
                import meshio
                supported_formats = meshio.extension_to_filetypes
                metrics["supported_formats"] = list(supported_formats.keys())
                metrics["format_count"] = len(supported_formats)
            except Exception as e:
                warnings.append(f"Could not get meshio formats: {e}")
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result