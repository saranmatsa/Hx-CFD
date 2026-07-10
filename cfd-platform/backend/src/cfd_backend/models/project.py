"""
Project models for CFD Backend.

Defines the Project entity and related models for CFD simulation projects.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cfd_backend.models.base import Base, BaseModel, JSONColumn


class ProjectStatus(str, enum.Enum):
    """Project status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class SimulationType(str, enum.Enum):
    """CFD simulation type enumeration."""
    STEADY = "steady"
    TRANSIENT = "transient"
    COMPRESSIBLE = "compressible"
    INCOMPRESSIBLE = "incompressible"
    MULTIPHASE = "multiphase"
    HEAT_TRANSFER = "heat_transfer"
    REACTING_FLOW = "reacting_flow"
    PARTICLE_TRACKING = "particle_tracking"


class TurbulenceModel(str, enum.Enum):
    """Turbulence model enumeration."""
    LAMINAR = "laminar"
    K_EPSILON = "kEpsilon"
    K_OMEGA = "kOmega"
    K_OMEGA_SST = "kOmegaSST"
    SPALART_ALLMARAS = "SpalartAllmaras"
    REALIZABLE_K_EPSILON = "realizableKEpsilon"
    RNG_K_EPSILON = "RNGkEpsilon"
    LES = "LES"
    DES = "DES"


class Project(BaseModel):
    """CFD Project model."""
    
    __tablename__ = "projects"
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.DRAFT,
        nullable=False,
        index=True,
    )
    
    # Simulation settings
    simulation_type: Mapped[SimulationType] = mapped_column(
        Enum(SimulationType),
        default=SimulationType.INCOMPRESSIBLE,
        nullable=False,
    )
    turbulence_model: Mapped[TurbulenceModel] = mapped_column(
        Enum(TurbulenceModel),
        default=TurbulenceModel.K_OMEGA_SST,
        nullable=False,
    )
    
    # Geometry & Mesh
    geometry_file: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    geometry_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    mesh_file: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    mesh_settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Physics settings
    physics_settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    boundary_conditions: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    initial_conditions: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Solver settings
    solver_settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    time_settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Results
    results_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_simulation_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    
    # Metadata
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    
    # Ownership
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True, index=True)
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Relationships
    simulations: Mapped[List["Simulation"]] = relationship(
        "Simulation",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    meshes: Mapped[List["Mesh"]] = relationship(
        "Mesh",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    optimizations: Mapped[List["Optimization"]] = relationship(
        "Optimization",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_projects_owner_status", "owner_id", "status"),
        Index("ix_projects_name_owner", "name", "owner_id"),
        UniqueConstraint("name", "owner_id", name="uq_project_name_owner"),
    )
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', status={self.status})>"


class SimulationStatus(str, enum.Enum):
    """Simulation status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    POST_PROCESSING = "post_processing"


class Simulation(BaseModel):
    """CFD Simulation run model."""
    
    __tablename__ = "simulations"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Run info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[SimulationStatus] = mapped_column(
        Enum(SimulationStatus),
        default=SimulationStatus.PENDING,
        nullable=False,
        index=True,
    )
    
    # Configuration snapshot
    config_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Execution
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Resources
    cpu_cores: Mapped[int] = mapped_column(default=1, nullable=False)
    memory_gb: Mapped[Optional[float]] = mapped_column(nullable=True)
    gpu_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Results
    results_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    log_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metrics
    convergence_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    performance_metrics: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="simulations")
    mesh_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("meshes.id", ondelete="SET NULL"),
        nullable=True,
    )
    mesh: Mapped[Optional["Mesh"]] = relationship("Mesh", back_populates="simulations")
    
    # Indexes
    __table_args__ = (
        Index("ix_simulations_project_status", "project_id", "status"),
        Index("ix_simulations_started", "started_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Simulation(id={self.id}, project_id={self.project_id}, status={self.status})>"


class MeshType(str, enum.Enum):
    """Mesh type enumeration."""
    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"
    HYBRID = "hybrid"
    BOUNDARY_LAYER = "boundary_layer"
    OVERSSET = "overset"


class MeshStatus(str, enum.Enum):
    """Mesh generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Mesh(BaseModel):
    """Mesh model."""
    
    __tablename__ = "meshes"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mesh_type: Mapped[MeshType] = mapped_column(
        Enum(MeshType),
        default=MeshType.UNSTRUCTURED,
        nullable=False,
    )
    status: Mapped[MeshStatus] = mapped_column(
        Enum(MeshStatus),
        default=MeshStatus.PENDING,
        nullable=False,
        index=True,
    )
    
    # Mesh file
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_format: Mapped[str] = mapped_column(String(50), default="msh", nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Mesh statistics
    num_cells: Mapped[Optional[int]] = mapped_column(nullable=True)
    num_faces: Mapped[Optional[int]] = mapped_column(nullable=True)
    num_nodes: Mapped[Optional[int]] = mapped_column(nullable=True)
    min_orthogonality: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_aspect_ratio: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_skewness: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Generation settings
    generation_settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    generation_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generation_time_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Quality metrics
    quality_metrics: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="meshes")
    simulations: Mapped[List["Simulation"]] = relationship(
        "Simulation",
        back_populates="mesh",
        lazy="selectin",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_meshes_project_status", "project_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Mesh(id={self.id}, project_id={self.project_id}, type={self.mesh_type})>"


class OptimizationStatus(str, enum.Enum):
    """Optimization status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OptimizationAlgorithm(str, enum.Enum):
    """Optimization algorithm enumeration."""
    NEVERGRAD_RANDOM = "nevergrad_random"
    NEVERGRAD_CMA = "nevergrad_cma"
    NEVERGRAD_PSO = "nevergrad_pso"
    NEVERGRAD_DE = "nevergrad_de"
    OPENMDAO_SLSQP = "openmdao_slsqp"
    OPENMDAO_COBYLA = "openmdao_cobyla"
    OPENMDAO_NSGA2 = "openmdao_nsga2"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"


class Optimization(BaseModel):
    """Optimization study model."""
    
    __tablename__ = "optimizations"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[OptimizationStatus] = mapped_column(
        Enum(OptimizationStatus),
        default=OptimizationStatus.PENDING,
        nullable=False,
        index=True,
    )
    algorithm: Mapped[OptimizationAlgorithm] = mapped_column(
        Enum(OptimizationAlgorithm),
        nullable=False,
    )
    
    # Parameters
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    objectives: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    constraints: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Execution
    max_iterations: Mapped[int] = mapped_column(default=100, nullable=False)
    current_iteration: Mapped[int] = mapped_column(default=0, nullable=False)
    population_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Results
    best_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    best_objectives: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    pareto_front: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    history: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    total_time_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Error
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="optimizations")
    
    # Indexes
    __table_args__ = (
        Index("ix_optimizations_project_status", "project_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Optimization(id={self.id}, project_id={self.project_id}, algorithm={self.algorithm})>"