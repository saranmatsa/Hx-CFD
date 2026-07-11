"""
Optimization and parameter study routes for CFD Backend.
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
from cfd_backend.models.simulation import Simulation, SimulationStatus
from cfd_backend.models.project import Project, ProjectStatus
from cfd_backend.models.user import User, UserRole
from cfd_backend.api.v1.auth import get_current_active_user
from cfd_backend.services.optimization_service import OptimizationService

router = APIRouter()


class OptimizationType(str, Enum):
    """Optimization type enumeration."""
    PARAMETER_SWEEP = "parameter_sweep"
    GRADIENT_BASED = "gradient_based"
    GENETIC_ALGORITHM = "genetic_algorithm"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    SURROGATE_MODEL = "surrogate_model"
    MULTI_OBJECTIVE = "multi_objective"
    ADJOINT = "adjoint"
    TOPOLOGY = "topology"
    SHAPE = "shape"


class OptimizationStatus(str, Enum):
    """Optimization status enumeration."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ParameterType(str, Enum):
    """Parameter type enumeration."""
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    CATEGORICAL = "categorical"
    INTEGER = "integer"


class ObjectiveType(str, Enum):
    """Objective type enumeration."""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    TARGET = "target"


class SurrogateModelType(str, Enum):
    """Surrogate model type enumeration."""
    KRIGING = "kriging"
    RADIAL_BASIS_FUNCTION = "radial_basis_function"
    POLYNOMIAL_CHAOS = "polynomial_chaos"
    GAUSSIAN_PROCESS = "gaussian_process"
    NEURAL_NETWORK = "neural_network"
    RANDOM_FOREST = "random_forest"
    SUPPORT_VECTOR_REGRESSION = "support_vector_regression"


class ParameterDefinition(BaseModel):
    """Parameter definition model."""
    name: str = Field(..., min_length=1, max_length=100)
    parameter_type: ParameterType
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    values: Optional[List[Any]] = None  # For discrete/categorical
    default: Optional[Any] = None
    description: Optional[str] = None
    units: Optional[str] = None


class ObjectiveDefinition(BaseModel):
    """Objective definition model."""
    name: str = Field(..., min_length=1, max_length=100)
    objective_type: ObjectiveType
    target_value: Optional[float] = None
    weight: float = Field(1.0, gt=0.0)
    description: Optional[str] = None
    expression: Optional[str] = None  # For computed objectives


class ConstraintDefinition(BaseModel):
    """Constraint definition model."""
    name: str = Field(..., min_length=1, max_length=100)
    expression: str  # Constraint expression
    constraint_type: str = Field("inequality", pattern="^(equality|inequality)$")
    tolerance: float = 1e-6
    description: Optional[str] = None


class OptimizationCreate(BaseModel):
    """Optimization study creation model."""
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    optimization_type: OptimizationType
    base_simulation_id: UUID
    parameters: List[ParameterDefinition]
    objectives: List[ObjectiveDefinition]
    constraints: List[ConstraintDefinition] = Field(default_factory=list)
    max_iterations: int = Field(100, ge=1, le=10000)
    max_evaluations: int = Field(1000, ge=1, le=100000)
    population_size: Optional[int] = Field(None, ge=2, le=1000)
    convergence_tolerance: float = Field(1e-6, gt=0.0)
    surrogate_model: Optional[SurrogateModelType] = None
    acquisition_function: Optional[str] = None
    initial_samples: int = Field(10, ge=1, le=100)
    parallel_evaluations: int = Field(1, ge=1, le=100)
    seed: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OptimizationUpdate(BaseModel):
    """Optimization study update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    max_iterations: Optional[int] = Field(None, ge=1, le=10000)
    max_evaluations: Optional[int] = Field(None, ge=1, le=100000)
    convergence_tolerance: Optional[float] = Field(None, gt=0.0)
    metadata: Optional[Dict[str, Any]] = None


class OptimizationResponse(BaseModel):
    """Optimization study response model."""
    id: str
    project_id: str
    name: str
    description: Optional[str]
    optimization_type: OptimizationType
    base_simulation_id: str
    status: OptimizationStatus
    parameters: List[Dict[str, Any]]
    objectives: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    max_iterations: int
    max_evaluations: int
    current_iteration: int
    current_evaluations: int
    best_objectives: Dict[str, float]
    best_parameters: Dict[str, Any]
    convergence_history: List[Dict[str, Any]]
    surrogate_model: Optional[SurrogateModelType]
    acquisition_function: Optional[str]
    initial_samples: int
    parallel_evaluations: int
    seed: Optional[int]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


class OptimizationListResponse(BaseModel):
    """Optimization study list response with pagination."""
    optimizations: List[OptimizationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OptimizationRunRequest(BaseModel):
    """Optimization run request model."""
    resume: bool = False


class OptimizationRunResponse(BaseModel):
    """Optimization run response model."""
    optimization_id: str
    status: OptimizationStatus
    message: str


class EvaluationCreate(BaseModel):
    """Evaluation creation model."""
    optimization_id: UUID
    parameters: Dict[str, Any]
    simulation_id: Optional[UUID] = None


class EvaluationResponse(BaseModel):
    """Evaluation response model."""
    id: str
    optimization_id: str
    parameters: Dict[str, Any]
    objectives: Dict[str, float]
    constraints: Dict[str, float]
    simulation_id: Optional[str]
    status: str
    iteration: int
    evaluation_time: Optional[float]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]


class EvaluationListResponse(BaseModel):
    """Evaluation list response with pagination."""
    evaluations: List[EvaluationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SurrogateModelCreate(BaseModel):
    """Surrogate model creation model."""
    optimization_id: UUID
    model_type: SurrogateModelType
    training_data: Optional[Dict[str, Any]] = None
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    cross_validation: bool = True
    cv_folds: int = Field(5, ge=2, le=10)


class SurrogateModelResponse(BaseModel):
    """Surrogate model response model."""
    id: str
    optimization_id: str
    model_type: SurrogateModelType
    status: str
    training_score: Optional[float]
    validation_score: Optional[float]
    hyperparameters: Dict[str, Any]
    feature_importance: Optional[Dict[str, float]]
    created_at: str
    trained_at: Optional[str]


class SurrogateModelPredictRequest(BaseModel):
    """Surrogate model prediction request."""
    model_id: UUID
    parameters: Dict[str, Any]
    return_std: bool = False


class SurrogateModelPredictResponse(BaseModel):
    """Surrogate model prediction response."""
    model_id: str
    parameters: Dict[str, Any]
    predictions: Dict[str, float]
    std_dev: Optional[Dict[str, float]]
    created_at: str


class SensitivityAnalysisRequest(BaseModel):
    """Sensitivity analysis request model."""
    optimization_id: UUID
    method: str = Field("sobol", pattern="^(sobol|morris|fast|delta)$")
    n_samples: int = Field(1000, ge=100, le=100000)
    parameters: Optional[List[str]] = None


class SensitivityAnalysisResponse(BaseModel):
    """Sensitivity analysis response model."""
    analysis_id: str
    optimization_id: str
    method: str
    n_samples: int
    first_order_indices: Dict[str, float]
    total_order_indices: Dict[str, float]
    second_order_indices: Optional[Dict[str, Dict[str, float]]]
    created_at: str


class ParetoFrontRequest(BaseModel):
    """Pareto front request model."""
    optimization_id: UUID
    objectives: List[str] = Field(..., min_items=2, max_items=5)
    n_points: int = Field(100, ge=10, le=1000)


class ParetoFrontResponse(BaseModel):
    """Pareto front response model."""
    pareto_id: str
    optimization_id: str
    objectives: List[str]
    points: List[Dict[str, Any]]
    hypervolume: Optional[float]
    created_at: str


class OptimizationExportRequest(BaseModel):
    """Optimization export request model."""
    optimization_id: UUID
    format: str = Field("csv", pattern="^(csv|json|hdf5|parquet)$")
    include_evaluations: bool = True
    include_surrogate: bool = False
    include_sensitivity: bool = False


class OptimizationExportResponse(BaseModel):
    """Optimization export response model."""
    export_id: str
    optimization_id: str
    format: str
    file_path: str
    file_size: int
    status: str
    created_at: str


class DesignOfExperimentsRequest(BaseModel):
    """Design of experiments request model."""
    optimization_id: UUID
    method: str = Field("lhs", pattern="^(lhs|sobol|halton|grid|random|factorial)$")
    n_samples: int = Field(10, ge=1, le=1000)
    parameters: Optional[List[str]] = None
    seed: Optional[int] = None


class DesignOfExperimentsResponse(BaseModel):
    """Design of experiments response model."""
    doe_id: str
    optimization_id: str
    method: str
    n_samples: int
    samples: List[Dict[str, Any]]
    created_at: str


@router.get("/optimizations", response_model=OptimizationListResponse)
async def list_optimizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[UUID] = None,
    optimization_type: Optional[OptimizationType] = None,
    status: Optional[OptimizationStatus] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(name|created_at|updated_at|optimization_type|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List optimization studies with pagination and filters."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    query = select(OptimizationStudy).options(
        selectinload(OptimizationStudy.project)
    )
    
    # Filter by project
    if project_id:
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError("Project", str(project_id))
        
        if not _check_project_access(project, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to project",
            )
        
        query = query.where(OptimizationStudy.project_id == project_id)
    
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
            query = query.where(OptimizationStudy.project_id.in_(accessible_project_ids))
    
    if optimization_type:
        query = query.where(OptimizationStudy.optimization_type == optimization_type)
    
    if status:
        query = query.where(OptimizationStudy.status == status)
    
    if search:
        query = query.where(
            or_(
                OptimizationStudy.name.ilike(f"%{search}%"),
                OptimizationStudy.description.ilike(f"%{search}%"),
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply sorting
    sort_column = getattr(OptimizationStudy, sort_by, OptimizationStudy.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    optimizations = result.scalars().all()
    
    return OptimizationListResponse(
        optimizations=[
            OptimizationResponse(
                id=str(o.id),
                project_id=str(o.project_id),
                name=o.name,
                description=o.description,
                optimization_type=o.optimization_type,
                base_simulation_id=str(o.base_simulation_id),
                status=o.status,
                parameters=o.parameters,
                objectives=o.objectives,
                constraints=o.constraints,
                max_iterations=o.max_iterations,
                max_evaluations=o.max_evaluations,
                current_iteration=o.current_iteration,
                current_evaluations=o.current_evaluations,
                best_objectives=o.best_objectives,
                best_parameters=o.best_parameters,
                convergence_history=o.convergence_history,
                surrogate_model=o.surrogate_model,
                acquisition_function=o.acquisition_function,
                initial_samples=o.initial_samples,
                parallel_evaluations=o.parallel_evaluations,
                seed=o.seed,
                metadata=o.metadata,
                created_at=o.created_at.isoformat(),
                updated_at=o.updated_at.isoformat(),
                started_at=o.started_at.isoformat() if o.started_at else None,
                completed_at=o.completed_at.isoformat() if o.completed_at else None,
            )
            for o in optimizations
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/optimizations", response_model=OptimizationResponse, status_code=status.HTTP_201_CREATED)
async def create_optimization(
    opt_data: OptimizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new optimization study."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    # Verify project access
    project_result = await db.execute(
        select(Project).where(Project.id == opt_data.project_id)
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise NotFoundError("Project", str(opt_data.project_id))
    
    if not _check_project_write_access(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied to project",
        )
    
    # Verify base simulation access
    sim_result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == opt_data.base_simulation_id)
    )
    simulation = sim_result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(opt_data.base_simulation_id))
    
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to base simulation",
        )
    
    # Validate parameters
    if not opt_data.parameters:
        raise ValidationError("At least one parameter must be defined")
    
    if not opt_data.objectives:
        raise ValidationError("At least one objective must be defined")
    
    # Validate parameter bounds
    for param in opt_data.parameters:
        if param.parameter_type == ParameterType.CONTINUOUS:
            if param.lower_bound is None or param.upper_bound is None:
                raise ValidationError(f"Continuous parameter '{param.name}' requires lower_bound and upper_bound")
            if param.lower_bound >= param.upper_bound:
                raise ValidationError(f"Parameter '{param.name}': lower_bound must be less than upper_bound")
        elif param.parameter_type in [ParameterType.DISCRETE, ParameterType.CATEGORICAL]:
            if not param.values:
                raise ValidationError(f"Parameter '{param.name}' requires values list")
    
    optimization = OptimizationStudy(
        project_id=opt_data.project_id,
        name=opt_data.name,
        description=opt_data.description,
        optimization_type=opt_data.optimization_type,
        base_simulation_id=opt_data.base_simulation_id,
        parameters=[p.model_dump() for p in opt_data.parameters],
        objectives=[o.model_dump() for o in opt_data.objectives],
        constraints=[c.model_dump() for c in opt_data.constraints],
        max_iterations=opt_data.max_iterations,
        max_evaluations=opt_data.max_evaluations,
        population_size=opt_data.population_size,
        convergence_tolerance=opt_data.convergence_tolerance,
        surrogate_model=opt_data.surrogate_model,
        acquisition_function=opt_data.acquisition_function,
        initial_samples=opt_data.initial_samples,
        parallel_evaluations=opt_data.parallel_evaluations,
        seed=opt_data.seed,
        metadata=opt_data.metadata,
        status=OptimizationStatus.PENDING,
    )
    
    db.add(optimization)
    await db.commit()
    await db.refresh(optimization)
    
    return OptimizationResponse(
        id=str(optimization.id),
        project_id=str(optimization.project_id),
        name=optimization.name,
        description=optimization.description,
        optimization_type=optimization.optimization_type,
        base_simulation_id=str(optimization.base_simulation_id),
        status=optimization.status,
        parameters=optimization.parameters,
        objectives=optimization.objectives,
        constraints=optimization.constraints,
        max_iterations=optimization.max_iterations,
        max_evaluations=optimization.max_evaluations,
        current_iteration=optimization.current_iteration,
        current_evaluations=optimization.current_evaluations,
        best_objectives=optimization.best_objectives,
        best_parameters=optimization.best_parameters,
        convergence_history=optimization.convergence_history,
        surrogate_model=optimization.surrogate_model,
        acquisition_function=optimization.acquisition_function,
        initial_samples=optimization.initial_samples,
        parallel_evaluations=optimization.parallel_evaluations,
        seed=optimization.seed,
        metadata=optimization.metadata,
        created_at=optimization.created_at.isoformat(),
        updated_at=optimization.updated_at.isoformat(),
        started_at=optimization.started_at.isoformat() if optimization.started_at else None,
        completed_at=optimization.completed_at.isoformat() if optimization.completed_at else None,
    )


@router.get("/optimizations/{optimization_id}", response_model=OptimizationResponse)
async def get_optimization(
    optimization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get optimization study by ID."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to optimization",
        )
    
    return OptimizationResponse(
        id=str(optimization.id),
        project_id=str(optimization.project_id),
        name=optimization.name,
        description=optimization.description,
        optimization_type=optimization.optimization_type,
        base_simulation_id=str(optimization.base_simulation_id),
        status=optimization.status,
        parameters=optimization.parameters,
        objectives=optimization.objectives,
        constraints=optimization.constraints,
        max_iterations=optimization.max_iterations,
        max_evaluations=optimization.max_evaluations,
        current_iteration=optimization.current_iteration,
        current_evaluations=optimization.current_evaluations,
        best_objectives=optimization.best_objectives,
        best_parameters=optimization.best_parameters,
        convergence_history=optimization.convergence_history,
        surrogate_model=optimization.surrogate_model,
        acquisition_function=optimization.acquisition_function,
        initial_samples=optimization.initial_samples,
        parallel_evaluations=optimization.parallel_evaluations,
        seed=optimization.seed,
        metadata=optimization.metadata,
        created_at=optimization.created_at.isoformat(),
        updated_at=optimization.updated_at.isoformat(),
        started_at=optimization.started_at.isoformat() if optimization.started_at else None,
        completed_at=optimization.completed_at.isoformat() if optimization.completed_at else None,
    )


@router.patch("/optimizations/{optimization_id}", response_model=OptimizationResponse)
async def update_optimization(
    optimization_id: UUID,
    opt_data: OptimizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update optimization study."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_write_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if optimization.status in [OptimizationStatus.RUNNING, OptimizationStatus.INITIALIZING]:
        raise ValidationError("Cannot update running optimization")
    
    update_data = opt_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(optimization, field, value)
    
    optimization.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(optimization)
    
    return OptimizationResponse(
        id=str(optimization.id),
        project_id=str(optimization.project_id),
        name=optimization.name,
        description=optimization.description,
        optimization_type=optimization.optimization_type,
        base_simulation_id=str(optimization.base_simulation_id),
        status=optimization.status,
        parameters=optimization.parameters,
        objectives=optimization.objectives,
        constraints=optimization.constraints,
        max_iterations=optimization.max_iterations,
        max_evaluations=optimization.max_evaluations,
        current_iteration=optimization.current_iteration,
        current_evaluations=optimization.current_evaluations,
        best_objectives=optimization.best_objectives,
        best_parameters=optimization.best_parameters,
        convergence_history=optimization.convergence_history,
        surrogate_model=optimization.surrogate_model,
        acquisition_function=optimization.acquisition_function,
        initial_samples=optimization.initial_samples,
        parallel_evaluations=optimization.parallel_evaluations,
        seed=optimization.seed,
        metadata=optimization.metadata,
        created_at=optimization.created_at.isoformat(),
        updated_at=optimization.updated_at.isoformat(),
        started_at=optimization.started_at.isoformat() if optimization.started_at else None,
        completed_at=optimization.completed_at.isoformat() if optimization.completed_at else None,
    )


@router.delete("/optimizations/{optimization_id}")
async def delete_optimization(
    optimization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete optimization study."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_write_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if optimization.status in [OptimizationStatus.RUNNING, OptimizationStatus.INITIALIZING]:
        raise ValidationError("Cannot delete running optimization")
    
    await db.delete(optimization)
    await db.commit()
    
    return {"message": "Optimization study deleted"}


@router.post("/optimizations/{optimization_id}/run", response_model=OptimizationRunResponse)
async def run_optimization(
    optimization_id: UUID,
    run_request: OptimizationRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Run optimization study."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_write_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if optimization.status == OptimizationStatus.RUNNING and not run_request.resume:
        raise ValidationError("Optimization is already running")
    
    if optimization.status == OptimizationStatus.COMPLETED and not run_request.resume:
        raise ValidationError("Optimization already completed")
    
    opt_service = OptimizationService(db)
    background_tasks.add_task(
        opt_service.run_optimization,
        optimization_id=optimization_id,
        resume=run_request.resume,
    )
    
    return OptimizationRunResponse(
        optimization_id=str(optimization_id),
        status=OptimizationStatus.INITIALIZING,
        message="Optimization started",
    )


@router.post("/optimizations/{optimization_id}/pause")
async def pause_optimization(
    optimization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Pause running optimization."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_write_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if optimization.status != OptimizationStatus.RUNNING:
        raise ValidationError("Optimization is not running")
    
    opt_service = OptimizationService(db)
    await opt_service.pause_optimization(optimization_id)
    
    return {"message": "Optimization paused"}


@router.post("/optimizations/{optimization_id}/cancel")
async def cancel_optimization(
    optimization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Cancel optimization."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_write_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    if optimization.status not in [OptimizationStatus.RUNNING, OptimizationStatus.INITIALIZING, OptimizationStatus.PAUSED]:
        raise ValidationError("Optimization cannot be cancelled")
    
    opt_service = OptimizationService(db)
    await opt_service.cancel_optimization(optimization_id)
    
    return {"message": "Optimization cancelled"}


@router.get("/optimizations/{optimization_id}/evaluations", response_model=EvaluationListResponse)
async def list_evaluations(
    optimization_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    iteration: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List optimization evaluations."""
    from cfd_backend.models.optimization import OptimizationStudy, OptimizationEvaluation
    
    # Verify optimization access
    opt_result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = opt_result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to optimization",
        )
    
    query = select(OptimizationEvaluation).where(
        OptimizationEvaluation.optimization_id == optimization_id
    )
    
    if status:
        query = query.where(OptimizationEvaluation.status == status)
    
    if iteration is not None:
        query = query.where(OptimizationEvaluation.iteration == iteration)
    
    query = query.order_by(OptimizationEvaluation.iteration, OptimizationEvaluation.created_at)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    evaluations = result.scalars().all()
    
    return EvaluationListResponse(
        evaluations=[
            EvaluationResponse(
                id=str(e.id),
                optimization_id=str(e.optimization_id),
                parameters=e.parameters,
                objectives=e.objectives,
                constraints=e.constraints,
                simulation_id=str(e.simulation_id) if e.simulation_id else None,
                status=e.status,
                iteration=e.iteration,
                evaluation_time=e.evaluation_time,
                error_message=e.error_message,
                created_at=e.created_at.isoformat(),
                completed_at=e.completed_at.isoformat() if e.completed_at else None,
            )
            for e in evaluations
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/optimizations/{optimization_id}/evaluations/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    optimization_id: UUID,
    evaluation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get optimization evaluation by ID."""
    from cfd_backend.models.optimization import OptimizationStudy, OptimizationEvaluation
    
    # Verify optimization access
    opt_result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = opt_result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to optimization",
        )
    
    eval_result = await db.execute(
        select(OptimizationEvaluation).where(
            and_(
                OptimizationEvaluation.id == evaluation_id,
                OptimizationEvaluation.optimization_id == optimization_id,
            )
        )
    )
    evaluation = eval_result.scalar_one_or_none()
    
    if not evaluation:
        raise NotFoundError("OptimizationEvaluation", str(evaluation_id))
    
    return EvaluationResponse(
        id=str(evaluation.id),
        optimization_id=str(evaluation.optimization_id),
        parameters=evaluation.parameters,
        objectives=evaluation.objectives,
        constraints=evaluation.constraints,
        simulation_id=str(evaluation.simulation_id) if evaluation.simulation_id else None,
        status=evaluation.status,
        iteration=evaluation.iteration,
        evaluation_time=evaluation.evaluation_time,
        error_message=evaluation.error_message,
        created_at=evaluation.created_at.isoformat(),
        completed_at=evaluation.completed_at.isoformat() if evaluation.completed_at else None,
    )


@router.post("/optimizations/{optimization_id}/surrogate", response_model=SurrogateModelResponse)
async def create_surrogate_model(
    optimization_id: UUID,
    surrogate_data: SurrogateModelCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create and train surrogate model."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    # Verify optimization access
    opt_result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = opt_result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_write_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    opt_service = OptimizationService(db)
    surrogate = await opt_service.create_surrogate_model(
        optimization_id=optimization_id,
        model_type=surrogate_data.model_type,
        training_data=surrogate_data.training_data,
        hyperparameters=surrogate_data.hyperparameters,
        cross_validation=surrogate_data.cross_validation,
        cv_folds=surrogate_data.cv_folds,
    )
    
    return SurrogateModelResponse(
        id=surrogate["id"],
        optimization_id=str(optimization_id),
        model_type=surrogate_data.model_type,
        status=surrogate["status"],
        training_score=surrogate.get("training_score"),
        validation_score=surrogate.get("validation_score"),
        hyperparameters=surrogate_data.hyperparameters,
        feature_importance=surrogate.get("feature_importance"),
        created_at=datetime.utcnow().isoformat(),
        trained_at=surrogate.get("trained_at"),
    )


@router.post("/surrogate/{model_id}/predict", response_model=SurrogateModelPredictResponse)
async def predict_surrogate(
    model_id: UUID,
    predict_request: SurrogateModelPredictRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Predict using surrogate model."""
    from cfd_backend.models.optimization import SurrogateModel, OptimizationStudy
    
    # Verify model access
    model_result = await db.execute(
        select(SurrogateModel)
        .options(selectinload(SurrogateModel.optimization).selectinload(OptimizationStudy.project))
        .where(SurrogateModel.id == model_id)
    )
    model = model_result.scalar_one_or_none()
    
    if not model:
        raise NotFoundError("SurrogateModel", str(model_id))
    
    if not _check_project_access(model.optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to surrogate model",
        )
    
    opt_service = OptimizationService(db)
    prediction = await opt_service.predict_surrogate(
        model_id=model_id,
        parameters=predict_request.parameters,
        return_std=predict_request.return_std,
    )
    
    return SurrogateModelPredictResponse(
        model_id=str(model_id),
        parameters=predict_request.parameters,
        predictions=prediction["predictions"],
        std_dev=prediction.get("std_dev"),
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/optimizations/{optimization_id}/sensitivity", response_model=SensitivityAnalysisResponse)
async def run_sensitivity_analysis(
    optimization_id: UUID,
    sensitivity_request: SensitivityAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Run sensitivity analysis."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    # Verify optimization access
    opt_result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = opt_result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to optimization",
        )
    
    opt_service = OptimizationService(db)
    sensitivity = await opt_service.run_sensitivity_analysis(
        optimization_id=optimization_id,
        method=sensitivity_request.method,
        n_samples=sensitivity_request.n_samples,
        parameters=sensitivity_request.parameters,
    )
    
    return SensitivityAnalysisResponse(
        analysis_id=sensitivity["analysis_id"],
        optimization_id=str(optimization_id),
        method=sensitivity_request.method,
        n_samples=sensitivity_request.n_samples,
        first_order_indices=sensitivity["first_order_indices"],
        total_order_indices=sensitivity["total_order_indices"],
        second_order_indices=sensitivity.get("second_order_indices"),
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/optimizations/{optimization_id}/pareto", response_model=ParetoFrontResponse)
async def compute_pareto_front(
    optimization_id: UUID,
    pareto_request: ParetoFrontRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Compute Pareto front for multi-objective optimization."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    # Verify optimization access
    opt_result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = opt_result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to optimization",
        )
    
    if optimization.optimization_type != OptimizationType.MULTI_OBJECTIVE:
        raise ValidationError("Pareto front only available for multi-objective optimization")
    
    opt_service = OptimizationService(db)
    pareto = await opt_service.compute_pareto_front(
        optimization_id=optimization_id,
        objectives=pareto_request.objectives,
        n_points=pareto_request.n_points,
    )
    
    return ParetoFrontResponse(
        pareto_id=pareto["pareto_id"],
        optimization_id=str(optimization_id),
        objectives=pareto_request.objectives,
        points=pareto["points"],
        hypervolume=pareto.get("hypervolume"),
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/optimizations/{optimization_id}/doe", response_model=DesignOfExperimentsResponse)
async def generate_doe(
    optimization_id: UUID,
    doe_request: DesignOfExperimentsRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate design of experiments samples."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    # Verify optimization access
    opt_result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = opt_result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_write_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    opt_service = OptimizationService(db)
    doe = await opt_service.generate_doe(
        optimization_id=optimization_id,
        method=doe_request.method,
        n_samples=doe_request.n_samples,
        parameters=doe_request.parameters,
        seed=doe_request.seed,
    )
    
    return DesignOfExperimentsResponse(
        doe_id=doe["doe_id"],
        optimization_id=str(optimization_id),
        method=doe_request.method,
        n_samples=doe_request.n_samples,
        samples=doe["samples"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/optimizations/{optimization_id}/export", response_model=OptimizationExportResponse)
async def export_optimization(
    optimization_id: UUID,
    export_request: OptimizationExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Export optimization study data."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    # Verify optimization access
    opt_result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = opt_result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to optimization",
        )
    
    opt_service = OptimizationService(db)
    export = await opt_service.export_optimization(
        optimization_id=optimization_id,
        format=export_request.format,
        include_evaluations=export_request.include_evaluations,
        include_surrogate=export_request.include_surrogate,
        include_sensitivity=export_request.include_sensitivity,
    )
    
    return OptimizationExportResponse(
        export_id=export["export_id"],
        optimization_id=str(optimization_id),
        format=export_request.format,
        file_path=export["file_path"],
        file_size=export["file_size"],
        status=export["status"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.get("/optimizations/{optimization_id}/convergence")
async def get_convergence_history(
    optimization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get optimization convergence history."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    # Verify optimization access
    opt_result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = opt_result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to optimization",
        )
    
    opt_service = OptimizationService(db)
    convergence = await opt_service.get_convergence_history(optimization_id)
    
    return convergence


@router.get("/optimizations/{optimization_id}/best")
async def get_best_solution(
    optimization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get best solution from optimization."""
    from cfd_backend.models.optimization import OptimizationStudy
    
    # Verify optimization access
    opt_result = await db.execute(
        select(OptimizationStudy)
        .options(selectinload(OptimizationStudy.project))
        .where(OptimizationStudy.id == optimization_id)
    )
    optimization = opt_result.scalar_one_or_none()
    
    if not optimization:
        raise NotFoundError("OptimizationStudy", str(optimization_id))
    
    if not _check_project_access(optimization.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to optimization",
        )
    
    opt_service = OptimizationService(db)
    best = await opt_service.get_best_solution(optimization_id)
    
    return best


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