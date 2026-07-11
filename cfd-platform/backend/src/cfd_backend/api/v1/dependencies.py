"""
Dependency detection API routes for CFD Backend.

Provides endpoints for detecting and managing CFD software dependencies
(OpenFOAM, Gmsh, ParaView, Python packages).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from uuid import UUID

from cfd_backend.api.deps import get_current_active_user
from cfd_backend.models.user import User
from cfd_backend.services.dependencies import DependencyDetectionService, ToolInfo, DependencyReport

router = APIRouter()


# Request/Response Models
class ToolInfoResponse(BaseModel):
    """Response model for tool information."""
    name: str
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None


class DependencyReportResponse(BaseModel):
    """Response model for dependency report."""
    all_available: bool
    tools: Dict[str, ToolInfoResponse]
    python_packages: Dict[str, ToolInfoResponse]
    missing_tools: List[str]
    warnings: List[str]


class ValidateCaseRequest(BaseModel):
    """Request model for validating OpenFOAM case."""
    case_path: str = Field(..., description="Path to OpenFOAM case directory")


class ValidateCaseResponse(BaseModel):
    """Response model for case validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    files_found: List[str]
    files_missing: List[str]


class SolversResponse(BaseModel):
    """Response model for available solvers."""
    solvers: List[str]


class VersionInfoResponse(BaseModel):
    """Response model for version information."""
    version: str
    info: str


# Dependency injection
def get_dependency_service() -> DependencyDetectionService:
    """Get dependency detection service instance."""
    return DependencyDetectionService()


@router.get("/detect", response_model=DependencyReportResponse)
async def detect_dependencies(
    force_refresh: bool = False,
    current_user: User = Depends(get_current_active_user),
    service: DependencyDetectionService = Depends(get_dependency_service),
):
    """
    Detect all CFD software dependencies.
    
    Checks for OpenFOAM, Gmsh, ParaView, and required Python packages.
    Use force_refresh=true to bypass cache.
    """
    if force_refresh:
        service.invalidate_cache()
    
    report = await service.detect_all()
    
    return DependencyReportResponse(
        all_available=report.all_available,
        tools={
            name: ToolInfoResponse(
                name=tool.name,
                available=tool.available,
                path=str(tool.path) if tool.path else None,
                version=tool.version,
                error=tool.error,
            )
            for name, tool in report.tools.items()
        },
        python_packages={
            name: ToolInfoResponse(
                name=tool.name,
                available=tool.available,
                path=str(tool.path) if tool.path else None,
                version=tool.version,
                error=tool.error,
            )
            for name, tool in report.python_packages.items()
        },
        missing_tools=report.missing_tools,
        warnings=report.warnings,
    )


@router.get("/openfoam", response_model=ToolInfoResponse)
async def detect_openfoam(
    current_user: User = Depends(get_current_active_user),
    service: DependencyDetectionService = Depends(get_dependency_service),
):
    """Detect OpenFOAM installation."""
    tool_info = await service.detect_openfoam()
    return ToolInfoResponse(
        name=tool_info.name,
        available=tool_info.available,
        path=str(tool_info.path) if tool_info.path else None,
        version=tool_info.version,
        error=tool_info.error,
    )


@router.get("/gmsh", response_model=ToolInfoResponse)
async def detect_gmsh(
    current_user: User = Depends(get_current_active_user),
    service: DependencyDetectionService = Depends(get_dependency_service),
):
    """Detect Gmsh installation."""
    tool_info = await service.detect_gmsh()
    return ToolInfoResponse(
        name=tool_info.name,
        available=tool_info.available,
        path=str(tool_info.path) if tool_info.path else None,
        version=tool_info.version,
        error=tool_info.error,
    )


@router.get("/paraview", response_model=ToolInfoResponse)
async def detect_paraview(
    current_user: User = Depends(get_current_active_user),
    service: DependencyDetectionService = Depends(get_dependency_service),
):
    """Detect ParaView installation."""
    tool_info = await service.detect_paraview()
    return ToolInfoResponse(
        name=tool_info.name,
        available=tool_info.available,
        path=str(tool_info.path) if tool_info.path else None,
        version=tool_info.version,
        error=tool_info.error,
    )


@router.get("/python-packages", response_model=Dict[str, ToolInfoResponse])
async def detect_python_packages(
    current_user: User = Depends(get_current_active_user),
    service: DependencyDetectionService = Depends(get_dependency_service),
):
    """Detect required Python packages."""
    packages = await service.detect_python_packages()
    return {
        name: ToolInfoResponse(
            name=tool.name,
            available=tool.available,
            path=str(tool.path) if tool.path else None,
            version=tool.version,
            error=tool.error,
        )
        for name, tool in packages.items()
    }


@router.post("/validate-case", response_model=ValidateCaseResponse)
async def validate_openfoam_case(
    request: ValidateCaseRequest,
    current_user: User = Depends(get_current_active_user),
    service: DependencyDetectionService = Depends(get_dependency_service),
):
    """Validate an OpenFOAM case directory structure."""
    from pathlib import Path
    
    case_path = Path(request.case_path)
    if not case_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case directory not found: {request.case_path}",
        )
    
    result = await service.validate_openfoam_case(case_path)
    return ValidateCaseResponse(**result)


@router.get("/solvers", response_model=SolversResponse)
async def get_openfoam_solvers(
    current_user: User = Depends(get_current_active_user),
    service: DependencyDetectionService = Depends(get_dependency_service),
):
    """Get list of available OpenFOAM solvers."""
    solvers = await service.get_openfoam_solvers()
    return SolversResponse(solvers=solvers)


@router.get("/gmsh/info", response_model=VersionInfoResponse)
async def get_gmsh_info(
    current_user: User = Depends(get_current_active_user),
    service: DependencyDetectionService = Depends(get_dependency_service),
):
    """Get detailed Gmsh version information."""
    info = await service.get_gmsh_version_info()
    return VersionInfoResponse(**info)


@router.get("/paraview/info", response_model=VersionInfoResponse)
async def get_paraview_info(
    current_user: User = Depends(get_current_active_user),
    service: DependencyDetectionService = Depends(get_dependency_service),
):
    """Get detailed ParaView version information."""
    info = await service.get_paraview_version_info()
    return VersionInfoResponse(**info)