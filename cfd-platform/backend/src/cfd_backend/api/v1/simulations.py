"""
Simulation management routes for CFD Backend.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.core.config import get_settings
from cfd_backend.core.dependencies import get_db_session
from cfd_backend.core.exceptions import NotFoundError, ValidationError
from cfd_backend.models.simulation import Simulation, SimulationStatus, SolverType
from cfd_backend.models.project import Project, ProjectStatus
from cfd_backend.models.mesh import Mesh
from cfd_backend.models.user import User, UserRole
from cfd_backend.api.v1.auth import get_current_active_user
from cfd_backend.services.simulation_service import SimulationService

router = APIRouter()


class SimulationCreate(BaseModel):
    """Simulation creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: UUID
    mesh_id: UUID
    solver_type: SolverType = SolverType.OPENFOAM
    solver_config: dict = Field(default_factory=dict)
    boundary_conditions: List[dict] = Field(default_factory=list)
    initial_conditions: dict = Field(default_factory=dict)
    solver_settings: dict = Field(default_factory=dict)
    max_runtime_hours: int = 24
    priority: int = 0


class SimulationUpdate(BaseModel):
    """Simulation update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    solver_config: Optional[dict] = None
    boundary_conditions: Optional[List[dict]] = None
    initial_conditions: Optional[dict] = None
    solver_settings: Optional[dict] = None
    max_runtime_hours: Optional[int] = None
    priority: Optional[int] = None


class SimulationResponse(BaseModel):
    """Simulation response model."""
    id: str
    name: str
    description: Optional[str]
    project_id: str
    mesh_id: str
    solver_type: SolverType
    status: SimulationStatus
    progress: float
    current_iteration: int
    max_iterations: int
    solver_config: dict
    boundary_conditions: List[dict]
    initial_conditions: dict
    solver_settings: dict
    max_runtime_hours: int
    priority: int
    cpu_hours: Optional[float]
    memory_peak_mb: Optional[int]
    disk_usage_bytes: Optional[int]
    result_size: Optional[int]
    error_message: Optional[str]
    log_path: Optional[str]
    result_path: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str


class SimulationListResponse(BaseModel):
    """Simulation list response with pagination."""
    simulations: List[SimulationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SimulationRunRequest(BaseModel):
    """Simulation run request."""
    restart: bool = False
    overwrite: bool = False


class SimulationStatusResponse(BaseModel):
    """Simulation status response."""
    id: str
    status: SimulationStatus
    progress: float
    current_iteration: int
    max_iterations: int
    cpu_hours: Optional[float]
    memory_peak_mb: Optional[int]
    error_message: Optional[str]
    started_at: Optional[str]
    estimated_completion: Optional[str]


@router.get("", response_model=SimulationListResponse)
async def list_simulations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[UUID] = None,
    mesh_id: Optional[UUID] = None,
    status: Optional[SimulationStatus] = None,
    solver_type: Optional[SolverType] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(name|created_at|updated_at|status|progress)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List simulations with pagination and filters."""
    query = select(Simulation).options(
        selectinload(Simulation.project),
        selectinload(Simulation.mesh),
    )
    
    # Filter by project access
    if project_id:
        # Verify project access
        project_result = await db.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project", str(project_id))
        
        if not _check_project_access(project, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to project",
            )
        query = query.where(Simulation.project_id == project_id)
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
            query = query.where(Simulation.project_id.in_(accessible_project_ids))
    
    if mesh_id:
        query = query.where(Simulation.mesh_id == mesh_id)
    
    if status:
        query = query.where(Simulation.status == status)
    
    if solver_type:
        query = query.where(Simulation.solver_type == solver_type)
    
    if search:
        query = query.where(
            or_(
                Simulation.name.ilike(f"%{search}%"),
                Simulation.description.ilike(f"%{search}%"),
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply sorting
    sort_column = getattr(Simulation, sort_by, Simulation.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    simulations = result.scalars().all()
    
    return SimulationListResponse(
        simulations=[
            SimulationResponse(
                id=str(s.id),
                name=s.name,
                description=s.description,
                project_id=str(s.project_id),
                mesh_id=str(s.mesh_id),
                solver_type=s.solver_type,
                status=s.status,
                progress=s.progress,
                current_iteration=s.current_iteration,
                max_iterations=s.max_iterations,
                solver_config=s.solver_config,
                boundary_conditions=s.boundary_conditions,
                initial_conditions=s.initial_conditions,
                solver_settings=s.solver_settings,
                max_runtime_hours=s.max_runtime_hours,
                priority=s.priority,
                cpu_hours=s.cpu_hours,
                memory_peak_mb=s.memory_peak_mb,
                disk_usage_bytes=s.disk_usage_bytes,
                result_size=s.result_size,
                error_message=s.error_message,
                log_path=s.log_path,
                result_path=s.result_path,
                started_at=s.started_at.isoformat() if s.started_at else None,
                completed_at=s.completed_at.isoformat() if s.completed_at else None,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            )
            for s in simulations
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    simulation_data: SimulationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new simulation."""
    # Verify project access
    project_result = await db.execute(select(Project).where(Project.id == simulation_data.project_id))
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(simulation_data.project_id))
    
    if not _check_project_write_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied to project",
        )
    
    # Verify mesh exists and belongs to project
    mesh_result = await db.execute(
        select(Mesh).where(
            and_(Mesh.id == simulation_data.mesh_id, Mesh.project_id == simulation_data.project_id)
        )
    )
    mesh = mesh_result.scalar_one_or_none()
    
    if not mesh:
        raise NotFoundError("Mesh", str(simulation_data.mesh_id))
    
    if mesh.status != "ready":
        raise ValidationError("Mesh is not ready for simulation")
    
    # Create simulation
    simulation = Simulation(
        name=simulation_data.name,
        description=simulation_data.description,
        project_id=simulation_data.project_id,
        mesh_id=simulation_data.mesh_id,
        solver_type=simulation_data.solver_type,
        solver_config=simulation_data.solver_config,
        boundary_conditions=simulation_data.boundary_conditions,
        initial_conditions=simulation_data.initial_conditions,
        solver_settings=simulation_data.solver_settings,
        max_runtime_hours=simulation_data.max_runtime_hours,
        priority=simulation_data.priority,
        status=SimulationStatus.PENDING,
        progress=0.0,
        current_iteration=0,
        max_iterations=simulation_data.solver_settings.get("max_iterations", 1000),
    )
    
    db.add(simulation)
    await db.commit()
    await db.refresh(simulation)
    
    return SimulationResponse(
        id=str(simulation.id),
        name=simulation.name,
        description=simulation.description,
        project_id=str(simulation.project_id),
        mesh_id=str(simulation.mesh_id),
        solver_type=simulation.solver_type,
        status=simulation.status,
        progress=simulation.progress,
        current_iteration=simulation.current_iteration,
        max_iterations=simulation.max_iterations,
        solver_config=simulation.solver_config,
        boundary_conditions=simulation.boundary_conditions,
        initial_conditions=simulation.initial_conditions,
        solver_settings=simulation.solver_settings,
        max_runtime_hours=simulation.max_runtime_hours,
        priority=simulation.priority,
        cpu_hours=simulation.cpu_hours,
        memory_peak_mb=simulation.memory_peak_mb,
        disk_usage_bytes=simulation.disk_usage_bytes,
        result_size=simulation.result_size,
        error_message=simulation.error_message,
        log_path=simulation.log_path,
        result_path=simulation.result_path,
        started_at=simulation.started_at.isoformat() if simulation.started_at else None,
        completed_at=simulation.completed_at.isoformat() if simulation.completed_at else None,
        created_at=simulation.created_at.isoformat(),
        updated_at=simulation.updated_at.isoformat(),
    )


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get simulation by ID."""
    result = await db.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.project),
            selectinload(Simulation.mesh),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(simulation_id))
    
    # Check project access
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to simulation",
        )
    
    return SimulationResponse(
        id=str(simulation.id),
        name=simulation.name,
        description=simulation.description,
        project_id=str(simulation.project_id),
        mesh_id=str(simulation.mesh_id),
        solver_type=simulation.solver_type,
        status=simulation.status,
        progress=simulation.progress,
        current_iteration=simulation.current_iteration,
        max_iterations=simulation.max_iterations,
        solver_config=simulation.solver_config,
        boundary_conditions=simulation.boundary_conditions,
        initial_conditions=simulation.initial_conditions,
        solver_settings=simulation.solver_settings,
        max_runtime_hours=simulation.max_runtime_hours,
        priority=simulation.priority,
        cpu_hours=simulation.cpu_hours,
        memory_peak_mb=simulation.memory_peak_mb,
        disk_usage_bytes=simulation.disk_usage_bytes,
        result_size=simulation.result_size,
        error_message=simulation.error_message,
        log_path=simulation.log_path,
        result_path=simulation.result_path,
        started_at=simulation.started_at.isoformat() if simulation.started_at else None,
        completed_at=simulation.completed_at.isoformat() if simulation.completed_at else None,
        created_at=simulation.created_at.isoformat(),
        updated_at=simulation.updated_at.isoformat(),
    )


@router.patch("/{simulation_id}", response_model=SimulationResponse)
async def update_simulation(
    simulation_id: UUID,
    simulation_data: SimulationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update simulation (only if pending or draft)."""
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(simulation_id))
    
    # Check write access
    if not _check_project_write_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    # Only allow updates if simulation is not running/completed
    if simulation.status in [SimulationStatus.RUNNING, SimulationStatus.COMPLETED]:
        raise ValidationError("Cannot update running or completed simulation")
    
    # Update fields
    update_data = simulation_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(simulation, field, value)
    
    simulation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(simulation)
    
    return SimulationResponse(
        id=str(simulation.id),
        name=simulation.name,
        description=simulation.description,
        project_id=str(simulation.project_id),
        mesh_id=str(simulation.mesh_id),
        solver_type=simulation.solver_type,
        status=simulation.status,
        progress=simulation.progress,
        current_iteration=simulation.current_iteration,
        max_iterations=simulation.max_iterations,
        solver_config=simulation.solver_config,
        boundary_conditions=simulation.boundary_conditions,
        initial_conditions=simulation.initial_conditions,
        solver_settings=simulation.solver_settings,
        max_runtime_hours=simulation.max_runtime_hours,
        priority=simulation.priority,
        cpu_hours=simulation.cpu_hours,
        memory_peak_mb=simulation.memory_peak_mb,
        disk_usage_bytes=simulation.disk_usage_bytes,
        result_size=simulation.result_size,
        error_message=simulation.error_message,
        log_path=simulation.log_path,
        result_path=simulation.result_path,
        started_at=simulation.started_at.isoformat() if simulation.started_at else None,
        completed_at=simulation.completed_at.isoformat() if simulation.completed_at else None,
        created_at=simulation.created_at.isoformat(),
        updated_at=simulation.updated_at.isoformat(),
    )


@router.delete("/{simulation_id}")
async def delete_simulation(
    simulation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete simulation."""
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(simulation_id))
    
    # Check write access
    if not _check_project_write_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    # Don't allow deletion of running simulations
    if simulation.status == SimulationStatus.RUNNING:
        raise ValidationError("Cannot delete running simulation. Stop it first.")
    
    await db.delete(simulation)
    await db.commit()
    
    return {"message": "Simulation deleted"}


@router.post("/{simulation_id}/run")
async def run_simulation(
    simulation_id: UUID,
    run_request: SimulationRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Start a simulation run."""
    result = await db.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.project),
            selectinload(Simulation.mesh),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(simulation_id))
    
    # Check write access
    if not _check_project_write_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    # Check if simulation can be run
    if simulation.status == SimulationStatus.RUNNING:
        raise ValidationError("Simulation is already running")
    
    if simulation.status == SimulationStatus.COMPLETED and not run_request.restart:
        raise ValidationError("Simulation already completed. Use restart=true to re-run.")
    
    # Start simulation in background
    simulation_service = SimulationService(db)
    background_tasks.add_task(
        simulation_service.run_simulation,
        simulation_id,
        restart=run_request.restart,
        overwrite=run_request.overwrite,
    )
    
    return {"message": "Simulation started", "simulation_id": str(simulation_id)}


@router.post("/{simulation_id}/stop")
async def stop_simulation(
    simulation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Stop a running simulation."""
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(simulation_id))
    
    # Check write access
    if not _check_project_write_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if simulation.status != SimulationStatus.RUNNING:
        raise ValidationError("Simulation is not running")
    
    # Stop simulation
    simulation_service = SimulationService(db)
    await simulation_service.stop_simulation(simulation_id)
    
    return {"message": "Simulation stop requested"}


@router.get("/{simulation_id}/status", response_model=SimulationStatusResponse)
async def get_simulation_status(
    simulation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get real-time simulation status."""
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(simulation_id))
    
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Estimate completion time
    estimated_completion = None
    if simulation.status == SimulationStatus.RUNNING and simulation.progress > 0:
        elapsed = (datetime.utcnow() - simulation.started_at).total_seconds() / 3600
        estimated_total = elapsed / (simulation.progress / 100)
        remaining = estimated_total - elapsed
        estimated_completion = (datetime.utcnow() + timedelta(hours=remaining)).isoformat()
    
    return SimulationStatusResponse(
        id=str(simulation.id),
        status=simulation.status,
        progress=simulation.progress,
        current_iteration=simulation.current_iteration,
        max_iterations=simulation.max_iterations,
        cpu_hours=simulation.cpu_hours,
        memory_peak_mb=simulation.memory_peak_mb,
        error_message=simulation.error_message,
        started_at=simulation.started_at.isoformat() if simulation.started_at else None,
        estimated_completion=estimated_completion,
    )


@router.get("/{simulation_id}/logs")
async def get_simulation_logs(
    simulation_id: UUID,
    tail: int = Query(100, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get simulation logs."""
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(simulation_id))
    
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Read log file
    if not simulation.log_path:
        return {"logs": [], "message": "No logs available yet"}
    
    try:
        import os
        if os.path.exists(simulation.log_path):
            with open(simulation.log_path, 'r') as f:
                lines = f.readlines()
                logs = lines[-tail:] if len(lines) > tail else lines
        else:
            logs = []
    except Exception as e:
        logs = [f"Error reading logs: {str(e)}"]
    
    return {"logs": logs}


@router.get("/{simulation_id}/results")
async def get_simulation_results(
    simulation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get simulation results metadata."""
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(simulation_id))
    
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    if simulation.status != SimulationStatus.COMPLETED:
        raise ValidationError("Simulation not completed yet")
    
    if not simulation.result_path:
        raise NotFoundError("Results", "No results available")
    
    # Return results metadata
    import os
    result_files = []
    if os.path.exists(simulation.result_path):
        for root, dirs, files in os.walk(simulation.result_path):
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, simulation.result_path)
                result_files.append({
                    "name": file,
                    "path": rel_path,
                    "size": os.path.getsize(filepath),
                    "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                })
    
    return {
        "simulation_id": str(simulation.id),
        "result_path": simulation.result_path,
        "result_size": simulation.result_size,
        "files": result_files,
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


from datetime import timedelta