"""
NeverGrad Adapter for dependency management.

NeverGrad is a Python library for performing gradient-free optimization.
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


class NeverGradAdapter(ToolAdapter):
    """Adapter for NeverGrad."""
    
    name = "nevergrad"
    display_name = "NeverGrad"
    description = "Gradient-free optimization library"
    category = DependencyCategory.PYTHON_PACKAGE
    homepage = "https://facebookresearch.github.io/nevergrad/"
    
    def __init__(self):
        super().__init__()
    
    def get_info(self) -> DependencyInfo:
        """Get NeverGrad information."""
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
            documentation="https://nevergrad.readthedocs.io/",
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
        """Find NeverGrad installation path."""
        try:
            import nevergrad
            return Path(nevergrad.__file__).parent
        except ImportError:
            return None
    
    def get_version(self) -> Optional[str]:
        """Get NeverGrad version."""
        try:
            import nevergrad
            return nevergrad.__version__
        except ImportError:
            return None
    
    def verify(self) -> DiagnosticResult:
        """Verify NeverGrad installation."""
        try:
            import nevergrad
            import nevergrad.optimization as optimization
            
            # Check if we can list available optimizers
            optimizer_count = len(optimization.registry)
            
            return DiagnosticResult(
                healthy=True,
                message=f"NeverGrad {nevergrad.__version__} is installed with {optimizer_count} optimizers",
                errors=[],
                warnings=[],
                severity=DiagnosticSeverity.INFO
            )
        except ImportError:
            return DiagnosticResult(
                healthy=False,
                message="NeverGrad not found",
                errors=["NeverGrad package not installed"],
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
        """Install NeverGrad."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "nevergrad"],
                capture_output=True,
                text=True,
                timeout=180
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure NeverGrad."""
        valid_keys = {"budget", "num_workers", "parallelization"}
        for key in settings:
            if key not in valid_keys:
                return False
        return True
    
    def _get_dependencies(self) -> List[Any]:
        """Get NeverGrad dependencies."""
        return []
    
    def diagnostics(self) -> DiagnosticResult:
        """Run NeverGrad diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            try:
                import nevergrad
                import nevergrad.optimization as optimization
                import nevergrad.benchmark as benchmark
                import nevergrad.common as common
                
                # Count available optimizers
                metrics["optimizer_count"] = len(optimization.registry)
                metrics["optimizer_categories"] = list(set(
                    optimizer.split("_")[0] for optimizer in optimization.registry.keys()
                ))
                
                # Check if parametrization is available
                try:
                    from nevergrad.parametrization import parametrization
                    metrics["parametrization_available"] = True
                except Exception:
                    warnings.append("Parametrization module not available")
                
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