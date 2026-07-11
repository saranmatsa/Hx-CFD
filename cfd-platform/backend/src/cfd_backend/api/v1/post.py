"""
Post-processing and results visualization routes for CFD Backend.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.core.config import get_settings
from cfd_backend.core.dependencies import get_db_session
from cfd_backend.core.exceptions import NotFoundError, ValidationError
from cfd_backend.models.simulation import Simulation, SimulationStatus
from cfd_backend.models.simulation_result import SimulationResult, ResultType, ResultStatus
from cfd_backend.models.project import Project, ProjectStatus
from cfd_backend.models.user import User, UserRole
from cfd_backend.api.v1.auth import get_current_active_user
from cfd_backend.services.post_processing_service import PostProcessingService

router = APIRouter()


class ResultType(str, Enum):
    """Result type enumeration."""
    FIELD_DATA = "field_data"
    SURFACE_DATA = "surface_data"
    LINE_DATA = "line_data"
    VOLUME_DATA = "volume_data"
    PARTICLE_TRACES = "particle_traces"
    STREAMLINES = "streamlines"
    CONTOURS = "contours"
    VECTORS = "vectors"
    ISO_SURFACES = "iso_surfaces"
    SLICES = "slices"
    PROBES = "probes"
    FORCES = "forces"
    FORCE_COEFFICIENTS = "force_coefficients"
    Y_PLUS = "y_plus"
    WALL_SHEAR_STRESS = "wall_shear_stress"
    TURBULENCE_STATISTICS = "turbulence_statistics"
    CUSTOM = "custom"


class ResultStatus(str, Enum):
    """Result status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPORTED = "exported"


class ExportFormat(str, Enum):
    """Export format enumeration."""
    VTK = "vtk"
    VTU = "vtu"
    VTP = "vtp"
    VTS = "vts"
    CSV = "csv"
    JSON = "json"
    HDF5 = "h5"
    XDMF = "xdmf"
    PNG = "png"
    JPEG = "jpg"
    PDF = "pdf"
    PARAVIEW_STATE = "pvsm"


class VisualizationType(str, Enum):
    """Visualization type enumeration."""
    CONTOUR = "contour"
    VECTOR = "vector"
    STREAMLINE = "streamline"
    PARTICLE_TRACE = "particle_trace"
    SLICE = "slice"
    ISO_SURFACE = "iso_surface"
    VOLUME_RENDER = "volume_render"
    GLYPH = "glyph"
    WARP = "warp"
    CLIP = "clip"
    THRESHOLD = "threshold"
    CALCULATOR = "calculator"


class SimulationResultCreate(BaseModel):
    """Simulation result creation model."""
    simulation_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    result_type: ResultType
    time_step: Optional[float] = None
    time_value: Optional[float] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    variables: List[str] = Field(default_factory=list)
    region: Optional[str] = None


class SimulationResultUpdate(BaseModel):
    """Simulation result update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    variables: Optional[List[str]] = None
    region: Optional[str] = None


class SimulationResultResponse(BaseModel):
    """Simulation result response model."""
    id: str
    simulation_id: str
    name: str
    description: Optional[str]
    result_type: ResultType
    status: ResultStatus
    time_step: Optional[float]
    time_value: Optional[float]
    file_path: Optional[str]
    file_size: Optional[int]
    metadata: Dict[str, Any]
    variables: List[str]
    region: Optional[str]
    min_values: Dict[str, float]
    max_values: Dict[str, float]
    created_at: str
    updated_at: str
    completed_at: Optional[str]


class SimulationResultListResponse(BaseModel):
    """Simulation result list response with pagination."""
    results: List[SimulationResultResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VisualizationRequest(BaseModel):
    """Visualization request model."""
    result_id: UUID
    visualization_type: VisualizationType
    field_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    color_map: str = "viridis"
    opacity: float = Field(1.0, ge=0.0, le=1.0)
    show_edges: bool = False
    line_width: float = 1.0
    point_size: float = 5.0


class VisualizationResponse(BaseModel):
    """Visualization response model."""
    visualization_id: str
    result_id: str
    visualization_type: VisualizationType
    field_name: str
    parameters: Dict[str, Any]
    image_data: Optional[str] = None  # Base64 encoded image
    vtk_data: Optional[str] = None  # Base64 encoded VTK data
    metadata: Dict[str, Any]
    created_at: str


class ExportRequest(BaseModel):
    """Export request model."""
    result_ids: List[UUID]
    format: ExportFormat
    options: Dict[str, Any] = Field(default_factory=dict)
    include_metadata: bool = True


class ExportResponse(BaseModel):
    """Export response model."""
    export_id: str
    format: ExportFormat
    file_path: str
    file_size: int
    status: ResultStatus
    created_at: str


class ProbeRequest(BaseModel):
    """Probe request model."""
    simulation_id: UUID
    points: List[List[float]]  # List of [x, y, z] coordinates
    fields: List[str]
    time_steps: Optional[List[float]] = None
    interpolation: str = "cellPointFace"


class ProbeResponse(BaseModel):
    """Probe response model."""
    probe_id: str
    simulation_id: str
    points: List[List[float]]
    fields: List[str]
    time_steps: List[float]
    data: Dict[str, List[List[float]]]  # field -> time_step -> point values per point
    created_at: str


class CutPlaneRequest(BaseModel):
    """Cut plane request model."""
    simulation_id: UUID
    origin: List[float] = Field(..., min_items=3, max_items=3)
    normal: List[float] = Field(..., min_items=3, max_items=3)
    fields: List[str]
    time_step: Optional[float] = None
    resolution: List[int] = Field([100, 100], min_items=2, max_items=2)


class CutPlaneResponse(BaseModel):
    """Cut plane response model."""
    cut_plane_id: str
    simulation_id: str
    origin: List[float]
    normal: List[float]
    fields: List[str]
    time_step: Optional[float]
    resolution: List[int]
    data: Dict[str, Any]  # VTK structured grid data
    bounds: List[float]
    created_at: str


class StreamlineRequest(BaseModel):
    """Streamline request model."""
    simulation_id: UUID
    seed_type: str = Field("line", pattern="^(line|plane|point|cloud)$")
    seed_points: List[List[float]]
    seed_resolution: int = 10
    field_name: str = "U"
    integration_direction: str = Field("both", pattern="^(forward|backward|both)$")
    max_steps: int = 1000
    step_size: float = 0.01
    time_step: Optional[float] = None


class StreamlineResponse(BaseModel):
    """Streamline response model."""
    streamline_id: str
    simulation_id: str
    seed_type: str
    seed_points: List[List[float]]
    field_name: str
    integration_direction: str
    max_steps: int
    step_size: float
    time_step: Optional[float]
    streamlines: List[Dict[str, Any]]  # List of streamline data
    created_at: str


class AnimationRequest(BaseModel):
    """Animation request model."""
    simulation_id: UUID
    visualization_type: VisualizationType
    field_name: str
    time_steps: List[float]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    frame_rate: int = 10
    resolution: List[int] = Field([1920, 1080], min_items=2, max_items=2)
    format: str = "mp4"


class AnimationResponse(BaseModel):
    """Animation response model."""
    animation_id: str
    simulation_id: str
    visualization_type: VisualizationType
    field_name: str
    time_steps: List[float]
    frame_rate: int
    resolution: List[int]
    format: str
    file_path: Optional[str]
    status: ResultStatus
    created_at: str


class ComparisonRequest(BaseModel):
    """Comparison request model."""
    simulation_ids: List[UUID] = Field(..., min_items=2, max_items=5)
    field_name: str
    time_step: Optional[float] = None
    comparison_type: str = Field("difference", pattern="^(difference|ratio|overlay)$")
    region: Optional[str] = None


class ComparisonResponse(BaseModel):
    """Comparison response model."""
    comparison_id: str
    simulation_ids: List[str]
    field_name: str
    time_step: Optional[float]
    comparison_type: str
    region: Optional[str]
    data: Dict[str, Any]
    statistics: Dict[str, float]
    created_at: str


class ReportRequest(BaseModel):
    """Report generation request model."""
    simulation_id: UUID
    template: str = "standard"
    sections: List[str] = Field(default_factory=list)
    include_images: bool = True
    include_tables: bool = True
    format: str = "pdf"


class ReportResponse(BaseModel):
    """Report response model."""
    report_id: str
    simulation_id: str
    template: str
    format: str
    file_path: str
    file_size: int
    status: ResultStatus
    created_at: str


@router.get("/results", response_model=SimulationResultListResponse)
async def list_simulation_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    simulation_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    result_type: Optional[ResultType] = None,
    status: Optional[ResultStatus] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(name|created_at|updated_at|result_type|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List simulation results with pagination and filters."""
    query = select(SimulationResult).options(
        selectinload(SimulationResult.simulation).selectinload(Simulation.project)
    )
    
    # Filter by simulation
    if simulation_id:
        sim_result = await db.execute(
            select(Simulation)
            .options(selectinload(Simulation.project))
            .where(Simulation.id == simulation_id)
        )
        simulation = sim_result.scalar_one_or_none()
        
        if not simulation:
            raise NotFoundError("Simulation", str(simulation_id))
        
        if not _check_project_access(simulation.project, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to simulation",
            )
        
        query = query.where(SimulationResult.simulation_id == simulation_id)
    
    # Filter by project
    elif project_id:
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
        
        # Join with simulation to filter by project
        query = query.join(Simulation).where(Simulation.project_id == project_id)
    
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
            query = query.join(Simulation).where(Simulation.project_id.in_(accessible_project_ids))
    
    if result_type:
        query = query.where(SimulationResult.result_type == result_type)
    
    if status:
        query = query.where(SimulationResult.status == status)
    
    if search:
        query = query.where(
            or_(
                SimulationResult.name.ilike(f"%{search}%"),
                SimulationResult.description.ilike(f"%{search}%"),
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply sorting
    sort_column = getattr(SimulationResult, sort_by, SimulationResult.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    results = result.scalars().all()
    
    return SimulationResultListResponse(
        results=[
            SimulationResultResponse(
                id=str(r.id),
                simulation_id=str(r.simulation_id),
                name=r.name,
                description=r.description,
                result_type=r.result_type,
                status=r.status,
                time_step=r.time_step,
                time_value=r.time_value,
                file_path=r.file_path,
                file_size=r.file_size,
                metadata=r.metadata,
                variables=r.variables,
                region=r.region,
                min_values=r.min_values,
                max_values=r.max_values,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
            )
            for r in results
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/results", response_model=SimulationResultResponse, status_code=status.HTTP_201_CREATED)
async def create_simulation_result(
    result_data: SimulationResultCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new simulation result entry."""
    # Verify simulation access
    sim_result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == result_data.simulation_id)
    )
    simulation = sim_result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(result_data.simulation_id))
    
    if not _check_project_write_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied to simulation",
        )
    
    result = SimulationResult(
        simulation_id=result_data.simulation_id,
        name=result_data.name,
        description=result_data.description,
        result_type=result_data.result_type,
        time_step=result_data.time_step,
        time_value=result_data.time_value,
        file_path=result_data.file_path,
        file_size=result_data.file_size,
        metadata=result_data.metadata,
        variables=result_data.variables,
        region=result_data.region,
        status=ResultStatus.PENDING,
    )
    
    db.add(result)
    await db.commit()
    await db.refresh(result)
    
    return SimulationResultResponse(
        id=str(result.id),
        simulation_id=str(result.simulation_id),
        name=result.name,
        description=result.description,
        result_type=result.result_type,
        status=result.status,
        time_step=result.time_step,
        time_value=result.time_value,
        file_path=result.file_path,
        file_size=result.file_size,
        metadata=result.metadata,
        variables=result.variables,
        region=result.region,
        min_values=result.min_values,
        max_values=result.max_values,
        created_at=result.created_at.isoformat(),
        updated_at=result.updated_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
    )


@router.get("/results/{result_id}", response_model=SimulationResultResponse)
async def get_simulation_result(
    result_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get simulation result by ID."""
    result = await db.execute(
        select(SimulationResult)
        .options(
            selectinload(SimulationResult.simulation).selectinload(Simulation.project)
        )
        .where(SimulationResult.id == result_id)
    )
    result = result.scalar_one_or_none()
    
    if not result:
        raise NotFoundError("SimulationResult", str(result_id))
    
    if not _check_project_access(result.simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to result",
        )
    
    return SimulationResultResponse(
        id=str(result.id),
        simulation_id=str(result.simulation_id),
        name=result.name,
        description=result.description,
        result_type=result.result_type,
        status=result.status,
        time_step=result.time_step,
        time_value=result.time_value,
        file_path=result.file_path,
        file_size=result.file_size,
        metadata=result.metadata,
        variables=result.variables,
        region=result.region,
        min_values=result.min_values,
        max_values=result.max_values,
        created_at=result.created_at.isoformat(),
        updated_at=result.updated_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
    )


@router.patch("/results/{result_id}", response_model=SimulationResultResponse)
async def update_simulation_result(
    result_id: UUID,
    result_data: SimulationResultUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update simulation result."""
    result = await db.execute(
        select(SimulationResult)
        .options(
            selectinload(SimulationResult.simulation).selectinload(Simulation.project)
        )
        .where(SimulationResult.id == result_id)
    )
    result = result.scalar_one_or_none()
    
    if not result:
        raise NotFoundError("SimulationResult", str(result_id))
    
    if not _check_project_write_access(result.simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    update_data = result_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(result, field, value)
    
    result.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(result)
    
    return SimulationResultResponse(
        id=str(result.id),
        simulation_id=str(result.simulation_id),
        name=result.name,
        description=result.description,
        result_type=result.result_type,
        status=result.status,
        time_step=result.time_step,
        time_value=result.time_value,
        file_path=result.file_path,
        file_size=result.file_size,
        metadata=result.metadata,
        variables=result.variables,
        region=result.region,
        min_values=result.min_values,
        max_values=result.max_values,
        created_at=result.created_at.isoformat(),
        updated_at=result.updated_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
    )


@router.delete("/results/{result_id}")
async def delete_simulation_result(
    result_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete simulation result."""
    result = await db.execute(
        select(SimulationResult)
        .options(
            selectinload(SimulationResult.simulation).selectinload(Simulation.project)
        )
        .where(SimulationResult.id == result_id)
    )
    result = result.scalar_one_or_none()
    
    if not result:
        raise NotFoundError("SimulationResult", str(result_id))
    
    if not _check_project_write_access(result.simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied",
        )
    
    await db.delete(result)
    await db.commit()
    
    return {"message": "Simulation result deleted"}


@router.post("/visualize", response_model=VisualizationResponse)
async def create_visualization(
    viz_request: VisualizationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create visualization from simulation result."""
    result = await db.execute(
        select(SimulationResult)
        .options(
            selectinload(SimulationResult.simulation).selectinload(Simulation.project)
        )
        .where(SimulationResult.id == viz_request.result_id)
    )
    result = result.scalar_one_or_none()
    
    if not result:
        raise NotFoundError("SimulationResult", str(viz_request.result_id))
    
    if not _check_project_access(result.simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to result",
        )
    
    post_service = PostProcessingService(db)
    visualization = await post_service.create_visualization(
        result_id=viz_request.result_id,
        visualization_type=viz_request.visualization_type,
        field_name=viz_request.field_name,
        parameters=viz_request.parameters,
        color_map=viz_request.color_map,
        opacity=viz_request.opacity,
        show_edges=viz_request.show_edges,
        line_width=viz_request.line_width,
        point_size=viz_request.point_size,
    )
    
    return VisualizationResponse(
        visualization_id=visualization["visualization_id"],
        result_id=str(viz_request.result_id),
        visualization_type=viz_request.visualization_type,
        field_name=viz_request.field_name,
        parameters=viz_request.parameters,
        image_data=visualization.get("image_data"),
        vtk_data=visualization.get("vtk_data"),
        metadata=visualization.get("metadata", {}),
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/export", response_model=ExportResponse)
async def export_results(
    export_request: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Export simulation results."""
    # Verify access to all results
    for result_id in export_request.result_ids:
        result = await db.execute(
            select(SimulationResult)
            .options(
                selectinload(SimulationResult.simulation).selectinload(Simulation.project)
            )
            .where(SimulationResult.id == result_id)
        )
        result = result.scalar_one_or_none()
        
        if not result:
            raise NotFoundError("SimulationResult", str(result_id))
        
        if not _check_project_access(result.simulation.project, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to result {result_id}",
            )
    
    post_service = PostProcessingService(db)
    export = await post_service.export_results(
        result_ids=export_request.result_ids,
        format=export_request.format,
        options=export_request.options,
        include_metadata=export_request.include_metadata,
    )
    
    return ExportResponse(
        export_id=export["export_id"],
        format=export_request.format,
        file_path=export["file_path"],
        file_size=export["file_size"],
        status=export["status"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/probe", response_model=ProbeResponse)
async def probe_fields(
    probe_request: ProbeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Probe field values at specific points."""
    # Verify simulation access
    sim_result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == probe_request.simulation_id)
    )
    simulation = sim_result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(probe_request.simulation_id))
    
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to simulation",
        )
    
    post_service = PostProcessingService(db)
    probe_data = await post_service.probe_fields(
        simulation_id=probe_request.simulation_id,
        points=probe_request.points,
        fields=probe_request.fields,
        time_steps=probe_request.time_steps,
        interpolation=probe_request.interpolation,
    )
    
    return ProbeResponse(
        probe_id=probe_data["probe_id"],
        simulation_id=str(probe_request.simulation_id),
        points=probe_request.points,
        fields=probe_request.fields,
        time_steps=probe_data["time_steps"],
        data=probe_data["data"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/cut-plane", response_model=CutPlaneResponse)
async def create_cut_plane(
    cut_request: CutPlaneRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create cut plane through simulation data."""
    # Verify simulation access
    sim_result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == cut_request.simulation_id)
    )
    simulation = sim_result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(cut_request.simulation_id))
    
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to simulation",
        )
    
    post_service = PostProcessingService(db)
    cut_plane = await post_service.create_cut_plane(
        simulation_id=cut_request.simulation_id,
        origin=cut_request.origin,
        normal=cut_request.normal,
        fields=cut_request.fields,
        time_step=cut_request.time_step,
        resolution=cut_request.resolution,
    )
    
    return CutPlaneResponse(
        cut_plane_id=cut_plane["cut_plane_id"],
        simulation_id=str(cut_request.simulation_id),
        origin=cut_request.origin,
        normal=cut_request.normal,
        fields=cut_request.fields,
        time_step=cut_request.time_step,
        resolution=cut_request.resolution,
        data=cut_plane["data"],
        bounds=cut_plane["bounds"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/streamlines", response_model=StreamlineResponse)
async def create_streamlines(
    stream_request: StreamlineRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create streamlines from velocity field."""
    # Verify simulation access
    sim_result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == stream_request.simulation_id)
    )
    simulation = sim_result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(stream_request.simulation_id))
    
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to simulation",
        )
    
    post_service = PostProcessingService(db)
    streamlines = await post_service.create_streamlines(
        simulation_id=stream_request.simulation_id,
        seed_type=stream_request.seed_type,
        seed_points=stream_request.seed_points,
        seed_resolution=stream_request.seed_resolution,
        field_name=stream_request.field_name,
        integration_direction=stream_request.integration_direction,
        max_steps=stream_request.max_steps,
        step_size=stream_request.step_size,
        time_step=stream_request.time_step,
    )
    
    return StreamlineResponse(
        streamline_id=streamlines["streamline_id"],
        simulation_id=str(stream_request.simulation_id),
        seed_type=stream_request.seed_type,
        seed_points=stream_request.seed_points,
        field_name=stream_request.field_name,
        integration_direction=stream_request.integration_direction,
        max_steps=stream_request.max_steps,
        step_size=stream_request.step_size,
        time_step=stream_request.time_step,
        streamlines=streamlines["streamlines"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/animation", response_model=AnimationResponse)
async def create_animation(
    anim_request: AnimationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create animation from time-series data."""
    # Verify simulation access
    sim_result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == anim_request.simulation_id)
    )
    simulation = sim_result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(anim_request.simulation_id))
    
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to simulation",
        )
    
    post_service = PostProcessingService(db)
    animation = await post_service.create_animation(
        simulation_id=anim_request.simulation_id,
        visualization_type=anim_request.visualization_type,
        field_name=anim_request.field_name,
        time_steps=anim_request.time_steps,
        parameters=anim_request.parameters,
        frame_rate=anim_request.frame_rate,
        resolution=anim_request.resolution,
        format=anim_request.format,
    )
    
    return AnimationResponse(
        animation_id=animation["animation_id"],
        simulation_id=str(anim_request.simulation_id),
        visualization_type=anim_request.visualization_type,
        field_name=anim_request.field_name,
        time_steps=anim_request.time_steps,
        frame_rate=anim_request.frame_rate,
        resolution=anim_request.resolution,
        format=anim_request.format,
        file_path=animation.get("file_path"),
        status=animation["status"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/compare", response_model=ComparisonResponse)
async def compare_simulations(
    compare_request: ComparisonRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Compare multiple simulation results."""
    # Verify access to all simulations
    for sim_id in compare_request.simulation_ids:
        sim_result = await db.execute(
            select(Simulation)
            .options(selectinload(Simulation.project))
            .where(Simulation.id == sim_id)
        )
        simulation = sim_result.scalar_one_or_none()
        
        if not simulation:
            raise NotFoundError("Simulation", str(sim_id))
        
        if not _check_project_access(simulation.project, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to simulation {sim_id}",
            )
    
    post_service = PostProcessingService(db)
    comparison = await post_service.compare_simulations(
        simulation_ids=compare_request.simulation_ids,
        field_name=compare_request.field_name,
        time_step=compare_request.time_step,
        comparison_type=compare_request.comparison_type,
        region=compare_request.region,
    )
    
    return ComparisonResponse(
        comparison_id=comparison["comparison_id"],
        simulation_ids=[str(s) for s in compare_request.simulation_ids],
        field_name=compare_request.field_name,
        time_step=compare_request.time_step,
        comparison_type=compare_request.comparison_type,
        region=compare_request.region,
        data=comparison["data"],
        statistics=comparison["statistics"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/report", response_model=ReportResponse)
async def generate_report(
    report_request: ReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate simulation report."""
    # Verify simulation access
    sim_result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.project))
        .where(Simulation.id == report_request.simulation_id)
    )
    simulation = sim_result.scalar_one_or_none()
    
    if not simulation:
        raise NotFoundError("Simulation", str(report_request.simulation_id))
    
    if not _check_project_access(simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to simulation",
        )
    
    post_service = PostProcessingService(db)
    report = await post_service.generate_report(
        simulation_id=report_request.simulation_id,
        template=report_request.template,
        sections=report_request.sections,
        include_images=report_request.include_images,
        include_tables=report_request.include_tables,
        format=report_request.format,
    )
    
    return ReportResponse(
        report_id=report["report_id"],
        simulation_id=str(report_request.simulation_id),
        template=report_request.template,
        format=report_request.format,
        file_path=report["file_path"],
        file_size=report["file_size"],
        status=report["status"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.get("/results/{result_id}/statistics")
async def get_result_statistics(
    result_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get statistical summary of result data."""
    result = await db.execute(
        select(SimulationResult)
        .options(
            selectinload(SimulationResult.simulation).selectinload(Simulation.project)
        )
        .where(SimulationResult.id == result_id)
    )
    result = result.scalar_one_or_none()
    
    if not result:
        raise NotFoundError("SimulationResult", str(result_id))
    
    if not _check_project_access(result.simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to result",
        )
    
    post_service = PostProcessingService(db)
    stats = await post_service.get_result_statistics(result_id)
    
    return stats


@router.get("/results/{result_id}/histogram")
async def get_result_histogram(
    result_id: UUID,
    field_name: str,
    bins: int = Query(50, ge=10, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get histogram of field values."""
    result = await db.execute(
        select(SimulationResult)
        .options(
            selectinload(SimulationResult.simulation).selectinload(Simulation.project)
        )
        .where(SimulationResult.id == result_id)
    )
    result = result.scalar_one_or_none()
    
    if not result:
        raise NotFoundError("SimulationResult", str(result_id))
    
    if not _check_project_access(result.simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to result",
        )
    
    post_service = PostProcessingService(db)
    histogram = await post_service.get_field_histogram(result_id, field_name, bins)
    
    return histogram


@router.post("/results/{result_id}/extract-surface")
async def extract_surface(
    result_id: UUID,
    region: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Extract surface mesh from volume result."""
    result = await db.execute(
        select(SimulationResult)
        .options(
            selectinload(SimulationResult.simulation).selectinload(Simulation.project)
        )
        .where(SimulationResult.id == result_id)
    )
    result = result.scalar_one_or_none()
    
    if not result:
        raise NotFoundError("SimulationResult", str(result_id))
    
    if not _check_project_access(result.simulation.project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to result",
        )
    
    post_service = PostProcessingService(db)
    surface = await post_service.extract_surface(result_id, region)
    
    return surface


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