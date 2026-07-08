"""
PyVista Adapter for dependency management.

PyVista is a streamlined interface for Visualization Toolkit (VTK).
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


class PyVistaAdapter(ToolAdapter):
    """Adapter for PyVista."""
    
    name = "pyvista"
    display_name = "PyVista"
    description = "Streamlined interface for Visualization Toolkit (VTK)"
    category = DependencyCategory.PYTHON_PACKAGE
    homepage = "https://docs.pyvista.org/"
    
    def __init__(self):
        super().__init__()
    
    def get_info(self) -> DependencyInfo:
        """Get PyVista information."""
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
            documentation="https://docs.pyvista.org/",
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
        """Find PyVista installation path."""
        try:
            import pyvista
            return Path(pyvista.__file__).parent
        except ImportError:
            return None
    
    def get_version(self) -> Optional[str]:
        """Get PyVista version."""
        try:
            import pyvista
            return pyvista.__version__
        except ImportError:
            return None
    
    def verify(self) -> DiagnosticResult:
        """Verify PyVista installation."""
        try:
            import pyvista
            
            # Check if we can create a basic plotter
            plotter = pyvista.Plotter(off_screen=True)
            plotter.close()
            
            return DiagnosticResult(
                healthy=True,
                message=f"PyVista {pyvista.__version__} is installed",
                errors=[],
                warnings=[],
                severity=DiagnosticSeverity.INFO
            )
        except ImportError:
            return DiagnosticResult(
                healthy=False,
                message="PyVista not found",
                errors=["PyVista package not installed"],
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
        """Install PyVista."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyvista"],
                capture_output=True,
                text=True,
                timeout=180
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure PyVista."""
        valid_keys = {"theme", "window_size", "notebook"}
        for key in settings:
            if key not in valid_keys:
                return False
        
        try:
            import pyvista
            if "theme" in settings:
                pyvista.set_plot_theme(settings["theme"])
            if "window_size" in settings:
                pyvista.global_theme.window_size = settings["window_size"]
            if "notebook" in settings:
                pyvista.set_notebook_magic(settings["notebook"])
            return True
        except Exception:
            return False
    
    def _get_dependencies(self) -> List[Any]:
        """Get PyVista dependencies."""
        return []
    
    def diagnostics(self) -> DiagnosticResult:
        """Run PyVista diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            try:
                import pyvista
                
                # Check VTK version
                try:
                    import vtk
                    metrics["vtk_version"] = vtk.VTK_VERSION
                except Exception:
                    warnings.append("Could not get VTK version")
                
                # Check available plotters
                metrics["plotting_available"] = True
                
                # Check if GPU rendering is available
                try:
                    plotter = pyvista.Plotter(off_screen=True)
                    metrics["renderers"] = plotter.renderer.GetActors().GetNumberOfItems()
                    plotter.close()
                except Exception:
                    metrics["rendering_limited"] = True
                    warnings.append("GPU rendering may be limited")
                
            except Exception as e:
                warnings.append(f"Could not run diagnostics: {e}")
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result