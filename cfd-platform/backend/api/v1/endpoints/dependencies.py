"""
Dependency Manager API Endpoints

Provides REST API endpoints for managing CFD platform dependencies.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from backend.infrastructure.dependency_manager import DependencyManager

router = APIRouter(prefix="/dependencies", tags=["dependencies"])

# Initialize dependency manager
dependency_manager = DependencyManager()


# Request/Response Models
class InstallRequest(BaseModel):
    """Request model for installing a dependency."""
    version: Optional[str] = Field(None, description="Specific version to install")
    force: bool = Field(False, description="Force reinstall if already installed")


class ConfigureRequest(BaseModel):
    """Request model for configuring a dependency."""
    settings: dict = Field(..., description="Configuration settings")


class DiagnosticResponse(BaseModel):
    """Response model for diagnostic results."""
    healthy: bool
    message: str
    errors: list[str] = []
    warnings: list[str] = []
    severity: str
    metrics: Optional[dict] = None


class DependencyResponse(BaseModel):
    """Response model for dependency information."""
    name: str
    display_name: str
    description: str
    category: str
    status: str
    installed_version: Optional[str] = None
    required_version: Optional[str] = None
    install_path: Optional[str] = None
    homepage: str
    documentation: str
    dependencies: list[dict] = []


class InstallResponse(BaseModel):
    """Response model for installation results."""
    success: bool
    message: str
    install_path: Optional[str] = None
    version: Optional[str] = None


class ConfigureResponse(BaseModel):
    """Response model for configuration results."""
    success: bool
    message: str
    settings: dict


class PlatformResponse(BaseModel):
    """Response model for platform information."""
    platform: str
    architecture: str
    package_manager: str
    home_directory: str


# Endpoints
@router.get("", response_model=list[DependencyResponse], responses={500: {"description": "Internal server error"}})
async def list_dependencies(category: Optional[str] = None):
    """
    List all available dependencies.
    
    Args:
        category: Optional category filter (engineering, platform, python_pkg)
    
    Returns:
        List of dependency information
    """
    try:
        dependencies = dependency_manager.list_dependencies(category)
        return [
            DependencyResponse(
                name=d.name,
                display_name=d.display_name,
                description=d.description,
                category=d.category.value if hasattr(d.category, 'value') else str(d.category),
                status=d.status.value if hasattr(d.status, 'value') else str(d.status),
                installed_version=d.installed_version,
                required_version=d.required_version,
                install_path=d.install_path,
                homepage=d.homepage,
                documentation=d.documentation,
                dependencies=[]
            )
            for d in dependencies
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform", response_model=PlatformResponse, responses={500: {"description": "Internal server error"}})
async def get_platform_info():
    """
    Get platform information.
    
    Returns:
        Platform detection information
    """
    try:
        platform_info = dependency_manager.get_platform_info()
        return PlatformResponse(
            platform=platform_info.platform.value if hasattr(platform_info.platform, 'value') else str(platform_info.platform),
            architecture=platform_info.architecture,
            package_manager=platform_info.package_manager.value if hasattr(platform_info.package_manager, 'value') else str(platform_info.package_manager),
            home_directory=platform_info.home_directory
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}", response_model=DependencyResponse, responses={404: {"description": "Dependency not found"}, 500: {"description": "Internal server error"}})
async def get_dependency(name: str):
    """
    Get information about a specific dependency.
    
    Args:
        name: Dependency name
    
    Returns:
        Dependency information
    """
    try:
        dependency = dependency_manager.get_dependency(name)
        if not dependency:
            raise HTTPException(status_code=404, detail=f"Dependency '{name}' not found")
        
        return DependencyResponse(
            name=dependency.name,
            display_name=dependency.display_name,
            description=dependency.description,
            category=dependency.category.value if hasattr(dependency.category, 'value') else str(dependency.category),
            status=dependency.status.value if hasattr(dependency.status, 'value') else str(dependency.status),
            installed_version=dependency.installed_version,
            required_version=dependency.required_version,
            install_path=dependency.install_path,
            homepage=dependency.homepage,
            documentation=dependency.documentation,
            dependencies=[]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/diagnostics", response_model=DiagnosticResponse, responses={404: {"description": "Dependency not found"}, 500: {"description": "Internal server error"}})
async def run_diagnostics(name: str):
    """
    Run diagnostics on a specific dependency.
    
    Args:
        name: Dependency name
    
    Returns:
        Diagnostic results
    """
    try:
        diagnostic = dependency_manager.diagnose(name)
        if not diagnostic:
            raise HTTPException(status_code=404, detail=f"Dependency '{name}' not found")
        
        return DiagnosticResponse(
            healthy=diagnostic.healthy,
            message=diagnostic.message,
            errors=diagnostic.errors,
            warnings=diagnostic.warnings,
            severity=diagnostic.severity.value if hasattr(diagnostic.severity, 'value') else str(diagnostic.severity),
            metrics=diagnostic.metrics
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/install", response_model=InstallResponse, responses={500: {"description": "Internal server error"}})
async def install_dependency(name: str, request: InstallRequest = None):
    """
    Install a specific dependency.
    
    Args:
        name: Dependency name
        request: Optional installation parameters
    
    Returns:
        Installation result
    """
    try:
        version = request.version if request else None
        force = request.force if request else False
        
        result = dependency_manager.install(name, version=version, force=force)
        
        return InstallResponse(
            success=result.success,
            message=result.message,
            install_path=result.install_path,
            version=result.version
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/configure", response_model=ConfigureResponse, responses={500: {"description": "Internal server error"}})
async def configure_dependency(name: str, request: ConfigureRequest):
    """
    Configure a specific dependency.
    
    Args:
        name: Dependency name
        request: Configuration settings
    
    Returns:
        Configuration result
    """
    try:
        result = dependency_manager.configure(name, request.settings)
        
        return ConfigureResponse(
            success=result.success,
            message=result.message,
            settings=result.settings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diagnose-all", responses={500: {"description": "Internal server error"}})
async def run_all_diagnostics(background_tasks: BackgroundTasks):
    """
    Run diagnostics on all dependencies.
    
    Returns:
        Summary of diagnostic results
    """
    try:
        results = dependency_manager.diagnose_all()
        
        # Return summary
        total = len(results)
        healthy = sum(1 for r in results.values() if r.healthy)
        unhealthy = total - healthy
        
        return {
            "total": total,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "results": {
                name: DiagnosticResponse(
                    healthy=r.healthy,
                    message=r.message,
                    errors=r.errors,
                    warnings=r.warnings,
                    severity=r.severity.value if hasattr(r.severity, 'value') else str(r.severity),
                    metrics=r.metrics
                )
                for name, r in results.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install-all", responses={500: {"description": "Internal server error"}})
async def install_all_dependencies(background_tasks: BackgroundTasks):
    """
    Install all missing dependencies.
    
    Returns:
        Summary of installation results
    """
    try:
        results = dependency_manager.install_all()
        
        total = len(results)
        successful = sum(1 for r in results.values() if r.success)
        failed = total - successful
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "results": {
                name: InstallResponse(
                    success=r.success,
                    message=r.message,
                    install_path=r.install_path,
                    version=r.version
                )
                for name, r in results.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))