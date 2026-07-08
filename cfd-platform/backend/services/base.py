"""
Base service class providing common functionality for all services.
Implements the service layer pattern with logging, error handling, and transaction management.
"""

from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from pydantic import BaseModel
import structlog
import uuid
from datetime import datetime

from core.errors import (
    CFDPlatformException,
    ProjectNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)
from core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)


class BaseService(Generic[T]):
    """
    Base service class providing common CRUD operations and utilities.
    
    All domain services should inherit from this class to ensure consistent
    behavior for logging, error handling, and database operations.
    """

    def __init__(self, model: Type[T], session: Session):
        """
        Initialize the service with a model class and database session.
        
        Args:
            model: The SQLAlchemy model class
            session: The database session
        """
        self.model = model
        self.session = session
        self._logger = logger.bind(service=self.__class__.__name__)

    def _generate_id(self) -> str:
        """Generate a new UUID for entities."""
        return str(uuid.uuid4())

    def _now(self) -> datetime:
        """Get current UTC timestamp."""
        return datetime.utcnow()

    def get_by_id(self, id: str) -> Optional[T]:
        """
        Retrieve an entity by its ID.
        
        Args:
            id: The entity UUID
            
        Returns:
            The entity or None if not found
        """
        self._logger.debug("get_by_id", entity_id=id)
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_by_id_or_raise(self, id: str) -> T:
        """
        Retrieve an entity by ID or raise ResourceNotFoundError.
        
        Args:
            id: The entity UUID
            
        Returns:
            The entity
            
        Raises:
            ResourceNotFoundError: If entity not found
        """
        entity = self.get_by_id(id)
        if entity is None:
            self._logger.warning("entity_not_found", entity_id=id, model=self.model.__name__)
            raise ResourceNotFoundError(f"{self.model.__name__} with id '{id}' not found")
        return entity

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Retrieve all entities with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of entities
        """
        self._logger.debug("get_all", skip=skip, limit=limit)
        return self.session.query(self.model).offset(skip).limit(limit).all()

    def count(self) -> int:
        """Count total entities."""
        return self.session.query(self.model).count()

    def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new entity.
        
        Args:
            data: Dictionary of entity data
            
        Returns:
            The created entity
        """
        self._logger.info("creating_entity", model=self.model.__name__)
        entity = self.model(**data)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        self._logger.info("entity_created", entity_id=entity.id)
        return entity

    def update(self, id: str, data: Dict[str, Any]) -> T:
        """
        Update an existing entity.
        
        Args:
            id: The entity UUID
            data: Dictionary of fields to update
            
        Returns:
            The updated entity
            
        Raises:
            ResourceNotFoundError: If entity not found
        """
        self._logger.info("updating_entity", entity_id=id)
        entity = self.get_by_id_or_raise(id)
        
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        entity.updated_at = self._now()
        self.session.commit()
        self.session.refresh(entity)
        self._logger.info("entity_updated", entity_id=id)
        return entity

    def delete(self, id: str) -> bool:
        """
        Delete an entity.
        
        Args:
            id: The entity UUID
            
        Returns:
            True if deleted
            
        Raises:
            ResourceNotFoundError: If entity not found
        """
        self._logger.info("deleting_entity", entity_id=id)
        entity = self.get_by_id_or_raise(id)
        self.session.delete(entity)
        self.session.commit()
        self._logger.info("entity_deleted", entity_id=id)
        return True

    def exists(self, id: str) -> bool:
        """Check if an entity exists."""
        return self.get_by_id(id) is not None

    def save(self, entity: T) -> T:
        """
        Save an entity (create or update).
        
        Args:
            entity: The entity to save
            
        Returns:
            The saved entity
        """
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.session.rollback()

    def flush(self) -> None:
        """Flush pending changes to the database."""
        self.session.flush()


class ProjectService(BaseService):
    """Service for project-related operations."""

    def __init__(self, session: Session):
        super().__init__(model=None, session=session)
        self.model = self._get_model()
        self._logger = logger.bind(service="ProjectService")

    @staticmethod
    def _get_model():
        from models.database import Project
        return Project

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[T]:
        """Get projects by status."""
        return (
            self.session.query(self.model)
            .filter(self.model.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_by_name(self, name: str, skip: int = 0, limit: int = 100) -> List[T]:
        """Search projects by name (case-insensitive)."""
        return (
            self.session.query(self.model)
            .filter(self.model.name.ilike(f"%{name}%"))
            .offset(skip)
            .limit(limit)
            .all()
        )


class GeometryService(BaseService):
    """Service for geometry-related operations."""

    def __init__(self, session: Session):
        super().__init__(model=None, session=session)
        self.model = self._get_model()
        self._logger = logger.bind(service="GeometryService")

    @staticmethod
    def _get_model():
        from models.database import Geometry
        return Geometry

    def get_by_project(self, project_id: str) -> List[T]:
        """Get all geometries for a project."""
        return (
            self.session.query(self.model)
            .filter(self.model.project_id == project_id)
            .all()
        )

    def get_latest(self, project_id: str) -> Optional[T]:
        """Get the most recent geometry for a project."""
        return (
            self.session.query(self.model)
            .filter(self.model.project_id == project_id)
            .order_by(self.model.created_at.desc())
            .first()
        )


class MeshService(BaseService):
    """Service for mesh-related operations."""

    def __init__(self, session: Session):
        super().__init__(model=None, session=session)
        self.model = self._get_model()
        self._logger = logger.bind(service="MeshService")

    @staticmethod
    def _get_model():
        from models.database import Mesh
        return Mesh

    def get_by_project(self, project_id: str) -> List[T]:
        """Get all meshes for a project."""
        return (
            self.session.query(self.model)
            .filter(self.model.project_id == project_id)
            .all()
        )

    def get_by_geometry(self, geometry_id: str) -> List[T]:
        """Get all meshes for a geometry."""
        return (
            self.session.query(self.model)
            .filter(self.model.geometry_id == geometry_id)
            .all()
        )


class SimulationService(BaseService):
    """Service for simulation-related operations."""

    def __init__(self, session: Session):
        super().__init__(model=None, session=session)
        self.model = self._get_model()
        self._logger = logger.bind(service="SimulationService")

    @staticmethod
    def _get_model():
        from models.database import Simulation
        return Simulation

    def get_by_project(self, project_id: str) -> List[T]:
        """Get all simulations for a project."""
        return (
            self.session.query(self.model)
            .filter(self.model.project_id == project_id)
            .all()
        )

    def get_by_mesh(self, mesh_id: str) -> List[T]:
        """Get all simulations for a mesh."""
        return (
            self.session.query(self.model)
            .filter(self.model.mesh_id == mesh_id)
            .all()
        )

    def get_by_status(self, status: str) -> List[T]:
        """Get all simulations with a specific status."""
        return (
            self.session.query(self.model)
            .filter(self.model.status == status)
            .all()
        )


class OptimizationService(BaseService):
    """Service for optimization-related operations."""

    def __init__(self, session: Session):
        super().__init__(model=None, session=session)
        self.model = self._get_model()
        self._logger = logger.bind(service="OptimizationService")

    @staticmethod
    def _get_model():
        from models.database import Optimization
        return Optimization

    def get_by_project(self, project_id: str) -> List[T]:
        """Get all optimizations for a project."""
        return (
            self.session.query(self.model)
            .filter(self.model.project_id == project_id)
            .all()
        )

    def get_by_simulation(self, simulation_id: str) -> List[T]:
        """Get all optimizations for a simulation."""
        return (
            self.session.query(self.model)
            .filter(self.model.simulation_id == simulation_id)
            .all()
        )


class JobService(BaseService):
    """Service for background job operations."""

    def __init__(self, session: Session):
        super().__init__(model=None, session=session)
        self.model = self._get_model()
        self._logger = logger.bind(service="JobService")

    @staticmethod
    def _get_model():
        from models.database import Job
        return Job

    def get_by_project(self, project_id: str) -> List[T]:
        """Get all jobs for a project."""
        return (
            self.session.query(self.model)
            .filter(self.model.project_id == project_id)
            .all()
        )

    def get_pending(self) -> List[T]:
        """Get all pending jobs."""
        from models.database import JobStatusDB
        return (
            self.session.query(self.model)
            .filter(self.model.status == JobStatusDB.QUEUED)
            .order_by(self.model.created_at)
            .all()
        )

    def update_progress(self, job_id: str, progress: float, message: str = None) -> T:
        """Update job progress."""
        from models.database import JobStatusDB
        job = self.get_by_id_or_raise(job_id)
        job.progress = progress
        if message:
            job.message = message
        if progress > 0 and job.status == JobStatusDB.QUEUED:
            job.status = JobStatusDB.RUNNING
            job.started_at = self._now()
        self.session.commit()
        self.session.refresh(job)
        return job

    def complete(self, job_id: str, result: Dict[str, Any] = None) -> T:
        """Mark a job as completed."""
        from models.database import JobStatusDB
        job = self.get_by_id_or_raise(job_id)
        job.status = JobStatusDB.COMPLETED
        job.progress = 100.0
        job.result = result
        job.completed_at = self._now()
        self.session.commit()
        self.session.refresh(job)
        return job

    def fail(self, job_id: str, error: str) -> T:
        """Mark a job as failed."""
        from models.database import JobStatusDB
        job = self.get_by_id_or_raise(job_id)
        job.status = JobStatusDB.FAILED
        job.error = error
        job.completed_at = self._now()
        self.session.commit()
        self.session.refresh(job)
        return job