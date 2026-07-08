"""
Diagnostics Engine for running and reporting on dependency health.

The diagnostics engine provides:
- Health checks for all dependencies
- Diagnostic reports
- Issue detection and recommendations
- Performance metrics
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base import ToolAdapter, DependencyInfo, DependencyStatus, DiagnosticResult, DiagnosticSeverity
from .registry import get_registry


class DiagnosticCategory(str, Enum):
    """Categories of diagnostics."""
    HEALTH = "health"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    COMPATIBILITY = "compatibility"
    SECURITY = "security"


@dataclass
class DiagnosticReport:
    """Complete diagnostic report for the system."""
    timestamp: datetime
    overall_health: str  # "healthy", "degraded", "unhealthy"
    total_tools: int
    healthy_count: int
    degraded_count: int
    unhealthy_count: int
    tool_reports: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    system_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolDiagnostic:
    """Diagnostic information for a single tool."""
    name: str
    status: DependencyStatus
    health: str
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DiagnosticsEngine:
    """
    Engine for running diagnostics on dependencies.
    
    Provides:
    - Individual tool diagnostics
    - System-wide diagnostic reports
    - Issue detection and recommendations
    - Performance monitoring
    """
    
    def __init__(self):
        self.registry = get_registry()
        self._diagnostic_history: List[DiagnosticReport] = []
        self._max_history = 100  # Keep last 100 reports
    
    def diagnose_tool(self, name: str, deep: bool = False) -> Optional[ToolDiagnostic]:
        """
        Run diagnostics on a specific tool.
        
        Args:
            name: Name of the tool.
            deep: Whether to run deep diagnostics.
            
        Returns:
            ToolDiagnostic, or None if tool not found.
        """
        adapter = self.registry.get(name)
        if adapter is None:
            return None
        
        diagnostic = ToolDiagnostic(
            name=name,
            status=DependencyStatus.UNKNOWN,
            health="unknown"
        )
        
        try:
            # Get basic info
            info = adapter.get_info()
            diagnostic.status = info.status
            
            # Run verification
            verify_result = adapter.verify()
            diagnostic.health = "healthy" if verify_result.healthy else "unhealthy"
            
            # Collect issues
            if not verify_result.healthy:
                diagnostic.issues.extend(verify_result.errors)
                diagnostic.warnings.extend(verify_result.warnings)
            
            # Check version compatibility
            if info.required_version and info.installed_version:
                if not self._check_version_compatibility(info.required_version, info.installed_version):
                    diagnostic.issues.append(
                        f"Version mismatch: required {info.required_version}, "
                        f"installed {info.installed_version}"
                    )
                    diagnostic.health = "degraded"
            
            # Deep diagnostics
            if deep:
                diag_result = adapter.diagnostics()
                diagnostic.metrics = diag_result.metrics
                diagnostic.recommendations = diag_result.recommendations
                
                if diag_result.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.CRITICAL):
                    diagnostic.health = "unhealthy"
                elif diag_result.severity == DiagnosticSeverity.WARNING:
                    if diagnostic.health == "healthy":
                        diagnostic.health = "degraded"
            
            # Generate recommendations
            diagnostic.recommendations.extend(self._generate_recommendations(diagnostic))
            
        except Exception as e:
            diagnostic.health = "unhealthy"
            diagnostic.issues.append(f"Diagnostic failed: {str(e)}")
        
        return diagnostic
    
    def diagnose_all(self, deep: bool = False) -> DiagnosticReport:
        """
        Run diagnostics on all registered tools.
        
        Args:
            deep: Whether to run deep diagnostics.
            
        Returns:
            DiagnosticReport for the entire system.
        """
        report = DiagnosticReport(
            timestamp=datetime.utcnow(),
            overall_health="healthy",
            total_tools=len(self.registry),
            healthy_count=0,
            degraded_count=0,
            unhealthy_count=0
        )
        
        for adapter in self.registry.get_all():
            diagnostic = self.diagnose_tool(adapter.name, deep)
            
            if diagnostic:
                report.tool_reports[diagnostic.name] = {
                    "status": diagnostic.status.value,
                    "health": diagnostic.health,
                    "issues": diagnostic.issues,
                    "warnings": diagnostic.warnings,
                    "metrics": diagnostic.metrics,
                    "recommendations": diagnostic.recommendations
                }
                
                # Update counts
                if diagnostic.health == "healthy":
                    report.healthy_count += 1
                elif diagnostic.health == "degraded":
                    report.degraded_count += 1
                    report.recommendations.extend(diagnostic.recommendations)
                else:
                    report.unhealthy_count += 1
                    report.recommendations.extend(diagnostic.recommendations)
        
        # Determine overall health
        if report.unhealthy_count > 0:
            report.overall_health = "unhealthy"
        elif report.degraded_count > 0:
            report.overall_health = "degraded"
        else:
            report.overall_health = "healthy"
        
        # Add system info
        report.system_info = self._get_system_info()
        
        # Store in history
        self._diagnostic_history.append(report)
        if len(self._diagnostic_history) > self._max_history:
            self._diagnostic_history.pop(0)
        
        return report
    
    def diagnose_category(self, category: str, deep: bool = False) -> List[ToolDiagnostic]:
        """
        Run diagnostics on all tools in a category.
        
        Args:
            category: Category name.
            deep: Whether to run deep diagnostics.
            
        Returns:
            List of ToolDiagnostic results.
        """
        from .base import DependencyCategory
        
        try:
            cat = DependencyCategory(category)
        except ValueError:
            return []
        
        tools = self.registry.get_by_category(cat)
        return [
            self.diagnose_tool(tool.name, deep)
            for tool in tools
        ]
    
    def check_dependencies(self, name: str) -> List[Dict[str, Any]]:
        """
        Check if a tool's dependencies are satisfied.
        
        Args:
            name: Name of the tool.
            
        Returns:
            List of dependency status dictionaries.
        """
        adapter = self.registry.get(name)
        if adapter is None:
            return []
        
        results = []
        for dep in adapter.dependencies:
            dep_adapter = self.registry.get(dep.name)
            
            if dep_adapter is None:
                results.append({
                    "name": dep.name,
                    "required": True,
                    "satisfied": False,
                    "reason": "Tool not registered"
                })
            else:
                info = dep_adapter.get_info()
                satisfied = info.status in (DependencyStatus.INSTALLED, DependencyStatus.CONFIGURED)
                
                results.append({
                    "name": dep.name,
                    "required": dep.required,
                    "satisfied": satisfied,
                    "status": info.status.value,
                    "installed_version": info.installed_version
                })
        
        return results
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get a summary of system health.
        
        Returns:
            Dictionary with health summary.
        """
        report = self.diagnose_all(deep=False)
        
        return {
            "overall_health": report.overall_health,
            "total_tools": report.total_tools,
            "healthy": report.healthy_count,
            "degraded": report.degraded_count,
            "unhealthy": report.unhealthy_count,
            "timestamp": report.timestamp.isoformat()
        }
    
    def get_diagnostic_history(self, limit: int = 10) -> List[DiagnosticReport]:
        """
        Get diagnostic history.
        
        Args:
            limit: Maximum number of reports to return.
            
        Returns:
            List of DiagnosticReport objects.
        """
        return self._diagnostic_history[-limit:]
    
    def _check_version_compatibility(self, required: str, installed: str) -> bool:
        """Check if installed version meets requirements."""
        # Simple version comparison - could be enhanced with packaging.version
        try:
            req_parts = [int(x) for x in required.split(".")]
            inst_parts = [int(x) for x in installed.split(".")]
            
            # Pad shorter version with zeros
            while len(req_parts) < len(inst_parts):
                req_parts.append(0)
            while len(inst_parts) < len(req_parts):
                inst_parts.append(0)
            
            # Compare parts
            for req, inst in zip(req_parts, inst_parts):
                if inst < req:
                    return False
                elif inst > req:
                    return True
            
            return True
        except (ValueError, AttributeError):
            return True  # Can't parse versions, assume compatible
    
    def _generate_recommendations(self, diagnostic: ToolDiagnostic) -> List[str]:
        """Generate recommendations based on diagnostic results."""
        recommendations = []
        
        if diagnostic.health == "unhealthy":
            if diagnostic.status == DependencyStatus.MISSING:
                recommendations.append(f"Install {diagnostic.name} to resolve issues")
            elif diagnostic.status == DependencyStatus.BROKEN:
                recommendations.append(f"Reinstall {diagnostic.name} to fix broken installation")
            elif diagnostic.status == DependencyStatus.WRONG_VERSION:
                recommendations.append(f"Update {diagnostic.name} to required version")
        
        if "path" in diagnostic.issues:
            recommendations.append(f"Verify {diagnostic.name} installation path is correct")
        
        if "environment" in diagnostic.issues:
            recommendations.append(f"Check {diagnostic.name} environment variables")
        
        return recommendations
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for the report."""
        import platform
        import sys
        
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "platform_release": platform.release(),
            "python_version": sys.version,
            "architecture": platform.machine(),
            "processor": platform.processor()
        }


# Global diagnostics engine instance
_diagnostics_engine: Optional[DiagnosticsEngine] = None


def get_diagnostics_engine() -> DiagnosticsEngine:
    """Get the global diagnostics engine instance."""
    global _diagnostics_engine
    if _diagnostics_engine is None:
        _diagnostics_engine = DiagnosticsEngine()
    return _diagnostics_engine