"""
API Routes for Dependency Management.

This module provides FastAPI routes for managing dependencies.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ..infrastructure.dependency_manager import DependencyManager
from ..infrastructure.dependency_manager.core.base import (
    DependencyInfo,
    DependencyStatus,
    DependencyCategory,
    DiagnosticResult,
    DiagnosticSeverity
)
from ..infrastructure.dependency_manager.core.platform import Platform


# Request/Response Models
class InstallRequest(BaseModel):
    """Request model for installing a dependency."""
    name: str = Field(..., description="Name of the dependency to install")
    version: Optional[str] = Field(None, description="Specific version to install")
    force: bool = Field(False, description="Force reinstall if already installed")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Installation settings")


class ConfigureRequest(BaseModel):
    """Request model for configuring a dependency."""
    name: str = Field(..., description="Name of the dependency to configure")
    settings: Dict[str, Any] = Field(..., description="Configuration settings")


class DependencyInfoResponse(BaseModel):
    """Response model for dependency information."""
    name: str
    display_name: str
    description: str
    category: str
    status: str
    installed_version: Optional[str]
    required_version: Optional[str]
    install_path: Optional[str]
    homepage: str
    documentation: str
    dependencies: List[Any]


class DiagnosticResponse(BaseModel):
    """Response model for diagnostic results."""
    healthy: bool
    message: str
    errors: List[str]
    warnings: List[str]
    severity: str
    metrics: Optional[Dict[str, Any]] = None


class InstallProgressResponse(BaseModel):
    """Response model for installation progress."""
    name: str
    status: str
    progress: float
    message: str


class PlatformInfoResponse(BaseModel):
    """Response model for platform information."""
    platform: str
    architecture: str
    package_manager: str
    home_directory: str


# Create router
router = APIRouter(prefix="/api/v1/dependencies", tags=["dependencies"])

# Initialize dependency manager
_manager: Optional[DependencyManager] = None


def get_manager() -> DependencyManager:
    """Get or create the dependency manager instance."""
    global _manager
    if _manager is None:
        _manager = DependencyManager()
    return _manager


def _dependency_info_to_response(info: DependencyInfo) -> DependencyInfoResponse:
    """Convert DependencyInfo to response model."""
    return DependencyInfoResponse(
        name=info.name,
        display_name=info.display_name,
        description=info.description,
        category=info.category.value if hasattr(info.category, 'value') else str(info.category),
        status=info.status.value if hasattr(info.status, 'value') else str(info.status),
        installed_version=info.installed_version,
        required_version=info.required_version,
        install_path=str(info.install_path) if info.install_path else None,
        homepage=info.homepage,
        documentation=info.documentation,
        dependencies=info.dependencies
    )


def _diagnostic_to_response(diagnostic: DiagnosticResult) -> DiagnosticResponse:
    """Convert DiagnosticResult to response model."""
    return DiagnosticResponse(
        healthy=diagnostic.healthy,
        message=diagnostic.message,
        errors=diagnostic.errors,
        warnings=diagnostic.warnings,
        severity=diagnostic.severity.value if hasattr(diagnostic.severity, 'value') else str(diagnostic.severity),
        metrics=diagnostic.metrics
    )


@router.get("/", response_model=List[DependencyInfoResponse])
async def list_dependencies(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status")
) -> List[DependencyInfoResponse]:
    """
    List all registered dependencies.
    
    Args:
        category: Optional category filter (engineering, platform, python_pkg)
        status: Optional status filter (installed, missing, broken, outdated)
    
    Returns:
        List of dependency information
    """
    manager = get_manager()
    
    # Get all registered tools
    tools = manager.list_tools()
    
    # Get info for each tool
    dependencies = []
    for tool_name in tools:
        info = manager.get_info(tool_name)
        if info:
            # Apply filters
            if category:
                info_category = info.category.value if hasattr(info.category, 'value') else str(info.category)
                if info_category != category:
                    continue
            
            if status:
                info_status = info.status.value if hasattr(info.status, 'value') else str(info.status)
                if info_status != status:
                    continue
            
            dependencies.append(_dependency_info_to_response(info))
    
    return dependencies


@router.get("/platform", response_model=PlatformInfoResponse)
async def get_platform_info() -> PlatformInfoResponse:
    """
    Get information about the current platform.
    
    Returns:
        Platform information
    """
    manager = get_manager()
    platform_info = manager.get_platform_info()
    
    return PlatformInfoResponse(
        platform=platform_info["platform"].value if hasattr(platform_info["platform"], 'value') else str(platform_info["platform"]),
        architecture=platform_info["architecture"],
        package_manager=platform_info["package_manager"].value if hasattr(platform_info["package_manager"], 'value') else str(platform_info["package_manager"]),
        home_directory=platform_info["home_directory"]
    )


@router.get("/{name}", response_model=DependencyInfoResponse)
async def get_dependency(name: str) -> DependencyInfoResponse:
    """
    Get information about a specific dependency.
    
    Args:
        name: Name of the dependency
    
    Returns:
        Dependency information
    """
    manager = get_manager()
    info = manager.get_info(name)
    
    if info is None:
        raise HTTPException(status_code=404, detail=f"Dependency '{name}' not found")
    
    return _dependency_info_to_response(info)


@router.get("/{name}/diagnostics", response_model=DiagnosticResponse)
async def get_diagnostics(name: str) -> DiagnosticResponse:
    """
    Run diagnostics for a specific dependency.
    
    Args:
        name: Name of the dependency
    
    Returns:
        Diagnostic results
    """
    manager = get_manager()
    
    # Check if tool is registered
    if not manager.is_registered(name):
        raise HTTPException(status_code=404, detail=f"Dependency '{name}' not found")
    
    diagnostic = manager.diagnose(name)
    return _diagnostic_to_response(diagnostic)


@router.post("/{name}/install")
async def install_dependency(
    name: str,
    background_tasks: BackgroundTasks,
    version: Optional[str] = Query(None, description="Specific version to install"),
    force: bool = Query(False, description="Force reinstall if already installed")
) -> Dict[str, Any]:
    """
    Install a dependency.
    
    Args:
        name: Name of the dependency to install
        background_tasks: Background tasks handler
        version: Specific version to install
        force: Force reinstall if already installed
    
    Returns:
        Installation status
    """
    manager = get_manager()
    
    # Check if tool is registered
    if not manager.is_registered(name):
        raise HTTPException(status_code=404, detail=f"Dependency '{name}' not found")
    
    # Check if already installed
    info = manager.get_info(name)
    if info and info.status == DependencyStatus.INSTALLED and not force:
        return {
            "status": "already_installed",
            "message": f"{name} is already installed",
            "version": info.installed_version
        }
    
    # Start installation in background
    def install_task():
        manager.install(name, version=version, force=force)
    
    background_tasks.add_task(install_task)
    
    return {
        "status": "installing",
        "message": f"Installing {name}...",
        "version": version
    }


@router.post("/{name}/configure")
async def configure_dependency(
    name: str,
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Configure a dependency.
    
    Args:
        name: Name of the dependency to configure
        settings: Configuration settings
    
    Returns:
        Configuration status
    """
    manager = get_manager()
    
    # Check if tool is registered
    if not manager.is_registered(name):
        raise HTTPException(status_code=404, detail=f"Dependency '{name}' not found")
    
    success = manager.configure(name, **settings)
    
    if not success:
        raise HTTPException(status_code=400, detail="Configuration failed")
    
    return {
        "status": "configured",
        "message": f"{name} configured successfully",
        "settings": settings
    }


@router.get("/{name}/verify", response_model=DiagnosticResponse)
async def verify_dependency(name: str) -> DiagnosticResponse:
    """
    Verify a dependency installation.
    
    Args:
        name: Name of the dependency to verify
    
    Returns:
        Verification results
    """
    manager = get_manager()
    
    # Check if tool is registered
    if not manager.is_registered(name):
        raise HTTPException(status_code=404, detail=f"Dependency '{name}' not found")
    
    diagnostic = manager.verify(name)
    return _diagnostic_to_response(diagnostic)


@router.post("/refresh")
async def refresh_dependencies() -> Dict[str, Any]:
    """
    Refresh all dependency information.
    
    Returns:
        Refresh status
    """
    manager = get_manager()
    manager.refresh()
    
    return {
        "status": "refreshed",
        "message": "Dependencies refreshed successfully"
    }


@router.get("/diagnostics/all")
async def get_all_diagnostics() -> List[Dict[str, Any]]:
    """
    Run diagnostics for all dependencies.
    
    Returns:
        List of diagnostic results
    """
    manager = get_manager()
    
    tools = manager.list_tools()
    results = []
    
    for tool_name in tools:
        diagnostic = manager.diagnose(tool_name)
        results.append({
            "name": tool_name,
            "diagnostic": _diagnostic_to_response(diagnostic).model_dump()
        })
    
    return results