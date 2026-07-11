"""
Simulation models for CFD Backend.

Defines the Simulation entity, solver types, and related enums.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text, Float, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cfd_backend.models.base import Base, BaseModel, JSONBType


class SolverType(str, enum.Enum):
    """CFD Solver type enumeration."""
    OPENFOAM = "openfoam"
    SU2 = "su2"
    ANSYS_FLUENT = "ansys_fluent"
    STARCCM = "starccm"
    OPENFOAM_DEV = "openfoam_dev"
    CUSTOM = "custom"


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
    
    # Solver configuration
    solver_type: Mapped[SolverType] = mapped_column(
        Enum(SolverType),
        default=SolverType.OPENFOAM,
        nullable=False,
    )
    solver_config: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Mesh reference
    mesh_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("meshes.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Boundary and initial conditions
    boundary_conditions: Mapped[List[Dict[str, Any]]] = mapped_column(JSONBType, default=list, nullable=False)
    initial_conditions: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    solver_settings: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Execution settings
    max_runtime_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Progress tracking
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_iteration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_iterations: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    
    # Execution timing
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Resources
    cpu_cores: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    memory_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cpu_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_peak_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Storage
    disk_usage_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    result_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Results paths
    results_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    log_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metrics
    convergence_data: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    performance_metrics: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="simulations")
    mesh: Mapped[Optional["Mesh"]] = relationship("Mesh", back_populates="simulations")
    optimization_trials: Mapped[List["OptimizationTrial"]] = relationship(
        "OptimizationTrial",
        back_populates="simulation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_simulations_project_status", "project_id", "status"),
        Index("ix_simulations_started", "started_at"),
        Index("ix_simulations_solver_type", "solver_type"),
    )
    
    def __repr__(self) -> str:
        return f"<Simulation(id={self.id}, name='{self.name}', status={self.status})>"