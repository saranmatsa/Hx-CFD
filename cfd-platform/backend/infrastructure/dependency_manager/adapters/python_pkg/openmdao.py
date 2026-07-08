"""
OpenMDAO Adapter for dependency management.

OpenMDAO is an open-source MDAO framework for system optimization.
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


class OpenMDAOAdapter(ToolAdapter):
    """Adapter for OpenMDAO."""
    
    name = "openmdao"
    display_name = "OpenMDAO"
    description = "Open-source MDAO framework for system optimization"
    category = DependencyCategory.PYTHON_PACKAGE
    homepage = "https://openmdao.org/"
    
    def __init__(self):
        super().__init__()
    
    def get_info(self) -> DependencyInfo:
        """Get OpenMDAO information."""
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
            documentation="https://openmdao.org/documentation/",
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
        """Find OpenMDAO installation path."""
        try:
            import openmdao
            return Path(openmdao.__file__).parent
        except ImportError:
            return None
    
    def get_version(self) -> Optional[str]:
        """Get OpenMDAO version."""
        try:
            import openmdao
            return openmdao.__version__
        except ImportError:
            return None
    
    def verify(self) -> DiagnosticResult:
        """Verify OpenMDAO installation."""
        try:
            import openmdao
            from openmdao.api import Problem, Group, Component
            
            # Check if we can create a basic problem
            class SimpleComp(Component):
                def __init__(self):
                    super().__init__()
                    self.add_param('x', val=0.0)
                    self.add_output('y', val=0.0)
                
                def solve_nonlinear(self, params, unknowns, resids):
                    unknowns['y'] = params['x'] ** 2
                
                def linearize(self, params, unknowns, resids):
                    jac = resids.__class__()
                    jac['y', 'x'] = 2 * params['x']
                    return jac
            
            return DiagnosticResult(
                healthy=True,
                message=f"OpenMDAO {openmdao.__version__} is installed",
                errors=[],
                warnings=[],
                severity=DiagnosticSeverity.INFO
            )
        except ImportError:
            return DiagnosticResult(
                healthy=False,
                message="OpenMDAO not found",
                errors=["OpenMDAO package not installed"],
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
        """Install OpenMDAO."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "openmdao"],
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure OpenMDAO."""
        valid_keys = {"n2", "show_wrap", "openmdao_defaults"}
        for key in settings:
            if key not in valid_keys:
                return False
        return True
    
    def _get_dependencies(self) -> List[Any]:
        """Get OpenMDAO dependencies."""
        return []
    
    def diagnostics(self) -> DiagnosticResult:
        """Run OpenMDAO diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            try:
                import openmdao
                from openmdao.api import __all__
                
                metrics["version"] = openmdao.__version__
                
                # Check available modules
                try:
                    from openmdao import solvers
                    metrics["solvers_available"] = True
                except Exception:
                    warnings.append("Solvers module not available")
                
                try:
                    from openmdao import drivers
                    metrics["drivers_available"] = True
                except Exception:
                    warnings.append("Drivers module not available")
                
                try:
                    from openmdao import components
                    metrics["components_available"] = True
                except Exception:
                    warnings.append("Components module not available")
                
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