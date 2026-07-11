"""
Optimization models for CFD Backend.

Defines models for optimization studies, trials, and surrogate models.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cfd_backend.models.base import Base, BaseModel, JSONBType


class StudyType(str, enum.Enum):
    """Optimization study type enumeration."""
    PARAMETER_SWEEP = "parameter_sweep"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    GENETIC_ALGORITHM = "genetic_algorithm"
    GRADIENT_BASED = "gradient_based"
    SURROGATE_BASED = "surrogate_based"
    MULTI_OBJECTIVE = "multi_objective"
    CUSTOM = "custom"


class StudyStatus(str, enum.Enum):
    """Optimization study status enumeration."""
    DRAFT = "draft"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrialStatus(str, enum.Enum):
    """Optimization trial status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PRUNED = "pruned"


class SurrogateType(str, enum.Enum):
    """Surrogate model type enumeration."""
    GAUSSIAN_PROCESS = "gaussian_process"
    RADIAL_BASIS_FUNCTION = "radial_basis_function"
    POLYNOMIAL_CHAOS = "polynomial_chaos"
    NEURAL_NETWORK = "neural_network"
    KRIGING = "kriging"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    CUSTOM = "custom"


# Aliases for service compatibility
OptimizationType = StudyType
OptimizationStatus = StudyStatus


class OptimizationStudy(BaseModel):
    """Optimization study model."""
    
    __tablename__ = "optimization_studies"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    study_type: Mapped[StudyType] = mapped_column(
        Enum(StudyType),
        nullable=False,
    )
    status: Mapped[StudyStatus] = mapped_column(
        Enum(StudyStatus),
        default=StudyStatus.DRAFT,
        nullable=False,
        index=True,
    )
    
    # Study configuration
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    objectives: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    constraints: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Algorithm settings
    algorithm_settings: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Execution settings
    max_trials: Mapped[int] = mapped_column(default=100, nullable=False)
    max_parallel_trials: Mapped[int] = mapped_column(default=1, nullable=False)
    timeout_seconds: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Results
    best_trial_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    best_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONBType, nullable=True)
    best_objectives: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONBType, nullable=True)
    pareto_front: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONBType, nullable=True)
    
    # Progress
    completed_trials: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_trials: Mapped[int] = mapped_column(default=0, nullable=False)
    pruned_trials: Mapped[int] = mapped_column(default=0, nullable=False)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    total_time_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Error
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="optimization_studies")
    trials: Mapped[List["OptimizationTrial"]] = relationship(
        "OptimizationTrial",
        back_populates="study",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    surrogate_models: Mapped[List["SurrogateModel"]] = relationship(
        "SurrogateModel",
        back_populates="study",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_optimization_studies_project_status", "project_id", "status"),
        Index("ix_optimization_studies_study_type", "study_type"),
    )
    
    def __repr__(self) -> str:
        return f"<OptimizationStudy(id={self.id}, name='{self.name}', type={self.study_type}, status={self.status})>"


class OptimizationTrial(BaseModel):
    """Optimization trial model."""
    
    __tablename__ = "optimization_trials"
    
    study_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("optimization_studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    trial_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[TrialStatus] = mapped_column(
        Enum(TrialStatus),
        default=TrialStatus.PENDING,
        nullable=False,
        index=True,
    )
    
    # Parameters and results
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    objectives: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONBType, nullable=True)
    constraints: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONBType, nullable=True)
    
    # Intermediate values (for pruning)
    intermediate_values: Mapped[List[Dict[str, Any]]] = mapped_column(JSONBType, default=list, nullable=False)
    
    # Execution
    simulation_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Error
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    user_attrs: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    system_attrs: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Relationships
    study: Mapped["OptimizationStudy"] = relationship("OptimizationStudy", back_populates="trials")
    
    # Indexes
    __table_args__ = (
        Index("ix_optimization_trials_study_number", "study_id", "trial_number", unique=True),
        Index("ix_optimization_trials_study_status", "study_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<OptimizationTrial(id={self.id}, study_id={self.study_id}, number={self.trial_number}, status={self.status})>"


class SurrogateModel(BaseModel):
    """Surrogate model for optimization."""
    
    __tablename__ = "surrogate_models"
    
    study_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("optimization_studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    surrogate_type: Mapped[SurrogateType] = mapped_column(
        Enum(SurrogateType),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), default="training", nullable=False)
    
    # Model configuration
    config: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    # Training data
    training_trials: Mapped[List[int]] = mapped_column(JSONBType, default=list, nullable=False)
    training_samples: Mapped[int] = mapped_column(default=0, nullable=False)
    
    # Model artifacts
    model_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    model_format: Mapped[str] = mapped_column(String(50), default="pickle", nullable=False)
    
    # Performance metrics
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    cross_validation_scores: Mapped[Optional[List[float]]] = mapped_column(JSONBType, nullable=True)
    
    # Timing
    trained_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    training_time_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Error
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    study: Mapped["OptimizationStudy"] = relationship("OptimizationStudy", back_populates="surrogate_models")
    
    # Indexes
    __table_args__ = (
        Index("ix_surrogate_models_study_type", "study_id", "surrogate_type"),
    )
    
    def __repr__(self) -> str:
        return f"<SurrogateModel(id={self.id}, study_id={self.study_id}, type={self.surrogate_type}, status={self.status})>"