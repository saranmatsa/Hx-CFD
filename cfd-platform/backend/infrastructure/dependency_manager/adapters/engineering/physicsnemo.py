"""
PhysicsNeMo Adapter for dependency management.

PhysicsNeMo is a physics-based neural modeling framework for CFD.
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


class PhysicsNeMoAdapter(ToolAdapter):
    """Adapter for PhysicsNeMo."""
    
    name = "physicsnemo"
    display_name = "PhysicsNeMo"
    description = "Physics-based neural modeling framework for CFD"
    category = DependencyCategory.ENGINEERING
    homepage = "https://github.com/physicsnemo/physicsnemo"
    
    def __init__(self):
        super().__init__()
        self._platform = PlatformDetector()
        self._package_name = "physicsnemo"
    
    def get_info(self) -> DependencyInfo:
        """Get PhysicsNeMo information."""
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
            documentation="https://physicsnemo.readthedocs.io/",
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
        """Find PhysicsNeMo installation path."""
        try:
            # Try to find physicsnemo package location
            result = subprocess.run(
                ["python", "-c", "import physicsnemo; print(physicsnemo.__file__)"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                path = Path(result.stdout.strip())
                if path.exists():
                    return path.parent
        except Exception:
            pass
        
        return None
    
    def get_version(self) -> Optional[str]:
        """Get PhysicsNeMo version."""
        try:
            result = subprocess.run(
                ["python", "-c", "import physicsnemo; print(physicsnemo.__version__)"],
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
        """Verify PhysicsNeMo installation."""
        try:
            version = self.get_version()
            if version is None:
                return DiagnosticResult(
                    healthy=False,
                    message="PhysicsNeMo not found",
                    errors=["PhysicsNeMo package not installed"],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            # Check if we can import physicsnemo
            result = subprocess.run(
                ["python", "-c", "import physicsnemo; print('OK')"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return DiagnosticResult(
                    healthy=False,
                    message="PhysicsNeMo import failed",
                    errors=[result.stderr],
                    warnings=[],
                    severity=DiagnosticSeverity.ERROR
                )
            
            return DiagnosticResult(
                healthy=True,
                message=f"PhysicsNeMo {version} is installed",
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
        """Install PhysicsNeMo."""
        try:
            # Install from PyPI
            result = subprocess.run(
                ["python", "-m", "pip", "install", self._package_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def configure(self, **settings) -> bool:
        """Configure PhysicsNeMo."""
        valid_keys = {"device", "precision", "num_workers", "cache_dir"}
        for key in settings:
            if key not in valid_keys:
                return False
        return True
    
    def _get_dependencies(self) -> List[Any]:
        """Get PhysicsNeMo dependencies."""
        return []  # PhysicsNeMo manages its own dependencies
    
    def diagnostics(self) -> DiagnosticResult:
        """Run PhysicsNeMo diagnostics."""
        result = self.verify()
        
        if result.healthy:
            warnings = []
            metrics = {}
            
            # Check GPU availability
            try:
                gpu_result = subprocess.run(
                    ["python", "-c", "import torch; print(torch.cuda.is_available())"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if gpu_result.returncode == 0:
                    metrics["cuda_available"] = gpu_result.stdout.strip() == "True"
                    if gpu_result.stdout.strip() != "True":
                        warnings.append("CUDA not available - GPU acceleration disabled")
            except Exception:
                warnings.append("Could not check CUDA availability")
            
            # Check installation path
            install_path = self._find_installation_path()
            if install_path:
                metrics["install_path"] = str(install_path)
            
            return DiagnosticResult(
                healthy=True,
                message=result.message,
                errors=[],
                warnings=warnings,
                severity=DiagnosticSeverity.INFO,
                metrics=metrics
            )
        
        return result