"""
Solver configuration and execution routes for CFD Backend.
"""

from typing import Optional, List, Dict, Any
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
from cfd_backend.models.solver import SolverConfig, SolverType, SolverStatus
from cfd_backend.models.project import Project, ProjectStatus
from cfd_backend.models.simulation import Simulation, SimulationStatus
from cfd_backend.models.user import User, UserRole
from cfd_backend.api.v1.auth import get_current_active_user
from cfd_backend.services.solver_service import SolverService

router = APIRouter()


class SolverConfigCreate(BaseModel):
    """Solver configuration creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: UUID
    simulation_id: Optional[UUID] = None
    solver_type: SolverType = SolverType.OPENFOAM
    solver_version: str = "v11"
    case_directory: Optional[str] = None
    control_dict: Dict[str, Any] = Field(default_factory=dict)
    fv_schemes: Dict[str, Any] = Field(default_factory=dict)
    fv_solution: Dict[str, Any] = Field(default_factory=dict)
    transport_properties: Dict[str, Any] = Field(default_factory=dict)
    turbulence_properties: Dict[str, Any] = Field(default_factory=dict)
    boundary_conditions: List[Dict[str, Any]] = Field(default_factory=list)
    initial_conditions: Dict[str, Any] = Field(default_factory=dict)
    solver_parameters: Dict[str, Any] = Field(default_factory=dict)
    parallel: bool = False
    num_processors: int = 1
    decomposition_method: str = "scotch"


class SolverConfigUpdate(BaseModel):
    """Solver configuration update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    control_dict: Optional[Dict[str, Any]] = None
    fv_schemes: Optional[Dict[str, Any]] = None
    fv_solution: Optional[Dict[str, Any]] = None
    transport_properties: Optional[Dict[str, Any]] = None
    turbulence_properties: Optional[Dict[str, Any]] = None
    boundary_conditions: Optional[List[Dict[str, Any]]] = None
    initial_conditions: Optional[Dict[str, Any]] = None
    solver_parameters: Optional[Dict[str, Any]] = None
    parallel: Optional[bool] = None
    num_processors: Optional[int] = None
    decomposition_method: Optional[str] = None


class SolverConfigResponse(BaseModel):
    """Solver configuration response model."""
    id: str
    name: str
    description: Optional[str]
    project_id: str
    simulation_id: Optional[str]
    solver_type: SolverType
    solver_version: str
    case_directory: Optional[str]
    control_dict: Dict[str, Any]
    fv_schemes: Dict[str, Any]
    fv_solution: Dict[str, Any]
    transport_properties: Dict[str, Any]
    turbulence_properties: Dict[str, Any]
    boundary_conditions: List[Dict[str, Any]]
    initial_conditions: Dict[str, Any]
    solver_parameters: Dict[str, Any]
    parallel: bool
    num_processors: int
    decomposition_method: str
    status: SolverStatus
    last_run_at: Optional[str]
    last_run_duration: Optional[float]
    last_run_log: Optional[str]
    created_at: str
    updated_at: str


class SolverConfigListResponse(BaseModel):
    """Solver configuration list response with pagination."""
    configs: List[SolverConfigResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SolverRunRequest(BaseModel):
    """Solver run request."""
    config_id: UUID
    simulation_id: Optional[UUID] = None
    overwrite: bool = False
    parameters: Optional[Dict[str, Any]] = None


class SolverRunResponse(BaseModel):
    """Solver run response."""
    run_id: str
    config_id: str
    simulation_id: Optional[str]
    status: SolverStatus
    started_at: str
    message: str


class SolverStatusResponse(BaseModel):
    """Solver status response."""
    run_id: str
    config_id: str
    simulation_id: Optional[str]
    status: SolverStatus
    progress: float
    current_iteration: int
    max_iterations: int
    residuals: Dict[str, float]
    started_at: str
    updated_at: str
    estimated_remaining: Optional[float]
    log_tail: List[str]


class SolverLogResponse(BaseModel):
    """Solver log response."""
    run_id: str
    logs: List[str]
    total_lines: int
    page: int
    page_size: int


class SolverTemplateResponse(BaseModel):
    """Solver template response."""
    id: str
    name: str
    description: str
    solver_type: SolverType
    category: str
    template_config: Dict[str, Any]
    required_parameters: List[str]
    optional_parameters: List[str]


@router.get("", response_model=SolverConfigListResponse)
async def list_solver_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[UUID] = None,
    simulation_id: Optional[UUID] = None,
    solver_type: Optional[SolverType] = None,
    status: Optional[SolverStatus] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(name|created_at|updated_at|solver_type|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List solver configurations with pagination and filters."""
    query = select(SolverConfig).options(
        selectinload(SolverConfig.project),
        selectinload(SolverConfig.simulation),
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
        query = query.where(SolverConfig.project_id == project_id)
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
            query = query.where(SolverConfig.project_id.in_(accessible_project_ids))
    
    if simulation_id:
        query = query.where(SolverConfig.simulation_id == simulation_id)
    
    if solver_type:
        query = query.where(SolverConfig.solver_type == solver_type)
    
    if status:
        query = query.where(SolverConfig.status == status)
    
    if search:
        query = query.where(
            or_(
                SolverConfig.name.ilike(f"%{search}%"),
                SolverConfig.description.ilike(f"%{search}%"),
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply sorting
    sort_column = getattr(SolverConfig, sort_by, SolverConfig.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    configs = result.scalars().all()
    
    return SolverConfigListResponse(
        configs=[
            SolverConfigResponse(
                id=str(c.id),
                name=c.name,
                description=c.description,
                project_id=str(c.project_id),
                simulation_id=str(c.simulation_id) if c.simulation_id else None,
                solver_type=c.solver_type,
                solver_version=c.solver_version,
                case_directory=c.case_directory,
                control_dict=c.control_dict,
                fv_schemes=c.fv_schemes,
                fv_solution=c.fv_solution,
                transport_properties=c.transport_properties,
                turbulence_properties=c.turbulence_properties,
                boundary_conditions=c.boundary_conditions,
                initial_conditions=c.initial_conditions,
                solver_parameters=c.solver_parameters,
                parallel=c.parallel,
                num_processors=c.num_processors,
                decomposition_method=c.decomposition_method,
                status=c.status,
                last_run_at=c.last_run_at.isoformat() if c.last_run_at else None,
                last_run_duration=c.last_run_duration,
                last_run_log=c.last_run_log,
                created_at=c.created_at.isoformat(),
                updated_at=c.updated_at.isoformat(),
            )
            for c in configs
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=SolverConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_solver_config(
    config_data: SolverConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new solver configuration."""
    # Verify project access
    project_result = await db.execute(select(Project).where(Project.id == config_data.project_id))
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(config_data.project_id))
    
    if not _check_project_write_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied to project",
        )
    
    # Verify simulation if provided
    if config_data.simulation_id:
        sim_result = await db.execute(
            select(Simulation)
            .options(selectinload(Simulation.project))
            .where(Simulation.id == config_data.simulation_id)
        )
        simulation = sim_result.scalar_one_or_none()
        
        if not simulation:
            raise NotFoundError("Simulation", str(config_data.simulation_id))
        
        if simulation.project_id != config_data.project_id:
            raise ValidationError("Simulation does not belong to the specified project")
    
    # Create solver config
    config = SolverConfig(
        name=config_data.name,
        description=config_data.description,
        project_id=config_data.project_id,
        simulation_id=config_data.simulation_id,
        solver_type=config_data.solver_type,
        solver_version=config_data.solver_version,
        case_directory=config_data.case_directory,
        control_dict=config_data.control_dict,
        fv_schemes=config_data.fv_schemes,
        fv_solution=config_data.fv_solution,
        transport_properties=config_data.transport_properties,
        turbulence_properties=config_data.turbulence_properties,
        boundary_conditions=config_data.boundary_conditions,
        initial_conditions=config_data.initial_conditions,
        solver_parameters=config_data.solver_parameters,
        parallel=config_data.parallel,
        num_processors=config_data.num_processors,
        decomposition_method=config_data.decomposition_method,
        status=SolverStatus.READY,
    )
    
    db.add(config)
    await db.commit()
    await db.refresh(config)
    
    return SolverConfigResponse(
        id=str(config.id),
        name=config.name,
        description=config.description,
        project_id=str(config.project_id),
        simulation_id=str(config.simulation_id) if config.simulation_id else None,
        solver_type=config.solver_type,
        solver_version=config.solver_version,
        case_directory=config.case_directory,
        control_dict=config.control_dict,
        fv_schemes=config.fv_schemes,
        fv_solution=config.fv_solution,
        transport_properties=config.transport_properties,
        turbulence_properties=config.turbulence_properties,
        boundary_conditions=config.boundary_conditions,
        initial_conditions=config.initial_conditions,
        solver_parameters=config.solver_parameters,
        parallel=config.parallel,
        num_processors=config.num_processors,
        decomposition_method=config.decomposition_method,
        status=config.status,
        last_run_at=config.last_run_at.isoformat() if config.last_run_at else None,
        last_run_duration=config.last_run_duration,
        last_run_log=config.last_run_log,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.get("/templates", response_model=List[SolverTemplateResponse])
async def list_solver_templates(
    solver_type: Optional[SolverType] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List available solver templates."""
    # Return built-in templates
    templates = [
        SolverTemplateResponse(
            id="simpleFoam",
            name="simpleFoam",
            description="Steady-state incompressible flow solver",
            solver_type=SolverType.OPENFOAM,
            category="incompressible",
            template_config={
                "solver": "simpleFoam",
                "control_dict": {
                    "application": "simpleFoam",
                    "startFrom": "startTime",
                    "startTime": 0,
                    "stopAt": "endTime",
                    "endTime": 1000,
                    "deltaT": 1,
                    "writeControl": "timeStep",
                    "writeInterval": 100,
                    "purgeWrite": 0,
                    "writeFormat": "ascii",
                    "writePrecision": 6,
                    "writeCompression": "off",
                    "timeFormat": "general",
                    "timePrecision": 6,
                    "runTimeModifiable": True,
                },
                "fv_schemes": {
                    "ddtSchemes": {"default": "steadyState"},
                    "gradSchemes": {"default": "Gauss linear", "grad(p)": "Gauss linear"},
                    "divSchemes": {
                        "default": "none",
                        "div(phi,U)": "Gauss upwind",
                        "div(phi,k)": "Gauss upwind",
                        "div(phi,epsilon)": "Gauss upwind",
                        "div(phi,omega)": "Gauss upwind",
                        "div((nuEff*dev2(T(grad(U)))))": "Gauss linear",
                    },
                    "laplacianSchemes": {"default": "Gauss linear corrected"},
                    "interpolationSchemes": {"default": "linear"},
                    "snGradSchemes": {"default": "corrected"},
                },
                "fv_solution": {
                    "solvers": {
                        "p": {"solver": "GAMG", "tolerance": 1e-06, "relTol": 0.1, "smoother": "GaussSeidel"},
                        "U": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "k": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "epsilon": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "omega": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                    },
                    "SIMPLE": {"nNonOrthogonalCorrectors": 2, "consistent": True},
                    "relaxationFactors": {
                        "fields": {"p": 0.3, "U": 0.7, "k": 0.7, "epsilon": 0.7, "omega": 0.7},
                        "equations": {"U": 0.7, "k": 0.7, "epsilon": 0.7, "omega": 0.7},
                    },
                },
            },
            required_parameters=["mesh", "boundary_conditions"],
            optional_parameters=["turbulence_model", "relaxation_factors"],
        ),
        SolverTemplateResponse(
            id="pimpleFoam",
            name="pimpleFoam",
            description="Transient incompressible flow solver",
            solver_type=SolverType.OPENFOAM,
            category="incompressible",
            template_config={
                "solver": "pimpleFoam",
                "control_dict": {
                    "application": "pimpleFoam",
                    "startFrom": "startTime",
                    "startTime": 0,
                    "stopAt": "endTime",
                    "endTime": 10,
                    "deltaT": 0.01,
                    "writeControl": "timeStep",
                    "writeInterval": 10,
                    "purgeWrite": 0,
                    "writeFormat": "ascii",
                    "writePrecision": 6,
                    "writeCompression": "off",
                    "timeFormat": "general",
                    "timePrecision": 6,
                    "runTimeModifiable": True,
                },
                "fv_schemes": {
                    "ddtSchemes": {"default": "Euler"},
                    "gradSchemes": {"default": "Gauss linear", "grad(p)": "Gauss linear"},
                    "divSchemes": {
                        "default": "none",
                        "div(phi,U)": "Gauss linearUpwind grad(U)",
                        "div(phi,k)": "Gauss linearUpwind grad(k)",
                        "div(phi,epsilon)": "Gauss linearUpwind grad(epsilon)",
                        "div(phi,omega)": "Gauss linearUpwind grad(omega)",
                        "div((nuEff*dev2(T(grad(U)))))": "Gauss linear",
                    },
                    "laplacianSchemes": {"default": "Gauss linear corrected"},
                    "interpolationSchemes": {"default": "linear"},
                    "snGradSchemes": {"default": "corrected"},
                },
                "fv_solution": {
                    "solvers": {
                        "p": {"solver": "GAMG", "tolerance": 1e-06, "relTol": 0.1, "smoother": "GaussSeidel"},
                        "U": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "k": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "epsilon": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "omega": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                    },
                    "PIMPLE": {
                        "momentumPredictor": True,
                        "nOuterCorrectors": 2,
                        "nCorrectors": 2,
                        "nNonOrthogonalCorrectors": 1,
                    },
                    "relaxationFactors": {
                        "fields": {"p": 0.3, "U": 0.7, "k": 0.7, "epsilon": 0.7, "omega": 0.7},
                        "equations": {"U": 0.7, "k": 0.7, "epsilon": 0.7, "omega": 0.7},
                    },
                },
            },
            required_parameters=["mesh", "boundary_conditions", "initial_conditions"],
            optional_parameters=["turbulence_model", "time_step", "relaxation_factors"],
        ),
        SolverTemplateResponse(
            id="rhoSimpleFoam",
            name="rhoSimpleFoam",
            description="Steady-state compressible flow solver",
            solver_type=SolverType.OPENFOAM,
            category="compressible",
            template_config={
                "solver": "rhoSimpleFoam",
                "control_dict": {
                    "application": "rhoSimpleFoam",
                    "startFrom": "startTime",
                    "startTime": 0,
                    "stopAt": "endTime",
                    "endTime": 1000,
                    "deltaT": 1,
                    "writeControl": "timeStep",
                    "writeInterval": 100,
                    "purgeWrite": 0,
                    "writeFormat": "ascii",
                    "writePrecision": 6,
                    "writeCompression": "off",
                    "timeFormat": "general",
                    "timePrecision": 6,
                    "runTimeModifiable": True,
                },
                "fv_schemes": {
                    "ddtSchemes": {"default": "steadyState"},
                    "gradSchemes": {"default": "Gauss linear", "grad(p)": "Gauss linear"},
                    "divSchemes": {
                        "default": "none",
                        "div(phi,U)": "Gauss upwind",
                        "div(phi,k)": "Gauss upwind",
                        "div(phi,epsilon)": "Gauss upwind",
                        "div(phi,omega)": "Gauss upwind",
                        "div(phi,h)": "Gauss upwind",
                        "div((nuEff*dev2(T(grad(U)))))": "Gauss linear",
                    },
                    "laplacianSchemes": {"default": "Gauss linear corrected"},
                    "interpolationSchemes": {"default": "linear"},
                    "snGradSchemes": {"default": "corrected"},
                },
                "fv_solution": {
                    "solvers": {
                        "p": {"solver": "GAMG", "tolerance": 1e-06, "relTol": 0.1, "smoother": "GaussSeidel"},
                        "U": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "k": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "epsilon": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "omega": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                        "h": {"solver": "smoothSolver", "smoother": "GaussSeidel", "tolerance": 1e-05, "relTol": 0.1},
                    },
                    "SIMPLE": {"nNonOrthogonalCorrectors": 2, "consistent": True},
                    "relaxationFactors": {
                        "fields": {"p": 0.3, "U": 0.7, "k": 0.7, "epsilon": 0.7, "omega": 0.7, "h": 0.7},
                        "equations": {"U": 0.7, "k": 0.7, "epsilon": 0.7, "omega": 0.7, "h": 0.7},
                    },
                },
            },
            required_parameters=["mesh", "boundary_conditions", "thermophysical_properties"],
            optional_parameters=["turbulence_model", "relaxation_factors"],
        ),
    ]
    
    if solver_type:
        templates = [t for t in templates if t.solver_type == solver_type]
    
    if category:
        templates = [t for t in templates if t.category == category]
    
    return templates


@router.get("/{config_id}", response_model=SolverConfigResponse)
async def get_solver_config(
    config_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get solver configuration by ID."""
    result = await db.execute(
        select(SolverConfig)
        .options(
            selectinload(SolverConfig.project),
            selectinload(SolverConfig.simulation),
        )
        .where(SolverConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise NotFoundError("SolverConfig", str(config_id))
    
    if not _check_project_access(config.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to solver configuration",
        )
    
    return SolverConfigResponse(
        id=str(config.id),
        name=config.name,
        description=config.description,
        project_id=str(config.project_id),
        simulation_id=str(config.simulation_id) if config.simulation_id else None,
        solver_type=config.solver_type,
        solver_version=config.solver_version,
        case_directory=config.case_directory,
        control_dict=config.control_dict,
        fv_schemes=config.fv_schemes,
        fv_solution=config.fv_solution,
        transport_properties=config.transport_properties,
        turbulence_properties=config.turbulence_properties,
        boundary_conditions=config.boundary_conditions,
        initial_conditions=config.initial_conditions,
        solver_parameters=config.solver_parameters,
        parallel=config.parallel,
        num_processors=config.num_processors,
        decomposition_method=config.decomposition_method,
        status=config.status,
        last_run_at=config.last_run_at.isoformat() if config.last_run_at else None,
        last_run_duration=config.last_run_duration,
        last_run_log=config.last_run_log,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.patch("/{config_id}", response_model=SolverConfigResponse)
async def update_solver_config(
    config_id: UUID,
    config_data: SolverConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update solver configuration."""
    result = await db.execute(
        select(SolverConfig)
        .options(selectinload(SolverConfig.project))
        .where(SolverConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise NotFoundError("SolverConfig", str(config_id))
    
    if not _check_project_write_access(config.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    config.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(config)
    
    return SolverConfigResponse(
        id=str(config.id),
        name=config.name,
        description=config.description,
        project_id=str(config.project_id),
        simulation_id=str(config.simulation_id) if config.simulation_id else None,
        solver_type=config.solver_type,
        solver_version=config.solver_version,
        case_directory=config.case_directory,
        control_dict=config.control_dict,
        fv_schemes=config.fv_schemes,
        fv_solution=config.fv_solution,
        transport_properties=config.transport_properties,
        turbulence_properties=config.turbulence_properties,
        boundary_conditions=config.boundary_conditions,
        initial_conditions=config.initial_conditions,
        solver_parameters=config.solver_parameters,
        parallel=config.parallel,
        num_processors=config.num_processors,
        decomposition_method=config.decomposition_method,
        status=config.status,
        last_run_at=config.last_run_at.isoformat() if config.last_run_at else None,
        last_run_duration=config.last_run_duration,
        last_run_log=config.last_run_log,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.delete("/{config_id}")
async def delete_solver_config(
    config_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete solver configuration."""
    result = await db.execute(
        select(SolverConfig)
        .options(selectinload(SolverConfig.project))
        .where(SolverConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise NotFoundError("SolverConfig", str(config_id))
    
    if not _check_project_write_access(config.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    await db.delete(config)
    await db.commit()
    
    return {"message": "Solver configuration deleted"}


@router.post("/{config_id}/run", response_model=SolverRunResponse)
async def run_solver(
    config_id: UUID,
    run_request: SolverRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Run solver with configuration."""
    result = await db.execute(
        select(SolverConfig)
        .options(
            selectinload(SolverConfig.project),
            selectinload(SolverConfig.simulation),
        )
        .where(SolverConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise NotFoundError("SolverConfig", str(config_id))
    
    if not _check_project_write_access(config.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if config.status == SolverStatus.RUNNING:
        raise ValidationError("Solver already running")
    
    # Update config with run parameters
    if run_request.parameters:
        config.solver_parameters.update(run_request.parameters)
    
    config.status = SolverStatus.PREPARING
    config.updated_at = datetime.utcnow()
    await db.commit()
    
    # Run solver in background
    solver_service = SolverService(db)
    run_id = await solver_service.run_solver(
        config_id,
        simulation_id=run_request.simulation_id,
        overwrite=run_request.overwrite,
    )
    
    return SolverRunResponse(
        run_id=run_id,
        config_id=str(config_id),
        simulation_id=str(run_request.simulation_id) if run_request.simulation_id else None,
        status=SolverStatus.RUNNING,
        started_at=datetime.utcnow().isoformat(),
        message="Solver started",
    )


@router.post("/{config_id}/stop")
async def stop_solver(
    config_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Stop running solver."""
    result = await db.execute(
        select(SolverConfig)
        .options(selectinload(SolverConfig.project))
        .where(SolverConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise NotFoundError("SolverConfig", str(config_id))
    
    if not _check_project_write_access(config.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if config.status != SolverStatus.RUNNING:
        raise ValidationError("Solver not running")
    
    solver_service = SolverService(db)
    await solver_service.stop_solver(config_id)
    
    return {"message": "Solver stop requested"}


@router.get("/{config_id}/status", response_model=SolverStatusResponse)
async def get_solver_status(
    config_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get solver run status."""
    result = await db.execute(
        select(SolverConfig)
        .options(selectinload(SolverConfig.project))
        .where(SolverConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise NotFoundError("SolverConfig", str(config_id))
    
    if not _check_project_access(config.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    solver_service = SolverService(db)
    status_info = await solver_service.get_solver_status(config_id)
    
    return SolverStatusResponse(
        run_id=status_info["run_id"],
        config_id=str(config_id),
        simulation_id=str(status_info["simulation_id"]) if status_info.get("simulation_id") else None,
        status=status_info["status"],
        progress=status_info["progress"],
        current_iteration=status_info["current_iteration"],
        max_iterations=status_info["max_iterations"],
        residuals=status_info["residuals"],
        started_at=status_info["started_at"],
        updated_at=status_info["updated_at"],
        estimated_remaining=status_info.get("estimated_remaining"),
        log_tail=status_info.get("log_tail", []),
    )


@router.get("/{config_id}/logs", response_model=SolverLogResponse)
async def get_solver_logs(
    config_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get solver logs."""
    result = await db.execute(
        select(SolverConfig)
        .options(selectinload(SolverConfig.project))
        .where(SolverConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise NotFoundError("SolverConfig", str(config_id))
    
    if not _check_project_access(config.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    solver_service = SolverService(db)
    logs = await solver_service.get_solver_logs(config_id, page, page_size)
    
    return SolverLogResponse(
        run_id=logs["run_id"],
        logs=logs["logs"],
        total_lines=logs["total_lines"],
        page=page,
        page_size=page_size,
    )


@router.post("/{config_id}/decompose")
async def decompose_case(
    config_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Decompose case for parallel run."""
    result = await db.execute(
        select(SolverConfig)
        .options(selectinload(SolverConfig.project))
        .where(SolverConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise NotFoundError("SolverConfig", str(config_id))
    
    if not _check_project_write_access(config.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if not config.parallel:
        raise ValidationError("Parallel not enabled for this configuration")
    
    solver_service = SolverService(db)
    await solver_service.decompose_case(config_id)
    
    return {"message": "Case decomposed", "num_processors": config.num_processors}


@router.post("/{config_id}/reconstruct")
async def reconstruct_case(
    config_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Reconstruct case after parallel run."""
    result = await db.execute(
        select(SolverConfig)
        .options(selectinload(SolverConfig.project))
        .where(SolverConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise NotFoundError("SolverConfig", str(config_id))
    
    if not _check_project_write_access(config.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    solver_service = SolverService(db)
    await solver_service.reconstruct_case(config_id)
    
    return {"message": "Case reconstructed"}


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