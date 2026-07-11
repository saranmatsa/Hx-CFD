"""
Solver configuration models for CFD Backend.

Defines solver configuration entities and related enums.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text, Float, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cfd_backend.models.base import Base, BaseModel, JSONBType
from cfd_backend.models.simulation import SolverType


class SolverStatus(str, enum.Enum):
    """Solver status enumeration."""
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SolverConfig(BaseModel):
    """Solver configuration model."""
    
    __tablename__ = "solver_configs"
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Ownership
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    simulation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("simulations.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Solver settings
    solver_type: Mapped[SolverType] = mapped_column(
        Enum(SolverType),
        default=SolverType.OPENFOAM,
        nullable=False,
    )
    solver_version: Mapped[str] = mapped_column(String(50), default="v11", nullable=False)
    case_directory: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # OpenFOAM dictionary configurations
    control_dict: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    fv_schemes: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    fv_solution: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    transport_properties: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    turbulence_properties: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Conditions
    boundary_conditions: Mapped[List[Dict[str, Any]]] = mapped_column(JSONBType, default=list, nullable=False)
    initial_conditions: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Solver parameters
    solver_parameters: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Parallel execution
    parallel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    num_processors: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    decomposition_method: Mapped[str] = mapped_column(String(50), default="scotch", nullable=False)
    
    # Status
    status: Mapped[SolverStatus] = mapped_column(
        Enum(SolverStatus),
        default=SolverStatus.READY,
        nullable=False,
        index=True,
    )
    
    # Last run info
    last_run_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_run_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_run_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project")
    simulation: Mapped[Optional["Simulation"]] = relationship("Simulation")
    
    # Indexes
    __table_args__ = (
        Index("ix_solver_configs_project_status", "project_id", "status"),
        Index("ix_solver_configs_solver_type", "solver_type"),
    )
    
    def __repr__(self) -> str:
        return f"<SolverConfig(id={self.id}, name='{self.name}', solver_type={self.solver_type})>"