"""
Mesh management routes for CFD Backend.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.core.config import get_settings
from cfd_backend.core.dependencies import get_db_session
from cfd_backend.core.exceptions import NotFoundError, ValidationError
from cfd_backend.models.mesh import Mesh, MeshStatus, MeshFormat
from cfd_backend.models.project import Project, ProjectStatus
from cfd_backend.models.user import User, UserRole
from cfd_backend.api.v1.auth import get_current_active_user
from cfd_backend.services.mesh_service import MeshService

router = APIRouter()


class MeshCreate(BaseModel):
    """Mesh creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: UUID
    format: MeshFormat = MeshFormat.GMSH
    geometry_file_id: Optional[UUID] = None
    gmsh_script: Optional[str] = None
    mesh_parameters: dict = Field(default_factory=dict)
    quality_thresholds: dict = Field(default_factory=dict)


class MeshUpdate(BaseModel):
    """Mesh update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    mesh_parameters: Optional[dict] = None
    quality_thresholds: Optional[dict] = None


class MeshResponse(BaseModel):
    """Mesh response model."""
    id: str
    name: str
    description: Optional[str]
    project_id: str
    format: MeshFormat
    status: MeshStatus
    file_path: Optional[str]
    file_size: Optional[int]
    element_count: Optional[int]
    node_count: Optional[int]
    boundary_count: Optional[int]
    min_quality: Optional[float]
    avg_quality: Optional[float]
    max_aspect_ratio: Optional[float]
    max_skewness: Optional[float]
    mesh_parameters: dict
    quality_thresholds: dict
    quality_report: Optional[dict]
    error_message: Optional[str]
    generated_at: Optional[str]
    created_at: str
    updated_at: str


class MeshListResponse(BaseModel):
    """Mesh list response with pagination."""
    meshes: List[MeshResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MeshGenerateRequest(BaseModel):
    """Mesh generation request."""
    overwrite: bool = False
    parameters: Optional[dict] = None


class MeshQualityResponse(BaseModel):
    """Mesh quality metrics response."""
    mesh_id: str
    element_count: int
    node_count: int
    boundary_count: int
    min_quality: float
    avg_quality: float
    max_aspect_ratio: float
    max_skewness: float
    quality_distribution: dict
    failed_elements: int
    warnings: List[str]
    report_path: Optional[str]


@router.get("", response_model=MeshListResponse)
async def list_meshes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[UUID] = None,
    status: Optional[MeshStatus] = None,
    format: Optional[MeshFormat] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(name|created_at|updated_at|status|element_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List meshes with pagination and filters."""
    query = select(Mesh).options(
        selectinload(Mesh.project),
    )
    
    # Filter by project access
    if project_id:
        project_result = await db.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project", str(project_id))
        
        if not _check_project_access(project, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to project",
            )
        query = query.where(Mesh.project_id == project_id)
    else:
        # Filter by accessible projects
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
            accessible_project_ids = select(Project.id).where(
                or_(
                    Project.owner_id == current_user.id,
                    and_(
                        Project.visibility == "public",
                        Project.status != ProjectStatus.ARCHIVED,
                    ),
                )
            )
            query = query.where(Mesh.project_id.in_(accessible_project_ids))
    
    if status:
        query = query.where(Mesh.status == status)
    
    if format:
        query = query.where(Mesh.format == format)
    
    if search:
        query = query.where(
            or_(
                Mesh.name.ilike(f"%{search}%"),
                Mesh.description.ilike(f"%{search}%"),
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply sorting
    sort_column = getattr(Mesh, sort_by, Mesh.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    meshes = result.scalars().all()
    
    return MeshListResponse(
        meshes=[
            MeshResponse(
                id=str(m.id),
                name=m.name,
                description=m.description,
                project_id=str(m.project_id),
                format=m.format,
                status=m.status,
                file_path=m.file_path,
                file_size=m.file_size,
                element_count=m.element_count,
                node_count=m.node_count,
                boundary_count=m.boundary_count,
                min_quality=m.min_quality,
                avg_quality=m.avg_quality,
                max_aspect_ratio=m.max_aspect_ratio,
                max_skewness=m.max_skewness,
                mesh_parameters=m.mesh_parameters,
                quality_thresholds=m.quality_thresholds,
                quality_report=m.quality_report,
                error_message=m.error_message,
                generated_at=m.generated_at.isoformat() if m.generated_at else None,
                created_at=m.created_at.isoformat(),
                updated_at=m.updated_at.isoformat(),
            )
            for m in meshes
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=MeshResponse, status_code=status.HTTP_201_CREATED)
async def create_mesh(
    mesh_data: MeshCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new mesh entry."""
    # Verify project access
    project_result = await db.execute(select(Project).where(Project.id == mesh_data.project_id))
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(mesh_data.project_id))
    
    if not _check_project_write_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied to project",
        )
    
    # Create mesh
    mesh = Mesh(
        name=mesh_data.name,
        description=mesh_data.description,
        project_id=mesh_data.project_id,
        format=mesh_data.format,
        geometry_file_id=mesh_data.geometry_file_id,
        gmsh_script=mesh_data.gmsh_script,
        mesh_parameters=mesh_data.mesh_parameters,
        quality_thresholds=mesh_data.quality_thresholds,
        status=MeshStatus.PENDING,
    )
    
    db.add(mesh)
    await db.commit()
    await db.refresh(mesh)
    
    return MeshResponse(
        id=str(mesh.id),
        name=mesh.name,
        description=mesh.description,
        project_id=str(mesh.project_id),
        format=mesh.format,
        status=mesh.status,
        file_path=mesh.file_path,
        file_size=mesh.file_size,
        element_count=mesh.element_count,
        node_count=mesh.node_count,
        boundary_count=mesh.boundary_count,
        min_quality=mesh.min_quality,
        avg_quality=mesh.avg_quality,
        max_aspect_ratio=mesh.max_aspect_ratio,
        max_skewness=mesh.max_skewness,
        mesh_parameters=mesh.mesh_parameters,
        quality_thresholds=mesh.quality_thresholds,
        quality_report=mesh.quality_report,
        error_message=mesh.error_message,
        generated_at=mesh.generated_at.isoformat() if mesh.generated_at else None,
        created_at=mesh.created_at.isoformat(),
        updated_at=mesh.updated_at.isoformat(),
    )


@router.post("/upload", response_model=MeshResponse, status_code=status.HTTP_201_CREATED)
async def upload_mesh(
    project_id: UUID,
    file: UploadFile = File(...),
    name: Optional[str] = None,
    description: Optional[str] = None,
    format: MeshFormat = MeshFormat.OPENFOAM,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Upload a mesh file."""
    # Verify project access
    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(project_id))
    
    if not _check_project_write_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied to project",
        )
    
    # Validate file
    allowed_extensions = {".msh", ".foam", ".vtk", ".vtu", ".stl", ".obj", ".ply"}
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_ext not in allowed_extensions:
        raise ValidationError(f"Unsupported file format: {file_ext}")
    
    # Save file
    import os
    from cfd_backend.core.config import get_settings
    settings = get_settings()
    
    upload_dir = os.path.join(settings.UPLOAD_DIR, "meshes", str(project_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    content = await file.read()
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create mesh record
    mesh = Mesh(
        name=name or file.filename,
        description=description,
        project_id=project_id,
        format=format,
        file_path=file_path,
        file_size=len(content),
        status=MeshStatus.VALIDATING,
    )
    
    db.add(mesh)
    await db.commit()
    await db.refresh(mesh)
    
    # Validate mesh in background
    mesh_service = MeshService(db)
    await mesh_service.validate_mesh(mesh.id)
    
    return MeshResponse(
        id=str(mesh.id),
        name=mesh.name,
        description=mesh.description,
        project_id=str(mesh.project_id),
        format=mesh.format,
        status=mesh.status,
        file_path=mesh.file_path,
        file_size=mesh.file_size,
        element_count=mesh.element_count,
        node_count=mesh.node_count,
        boundary_count=mesh.boundary_count,
        min_quality=mesh.min_quality,
        avg_quality=mesh.avg_quality,
        max_aspect_ratio=mesh.max_aspect_ratio,
        max_skewness=mesh.max_skewness,
        mesh_parameters=mesh.mesh_parameters,
        quality_thresholds=mesh.quality_thresholds,
        quality_report=mesh.quality_report,
        error_message=mesh.error_message,
        generated_at=mesh.generated_at.isoformat() if mesh.generated_at else None,
        created_at=mesh.created_at.isoformat(),
        updated_at=mesh.updated_at.isoformat(),
    )


@router.get("/{mesh_id}", response_model=MeshResponse)
async def get_mesh(
    mesh_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get mesh by ID."""
    result = await db.execute(
        select(Mesh)
        .options(selectinload(Mesh.project))
        .where(Mesh.id == mesh_id)
    )
    mesh = result.scalar_one_or_none()
    
    if not mesh:
        raise NotFoundError("Mesh", str(mesh_id))
    
    if not _check_project_access(mesh.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to mesh",
        )
    
    return MeshResponse(
        id=str(mesh.id),
        name=mesh.name,
        description=mesh.description,
        project_id=str(mesh.project_id),
        format=mesh.format,
        status=mesh.status,
        file_path=mesh.file_path,
        file_size=mesh.file_size,
        element_count=mesh.element_count,
        node_count=mesh.node_count,
        boundary_count=mesh.boundary_count,
        min_quality=mesh.min_quality,
        avg_quality=mesh.avg_quality,
        max_aspect_ratio=mesh.max_aspect_ratio,
        max_skewness=mesh.max_skewness,
        mesh_parameters=mesh.mesh_parameters,
        quality_thresholds=mesh.quality_thresholds,
        quality_report=mesh.quality_report,
        error_message=mesh.error_message,
        generated_at=mesh.generated_at.isoformat() if mesh.generated_at else None,
        created_at=mesh.created_at.isoformat(),
        updated_at=mesh.updated_at.isoformat(),
    )


@router.patch("/{mesh_id}", response_model=MeshResponse)
async def update_mesh(
    mesh_id: UUID,
    mesh_data: MeshUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update mesh metadata."""
    result = await db.execute(
        select(Mesh)
        .options(selectinload(Mesh.project))
        .where(Mesh.id == mesh_id)
    )
    mesh = result.scalar_one_or_none()
    
    if not mesh:
        raise NotFoundError("Mesh", str(mesh_id))
    
    if not _check_project_write_access(mesh.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    update_data = mesh_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(mesh, field, value)
    
    mesh.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(mesh)
    
    return MeshResponse(
        id=str(mesh.id),
        name=mesh.name,
        description=mesh.description,
        project_id=str(mesh.project_id),
        format=mesh.format,
        status=mesh.status,
        file_path=mesh.file_path,
        file_size=mesh.file_size,
        element_count=mesh.element_count,
        node_count=mesh.node_count,
        boundary_count=mesh.boundary_count,
        min_quality=mesh.min_quality,
        avg_quality=mesh.avg_quality,
        max_aspect_ratio=mesh.max_aspect_ratio,
        max_skewness=mesh.max_skewness,
        mesh_parameters=mesh.mesh_parameters,
        quality_thresholds=mesh.quality_thresholds,
        quality_report=mesh.quality_report,
        error_message=mesh.error_message,
        generated_at=mesh.generated_at.isoformat() if mesh.generated_at else None,
        created_at=mesh.created_at.isoformat(),
        updated_at=mesh.updated_at.isoformat(),
    )


@router.delete("/{mesh_id}")
async def delete_mesh(
    mesh_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete mesh."""
    result = await db.execute(
        select(Mesh)
        .options(selectinload(Mesh.project))
        .where(Mesh.id == mesh_id)
    )
    mesh = result.scalar_one_or_none()
    
    if not mesh:
        raise NotFoundError("Mesh", str(mesh_id))
    
    if not _check_project_write_access(mesh.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    # Delete file if exists
    if mesh.file_path:
        import os
        try:
            os.remove(mesh.file_path)
        except OSError:
            pass
    
    await db.delete(mesh)
    await db.commit()
    
    return {"message": "Mesh deleted"}


@router.post("/{mesh_id}/generate")
async def generate_mesh(
    mesh_id: UUID,
    generate_request: MeshGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate mesh using Gmsh."""
    result = await db.execute(
        select(Mesh)
        .options(selectinload(Mesh.project))
        .where(Mesh.id == mesh_id)
    )
    mesh = result.scalar_one_or_none()
    
    if not mesh:
        raise NotFoundError("Mesh", str(mesh_id))
    
    if not _check_project_write_access(mesh.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if mesh.status in [MeshStatus.GENERATING, MeshStatus.READY] and not generate_request.overwrite:
        raise ValidationError("Mesh already generated. Use overwrite=true to regenerate.")
    
    # Update parameters if provided
    if generate_request.parameters:
        mesh.mesh_parameters.update(generate_request.parameters)
    
    mesh.status = MeshStatus.GENERATING
    mesh.updated_at = datetime.utcnow()
    await db.commit()
    
    # Generate mesh in background
    mesh_service = MeshService(db)
    background_tasks.add_task(
        mesh_service.generate_mesh,
        mesh_id,
        overwrite=generate_request.overwrite,
    )
    
    return {"message": "Mesh generation started", "mesh_id": str(mesh_id)}


@router.get("/{mesh_id}/quality", response_model=MeshQualityResponse)
async def get_mesh_quality(
    mesh_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get mesh quality metrics."""
    result = await db.execute(
        select(Mesh)
        .options(selectinload(Mesh.project))
        .where(Mesh.id == mesh_id)
    )
    mesh = result.scalar_one_or_none()
    
    if not mesh:
        raise NotFoundError("Mesh", str(mesh_id))
    
    if not _check_project_access(mesh.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    if mesh.status != MeshStatus.READY:
        raise ValidationError("Mesh not ready for quality assessment")
    
    # Return cached quality report or compute
    if mesh.quality_report:
        return MeshQualityResponse(
            mesh_id=str(mesh.id),
            element_count=mesh.element_count or 0,
            node_count=mesh.node_count or 0,
            boundary_count=mesh.boundary_count or 0,
            min_quality=mesh.min_quality or 0.0,
            avg_quality=mesh.avg_quality or 0.0,
            max_aspect_ratio=mesh.max_aspect_ratio or 0.0,
            max_skewness=mesh.max_skewness or 0.0,
            quality_distribution=mesh.quality_report.get("distribution", {}),
            failed_elements=mesh.quality_report.get("failed_elements", 0),
            warnings=mesh.quality_report.get("warnings", []),
            report_path=mesh.quality_report.get("report_path"),
        )
    
    # Compute quality if not cached
    mesh_service = MeshService(db)
    quality_report = await mesh_service.compute_quality(mesh_id)
    
    return MeshQualityResponse(
        mesh_id=str(mesh.id),
        element_count=quality_report["element_count"],
        node_count=quality_report["node_count"],
        boundary_count=quality_report["boundary_count"],
        min_quality=quality_report["min_quality"],
        avg_quality=quality_report["avg_quality"],
        max_aspect_ratio=quality_report["max_aspect_ratio"],
        max_skewness=quality_report["max_skewness"],
        quality_distribution=quality_report["distribution"],
        failed_elements=quality_report["failed_elements"],
        warnings=quality_report["warnings"],
        report_path=quality_report.get("report_path"),
    )


@router.post("/{mesh_id}/convert")
async def convert_mesh(
    mesh_id: UUID,
    target_format: MeshFormat,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Convert mesh to different format."""
    result = await db.execute(
        select(Mesh)
        .options(selectinload(Mesh.project))
        .where(Mesh.id == mesh_id)
    )
    mesh = result.scalar_one_or_none()
    
    if not mesh:
        raise NotFoundError("Mesh", str(mesh_id))
    
    if not _check_project_write_access(mesh.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if mesh.status != MeshStatus.READY:
        raise ValidationError("Mesh not ready for conversion")
    
    mesh_service = MeshService(db)
    new_mesh = await mesh_service.convert_mesh(mesh_id, target_format)
    
    return {
        "message": "Mesh converted",
        "new_mesh_id": str(new_mesh.id),
        "format": new_mesh.format,
    }


def _check_project_access(project: Project, user: User) -> bool:
    """Check if user has read access to project."""
    if user.role in [UserRole.ADMIN, UserRole.MANAGER]:
        return True
    if project.owner_id == user.id:
        return True
    if project.visibility == "public" and project.status != ProjectStatus.ARCHIVED:
        return True
    return False


def _check_project_write_access(project: Project, user: User) -> bool:
    """Check if user has write access to project."""
    if user.role == UserRole.ADMIN:
        return True
    if project.owner_id == user.id:
        return True
    return False