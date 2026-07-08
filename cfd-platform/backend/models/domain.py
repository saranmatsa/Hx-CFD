"""
Core domain models for the CFD Platform.
These models represent the core business entities and are independent of any external dependencies.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid


class ProjectStatus(str, Enum):
    """Project lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class GeometryFormat(str, Enum):
    """Supported geometry file formats."""
    STEP = "step"
    IGES = "iges"
    BREP = "brep"
    STL = "stl"
    OBJ = "obj"


class MeshFormat(str, Enum):
    """Supported mesh file formats."""
    UNSTRUCTURED = "unstructured"
    STRUCTURED = "structured"
    OPENFOAM = "openfoam"
    VTK = "vtk"
    STL = "stl"


class MeshStatus(str, Enum):
    """Mesh generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class SolverType(str, Enum):
    """OpenFOAM solver types."""
    SIMPLE = "simpleFoam"
    PIMPLE = "pimpleFoam"
    PISOF = "pisoFoam"
    INTER = "interFoam"
    RHO = "rhoCentralFoam"
    DNS = "dnsFoam"


class SimulationStatus(str, Enum):
    """Simulation run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OptimizationStatus(str, Enum):
    """Optimization run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, Enum):
    """Background job status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Base model configuration
class BaseModelConfig:
    """Base Pydantic model configuration."""
    from_attributes = True
    populate_by_name = True


class UUIDModel(BaseModel):
    """Base model with UUID primary key."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class TimestampModel(BaseModel):
    """Base model with timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Project Model
class ProjectBase(BaseModel):
    """Base project fields."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: ProjectStatus = ProjectStatus.DRAFT
    geometry_format: GeometryFormat = GeometryFormat.STEP
    mesh_format: MeshFormat = MeshFormat.OPENFOAM
    solver_type: SolverType = SolverType.SIMPLE


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ProjectStatus] = None


class Project(ProjectBase, UUIDModel, TimestampModel):
    """Complete project model."""
    geometry_path: Optional[str] = None
    mesh_path: Optional[str] = None
    case_path: Optional[str] = None
    results_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectSummary(BaseModel):
    """Summary view of a project."""
    id: str
    name: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


# Geometry Model
class GeometryBase(BaseModel):
    """Base geometry fields."""
    name: str = Field(..., min_length=1, max_length=255)
    format: GeometryFormat
    file_path: str
    bounding_box: Optional[Dict[str, float]] = None
    volume: Optional[float] = None
    surface_area: Optional[float] = None


class Geometry(GeometryBase, UUIDModel, TimestampModel):
    """Complete geometry model."""
    project_id: str
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Mesh Model
class MeshBase(BaseModel):
    """Base mesh fields."""
    name: str = Field(..., min_length=1, max_length=255)
    format: MeshFormat
    file_path: str
    element_count: Optional[int] = None
    node_count: Optional[int] = None
    mesh_quality: Optional[Dict[str, float]] = None


class Mesh(MeshBase, UUIDModel, TimestampModel):
    """Complete mesh model."""
    project_id: str
    geometry_id: str
    mesh_config: Dict[str, Any] = Field(default_factory=dict)


# Simulation Model
class SimulationConfig(BaseModel):
    """Simulation configuration."""
    solver: SolverType = SolverType.SIMPLE
    start_time: float = 0.0
    end_time: float = 1000.0
    delta_t: float = 0.5
    write_interval: float = 100.0
    residual_control: bool = True
    max_iterations: int = 1000
    tolerance: float = 1e-6
    relaxation_factors: Dict[str, float] = Field(default_factory=dict)
    boundary_conditions: Dict[str, Any] = Field(default_factory=dict)


class SimulationBase(BaseModel):
    """Base simulation fields."""
    name: str = Field(..., min_length=1, max_length=255)
    config: SimulationConfig = Field(default_factory=SimulationConfig)


class Simulation(SimulationBase, UUIDModel, TimestampModel):
    """Complete simulation model."""
    project_id: str
    mesh_id: str
    status: SimulationStatus = SimulationStatus.PENDING
    case_path: Optional[str] = None
    results_path: Optional[str] = None
    iterations: Optional[int] = None
    final_residuals: Optional[Dict[str, float]] = None
    runtime_seconds: Optional[float] = None
    error_message: Optional[str] = None


# Optimization Model
class OptimizationConfig(BaseModel):
    """Optimization configuration."""
    algorithm: str = "NGOpt"
    max_iterations: int = 100
    budget: int = 1000
    objective_function: str = "drag"
    constraints: List[str] = Field(default_factory=list)
    design_variables: List[Dict[str, Any]] = Field(default_factory=list)


class OptimizationBase(BaseModel):
    """Base optimization fields."""
    name: str = Field(..., min_length=1, max_length=255)
    config: OptimizationConfig = Field(default_factory=OptimizationConfig)


class Optimization(OptimizationBase, UUIDModel, TimestampModel):
    """Complete optimization model."""
    project_id: str
    simulation_id: str
    status: OptimizationStatus = OptimizationStatus.PENDING
    best_parameters: Optional[Dict[str, float]] = None
    best_objective: Optional[float] = None
    iterations: Optional[int] = None
    error_message: Optional[str] = None


# Job Model
class JobBase(BaseModel):
    """Base job fields."""
    job_type: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    message: Optional[str] = None


class Job(JobBase, UUIDModel, TimestampModel):
    """Background job model."""
    project_id: Optional[str] = None
    entity_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Visualization Model
class VisualizationConfig(BaseModel):
    """Visualization configuration."""
    field_name: str = "U"
    time_step: Optional[float] = None
    slice_position: Optional[Dict[str, float]] = None
    color_range: Optional[tuple[float, float]] = None
    show_mesh: bool = False
    show_boundaries: bool = True


class Visualization(BaseModel):
    """Visualization configuration model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    simulation_id: str
    config: VisualizationConfig = Field(default_factory=VisualizationConfig)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# AI Provider Configuration
class AIProviderType(str, Enum):
    """Supported AI provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NVIDIA_NIM = "nvidia_nim"
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    OPENROUTER = "openrouter"


class AIProviderConfig(BaseModel):
    """AI provider configuration."""
    provider_type: AIProviderType
    base_url: Optional[str] = None
    model: str = "gpt-4"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


class AIConversation(BaseModel):
    """AI conversation history."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    messages: List[Dict[str, str]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)