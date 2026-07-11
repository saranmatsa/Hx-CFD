"""
Simulation result models for CFD Backend.

Defines simulation result entities and related enums for post-processing.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cfd_backend.models.base import Base, BaseModel, JSONBType


class ResultType(str, enum.Enum):
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


class ResultStatus(str, enum.Enum):
    """Result status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPORTED = "exported"


class SimulationResult(BaseModel):
    """Simulation result model for post-processing."""
    
    __tablename__ = "simulation_results"
    
    # Ownership
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_type: Mapped[ResultType] = mapped_column(
        Enum(ResultType),
        nullable=False,
    )
    status: Mapped[ResultStatus] = mapped_column(
        Enum(ResultStatus),
        default=ResultStatus.PENDING,
        nullable=False,
        index=True,
    )
    
    # Time information
    time_step: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # File information
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Metadata
    result_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    variables: Mapped[List[str]] = mapped_column(JSONBType, default=list, nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Statistics
    min_values: Mapped[Dict[str, float]] = mapped_column(JSONBType, default=dict, nullable=False)
    max_values: Mapped[Dict[str, float]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Timing
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Relationships
    simulation: Mapped["Simulation"] = relationship("Simulation")
    
    # Indexes
    __table_args__ = (
        Index("ix_simulation_results_simulation_type", "simulation_id", "result_type"),
        Index("ix_simulation_results_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<SimulationResult(id={self.id}, name='{self.name}', type={self.result_type})>"