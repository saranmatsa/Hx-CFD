"""
CFD Project management routes for CFD Backend.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.core.config import get_settings
from cfd_backend.core.dependencies import get_db_session
from cfd_backend.core.exceptions import NotFoundError, ValidationError
from cfd_backend.models.project import Project, ProjectStatus, ProjectVisibility
from cfd_backend.models.user import User, UserRole
from cfd_backend.models.mesh import Mesh
from cfd_backend.models.simulation import Simulation
from cfd_backend.api.v1.auth import get_current_active_user

router = APIRouter()


class ProjectCreate(BaseModel):
    """Project creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    visibility: ProjectVisibility = ProjectVisibility.PRIVATE
    solver: str = "openfoam"
    solver_version: Optional[str] = None
    turbulence_model: Optional[str] = None
    reference_velocity: Optional[float] = None
    reference_length: Optional[float] = None
    fluid_density: Optional[float] = None
    fluid_viscosity: Optional[float] = None


class ProjectUpdate(BaseModel):
    """Project update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    visibility: Optional[ProjectVisibility] = None
    solver: Optional[str] = None
    solver_version: Optional[str] = None
    turbulence_model: Optional[str] = None
    reference_velocity: Optional[float] = None
    reference_length: Optional[float] = None
    fluid_density: Optional[float] = None
    fluid_viscosity: Optional[float] = None
    status: Optional[ProjectStatus] = None


class ProjectResponse(BaseModel):
    """Project response model."""
    id: str
    name: str
    description: Optional[str]
    visibility: ProjectVisibility
    status: ProjectStatus
    solver: str
    solver_version: Optional[str]
    turbulence_model: Optional[str]
    reference_velocity: Optional[float]
    reference_length: Optional[float]
    fluid_density: Optional[float]
    fluid_viscosity: Optional[float]
    owner_id: str
    mesh_count: int
    simulation_count: int
    created_at: str
    updated_at: str
    last_simulation_at: Optional[str]


class ProjectListResponse(BaseModel):
    """Project list response with pagination."""
    projects: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProjectStatsResponse(BaseModel):
    """Project statistics response."""
    total_meshes: int
    total_simulations: int
    completed_simulations: int
    failed_simulations: int
    running_simulations: int
    total_cpu_hours: float
    total_storage_bytes: int


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[ProjectStatus] = None,
    visibility: Optional[ProjectVisibility] = None,
    solver: Optional[str] = None,
    sort_by: str = Query("updated_at", pattern="^(name|created_at|updated_at|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List projects with pagination and filters."""
    query = select(Project).options(
        selectinload(Project.meshes),
        selectinload(Project.simulations),
    )
    
    # Filter by ownership/visibility
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        query = query.where(
            or_(
                Project.owner_id == current_user.id,
                and_(
                    Project.visibility == ProjectVisibility.PUBLIC,
                    Project.status != ProjectStatus.ARCHIVED,
                ),
                and_(
                    Project.visibility == ProjectVisibility.TEAM,
                    Project.owner_id.in_(
                        select(User.id).where(User.id == current_user.id)
                    ),
                ),
            )
        )
    
    if search:
        query = query.where(
            or_(
                Project.name.ilike(f"%{search}%"),
                Project.description.ilike(f"%{search}%"),
            )
        )
    
    if status:
        query = query.where(Project.status == status)
    
    if visibility:
        query = query.where(Project.visibility == visibility)
    
    if solver:
        query = query.where(Project.solver == solver)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply sorting
    sort_column = getattr(Project, sort_by, Project.updated_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ProjectListResponse(
        projects=[
            ProjectResponse(
                id=str(p.id),
                name=p.name,
                description=p.description,
                visibility=p.visibility,
                status=p.status,
                solver=p.solver,
                solver_version=p.solver_version,
                turbulence_model=p.turbulence_model,
                reference_velocity=p.reference_velocity,
                reference_length=p.reference_length,
                fluid_density=p.fluid_density,
                fluid_viscosity=p.fluid_viscosity,
                owner_id=str(p.owner_id),
                mesh_count=len(p.meshes),
                simulation_count=len(p.simulations),
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
                last_simulation_at=p.last_simulation_at.isoformat() if p.last_simulation_at else None,
            )
            for p in projects
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new CFD project."""
    project = Project(
        name=project_data.name,
        description=project_data.description,
        visibility=project_data.visibility,
        solver=project_data.solver,
        solver_version=project_data.solver_version,
        turbulence_model=project_data.turbulence_model,
        reference_velocity=project_data.reference_velocity,
        reference_length=project_data.reference_length,
        fluid_density=project_data.fluid_density,
        fluid_viscosity=project_data.fluid_viscosity,
        owner_id=current_user.id,
        status=ProjectStatus.DRAFT,
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        visibility=project.visibility,
        status=project.status,
        solver=project.solver,
        solver_version=project.solver_version,
        turbulence_model=project.turbulence_model,
        reference_velocity=project.reference_velocity,
        reference_length=project.reference_length,
        fluid_density=project.fluid_density,
        fluid_viscosity=project.fluid_viscosity,
        owner_id=str(project.owner_id),
        mesh_count=0,
        simulation_count=0,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        last_simulation_at=None,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get project by ID."""
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.meshes),
            selectinload(Project.simulations),
        )
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(project_id))
    
    # Check access
    if not _check_project_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project",
        )
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        visibility=project.visibility,
        status=project.status,
        solver=project.solver,
        solver_version=project.solver_version,
        turbulence_model=project.turbulence_model,
        reference_velocity=project.reference_velocity,
        reference_length=project.reference_length,
        fluid_density=project.fluid_density,
        fluid_viscosity=project.fluid_viscosity,
        owner_id=str(project.owner_id),
        mesh_count=len(project.meshes),
        simulation_count=len(project.simulations),
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        last_simulation_at=project.last_simulation_at.isoformat() if project.last_simulation_at else None,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(project_id))
    
    # Check write access
    if not _check_project_write_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    # Update fields
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    project.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)
    
    # Reload with relationships
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.meshes),
            selectinload(Project.simulations),
        )
        .where(Project.id == project_id)
    )
    project = result.scalar_one()
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        visibility=project.visibility,
        status=project.status,
        solver=project.solver,
        solver_version=project.solver_version,
        turbulence_model=project.turbulence_model,
        reference_velocity=project.reference_velocity,
        reference_length=project.reference_length,
        fluid_density=project.fluid_density,
        fluid_viscosity=project.fluid_viscosity,
        owner_id=str(project.owner_id),
        mesh_count=len(project.meshes),
        simulation_count=len(project.simulations),
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        last_simulation_at=project.last_simulation_at.isoformat() if project.last_simulation_at else None,
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete project (owner or admin only)."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(project_id))
    
    # Check ownership
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner or admin can delete",
        )
    
    await db.delete(project)
    await db.commit()
    
    return {"message": "Project deleted"}


@router.get("/{project_id}/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get project statistics."""
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.meshes),
            selectinload(Project.simulations),
        )
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(project_id))
    
    if not _check_project_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Calculate stats
    total_meshes = len(project.meshes)
    total_simulations = len(project.simulations)
    completed_simulations = sum(1 for s in project.simulations if s.status == "completed")
    failed_simulations = sum(1 for s in project.simulations if s.status == "failed")
    running_simulations = sum(1 for s in project.simulations if s.status == "running")
    
    total_cpu_hours = sum(s.cpu_hours or 0 for s in project.simulations)
    total_storage = sum(m.file_size or 0 for m in project.meshes)
    total_storage += sum(s.result_size or 0 for s in project.simulations)
    
    return ProjectStatsResponse(
        total_meshes=total_meshes,
        total_simulations=total_simulations,
        completed_simulations=completed_simulations,
        failed_simulations=failed_simulations,
        running_simulations=running_simulations,
        total_cpu_hours=total_cpu_hours,
        total_storage_bytes=total_storage,
    )


@router.post("/{project_id}/archive")
async def archive_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Archive a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(project_id))
    
    if not _check_project_write_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    project.status = ProjectStatus.ARCHIVED
    project.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Project archived"}


@router.post("/{project_id}/restore")
async def restore_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Restore an archived project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(project_id))
    
    if not _check_project_write_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    project.status = ProjectStatus.DRAFT
    project.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Project restored"}


def _check_project_access(project: Project, user: User) -> bool:
    """Check if user has read access to project."""
    if user.role in [UserRole.ADMIN, UserRole.MANAGER]:
        return True
    if project.owner_id == user.id:
        return True
    if project.visibility == ProjectVisibility.PUBLIC and project.status != ProjectStatus.ARCHIVED:
        return True
    if project.visibility == ProjectVisibility.TEAM:
        # TODO: Check team membership
        return False
    return False


def _check_project_write_access(project: Project, user: User) -> bool:
    """Check if user has write access to project."""
    if user.role == UserRole.ADMIN:
        return True
    if project.owner_id == user.id:
        return True
    return False