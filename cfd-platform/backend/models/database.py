"""
SQLAlchemy database models for persistent storage.
These models map domain models to database tables.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, ForeignKey,
    Text, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class ProjectStatusDB(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class GeometryFormatDB(str, enum.Enum):
    STEP = "step"
    IGES = "iges"
    BREP = "brep"
    STL = "stl"
    OBJ = "obj"


class MeshFormatDB(str, enum.Enum):
    UNSTRUCTURED = "unstructured"
    STRUCTURED = "structured"
    OPENFOAM = "openfoam"
    VTK = "vtk"
    STL = "stl"


class SolverTypeDB(str, enum.Enum):
    SIMPLE = "simpleFoam"
    PIMPLE = "pimpleFoam"
    PISOF = "pisoFoam"
    INTER = "interFoam"
    RHO = "rhoCentralFoam"
    DNS = "dnsFoam"


class SimulationStatusDB(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OptimizationStatusDB(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatusDB(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(Base):
    """Project database model."""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ProjectStatusDB), default=ProjectStatusDB.DRAFT)
    geometry_format = Column(SQLEnum(GeometryFormatDB), default=GeometryFormatDB.STEP)
    mesh_format = Column(SQLEnum(MeshFormatDB), default=MeshFormatDB.OPENFOAM)
    solver_type = Column(SQLEnum(SolverTypeDB), default=SolverTypeDB.SIMPLE)
    geometry_path = Column(String(512), nullable=True)
    mesh_path = Column(String(512), nullable=True)
    case_path = Column(String(512), nullable=True)
    results_path = Column(String(512), nullable=True)
    project_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    geometries = relationship("Geometry", back_populates="project", cascade="all, delete-orphan")
    meshes = relationship("Mesh", back_populates="project", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="project", cascade="all, delete-orphan")
    optimizations = relationship("Optimization", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")
    ai_conversations = relationship("AIConversation", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_project_status", "status"),
        Index("idx_project_created", "created_at"),
    )


class Geometry(Base):
    """Geometry database model."""
    __tablename__ = "geometries"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    format = Column(SQLEnum(GeometryFormatDB), nullable=False)
    file_path = Column(String(512), nullable=False)
    bounding_box = Column(JSON, nullable=True)
    volume = Column(Float, nullable=True)
    surface_area = Column(Float, nullable=True)
    checksum = Column(String(64), nullable=True)
    geometry_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="geometries")
    meshes = relationship("Mesh", back_populates="geometry")

    __table_args__ = (
        Index("idx_geometry_project", "project_id"),
    )


class Mesh(Base):
    """Mesh database model."""
    __tablename__ = "meshes"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    geometry_id = Column(String(36), ForeignKey("geometries.id"), nullable=False)
    name = Column(String(255), nullable=False)
    format = Column(SQLEnum(MeshFormatDB), nullable=False)
    file_path = Column(String(512), nullable=False)
    element_count = Column(Integer, nullable=True)
    node_count = Column(Integer, nullable=True)
    mesh_quality = Column(JSON, nullable=True)
    mesh_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="meshes")
    geometry = relationship("Geometry", back_populates="meshes")
    simulations = relationship("Simulation", back_populates="mesh")

    __table_args__ = (
        Index("idx_mesh_project", "project_id"),
        Index("idx_mesh_geometry", "geometry_id"),
    )


class Simulation(Base):
    """Simulation database model."""
    __tablename__ = "simulations"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    mesh_id = Column(String(36), ForeignKey("meshes.id"), nullable=False)
    name = Column(String(255), nullable=False)
    config = Column(JSON, default=dict)
    status = Column(SQLEnum(SimulationStatusDB), default=SimulationStatusDB.PENDING)
    case_path = Column(String(512), nullable=True)
    results_path = Column(String(512), nullable=True)
    iterations = Column(Integer, nullable=True)
    final_residuals = Column(JSON, nullable=True)
    runtime_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="simulations")
    mesh = relationship("Mesh", back_populates="simulations")
    optimizations = relationship("Optimization", back_populates="simulation")

    __table_args__ = (
        Index("idx_simulation_project", "project_id"),
        Index("idx_simulation_mesh", "mesh_id"),
        Index("idx_simulation_status", "status"),
    )


class Optimization(Base):
    """Optimization database model."""
    __tablename__ = "optimizations"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    simulation_id = Column(String(36), ForeignKey("simulations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    config = Column(JSON, default=dict)
    status = Column(SQLEnum(OptimizationStatusDB), default=OptimizationStatusDB.PENDING)
    best_parameters = Column(JSON, nullable=True)
    best_objective = Column(Float, nullable=True)
    iterations = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="optimizations")
    simulation = relationship("Simulation", back_populates="optimizations")

    __table_args__ = (
        Index("idx_optimization_project", "project_id"),
        Index("idx_optimization_simulation", "simulation_id"),
    )


class Job(Base):
    """Background job database model."""
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    entity_id = Column(String(36), nullable=True)
    job_type = Column(String(50), nullable=False)
    status = Column(SQLEnum(JobStatusDB), default=JobStatusDB.QUEUED)
    progress = Column(Float, default=0.0)
    message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="jobs")

    __table_args__ = (
        Index("idx_job_project", "project_id"),
        Index("idx_job_status", "status"),
    )


class AIConversation(Base):
    """AI conversation history database model."""
    __tablename__ = "ai_conversations"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    messages = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="ai_conversations")

    __table_args__ = (
        Index("idx_ai_conversation_project", "project_id"),
    )


class AIProviderConfigDB(Base):
    """AI provider configuration database model."""
    __tablename__ = "ai_provider_configs"

    id = Column(String(36), primary_key=True)
    provider_type = Column(String(50), nullable=False)
    base_url = Column(String(512), nullable=True)
    model = Column(String(100), nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_ai_provider_active", "is_active"),
    )