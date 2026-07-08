"""
Celery tasks for mesh generation operations.
"""

from typing import Dict, Any, Optional
from celery import Task
from celery.utils.log import get_task_logger

from backend.celery_app import celery_app
from backend.services.integration import GmshClient
from backend.services.base import MeshService, JobService
from backend.websocket.manager import get_websocket_manager, EventType
from core.config import get_settings
from core.database import get_db_context

logger = get_task_logger(__name__)
settings = get_settings()


class MeshTask(Task):
    """Base task for mesh operations."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error("mesh_task_failed", task_id=task_id, error=str(exc))
        
        mesh_id = kwargs.get("mesh_id")
        job_id = kwargs.get("job_id")
        
        if mesh_id:
            with get_db_context() as db:
                mesh_service = MeshService(db)
                mesh_service.update(mesh_id, {"status": "failed", "error": str(exc)})
        
        if job_id:
            ws_manager = get_websocket_manager()
            # Emit failure event
            # Note: In production, get project_id from mesh
            logger.info("job_failed_emit", job_id=job_id)


@celery_app.task(bind=True, base=MeshTask, name="tasks.generate_mesh")
def generate_mesh(
    self,
    mesh_id: str,
    geometry_id: str,
    job_id: str,
    mesh_config: Dict[str, Any],
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate mesh from geometry.
    
    Args:
        mesh_id: Mesh record ID
        geometry_id: Source geometry ID
        job_id: Job tracking ID
        mesh_config: Mesh generation parameters
        project_id: Project for WebSocket updates
        
    Returns:
        Mesh generation result
    """
    logger.info("generate_mesh_started", mesh_id=mesh_id, geometry_id=geometry_id)
    
    ws_manager = get_websocket_manager()
    
    try:
        with get_db_context() as db:
            mesh_service = MeshService(db)
            job_service = JobService(db)
            
            # Update job status
            job_service.update_progress(job_id, 0.1, "Initializing mesh generation")
            
            # Update mesh status
            mesh_service.update(mesh_id, {"status": "running"})
            
            # Get geometry file path
            geometry = mesh_service.get(geometry_id)
            if not geometry:
                raise ValueError(f"Geometry not found: {geometry_id}")
            
            geometry_path = geometry.file_path
            
            # Initialize Gmsh client
            gmsh_client = GmshClient()
            
            # Update progress
            job_service.update_progress(job_id, 0.3, "Generating mesh with Gmsh")
            
            # Generate mesh
            mesh_info = gmsh_client.generate_mesh(
                geometry_path=geometry_path,
                mesh_type=mesh_config.get("mesh_type", "tetrahedral"),
                element_size=mesh_config.get("element_size", 0.1),
                refinement=mesh_config.get("refinement", 0),
                output_path=mesh_config.get("output_path"),
            )
            
            job_service.update_progress(job_id, 0.8, "Finalizing mesh")
            
            # Update mesh record
            mesh_service.update(mesh_id, {
                "status": "completed",
                "file_path": mesh_info["output_file"],
                "num_cells": mesh_info["num_cells"],
                "num_points": mesh_info["num_points"],
                "mesh_quality": mesh_info.get("quality", {}),
            })
            
            job_service.complete(job_id, {
                "mesh_id": mesh_id,
                "num_cells": mesh_info["num_cells"],
                "num_points": mesh_info["num_points"],
            })
            
            # Emit WebSocket events
            ws_manager.broadcast(
                EventType.MESH_COMPLETED,
                {
                    "mesh_id": mesh_id,
                    "geometry_id": geometry_id,
                    "num_cells": mesh_info["num_cells"],
                    "num_points": mesh_info["num_points"],
                },
                project_id=project_id,
            )
            
            logger.info("generate_mesh_completed", mesh_id=mesh_id)
            
            return {
                "mesh_id": mesh_id,
                "file_path": mesh_info["output_file"],
                "num_cells": mesh_info["num_cells"],
                "num_points": mesh_info["num_points"],
            }
            
    except Exception as e:
        logger.error("generate_mesh_failed", mesh_id=mesh_id, error=str(e))
        
        with get_db_context() as db:
            mesh_service = MeshService(db)
            job_service = JobService(db)
            
            mesh_service.update(mesh_id, {"status": "failed", "error": str(e)})
            job_service.fail(job_id, str(e))
        
        ws_manager.broadcast(
            EventType.JOB_FAILED,
            {"job_id": job_id, "error": str(e)},
            project_id=project_id,
        )
        
        raise


@celery_app.task(bind=True, base=MeshTask, name="tasks.refine_mesh")
def refine_mesh(
    self,
    mesh_id: str,
    source_mesh_id: str,
    job_id: str,
    refinement_config: Dict[str, Any],
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Refine an existing mesh.
    
    Args:
        mesh_id: New mesh record ID
        source_mesh_id: Source mesh to refine
        job_id: Job tracking ID
        refinement_config: Refinement parameters
        project_id: Project for WebSocket updates
        
    Returns:
        Refined mesh result
    """
    logger.info("refine_mesh_started", mesh_id=mesh_id, source_mesh_id=source_mesh_id)
    
    ws_manager = get_websocket_manager()
    
    try:
        with get_db_context() as db:
            mesh_service = MeshService(db)
            job_service = JobService(db)
            
            job_service.update_progress(job_id, 0.1, "Starting mesh refinement")
            
            # Get source mesh
            source_mesh = mesh_service.get(source_mesh_id)
            if not source_mesh:
                raise ValueError(f"Source mesh not found: {source_mesh_id}")
            
            # Initialize Gmsh client
            gmsh_client = GmshClient()
            
            job_service.update_progress(job_id, 0.3, "Refining mesh")
            
            # Refine mesh
            mesh_info = gmsh_client.refine_mesh(
                input_path=source_mesh.file_path,
                refinement_level=refinement_config.get("refinement_level", 1),
                output_path=refinement_config.get("output_path"),
            )
            
            job_service.update_progress(job_id, 0.9, "Finalizing")
            
            # Update mesh record
            mesh_service.update(mesh_id, {
                "status": "completed",
                "file_path": mesh_info["output_file"],
                "num_cells": mesh_info["num_cells"],
                "num_points": mesh_info["num_points"],
                "parent_mesh_id": source_mesh_id,
            })
            
            job_service.complete(job_id, {
                "mesh_id": mesh_id,
                "num_cells": mesh_info["num_cells"],
            })
            
            ws_manager.broadcast(
                EventType.MESH_COMPLETED,
                {"mesh_id": mesh_id, "refined_from": source_mesh_id},
                project_id=project_id,
            )
            
            return {
                "mesh_id": mesh_id,
                "file_path": mesh_info["output_file"],
                "num_cells": mesh_info["num_cells"],
            }
            
    except Exception as e:
        logger.error("refine_mesh_failed", mesh_id=mesh_id, error=str(e))
        
        with get_db_context() as db:
            mesh_service = MeshService(db)
            job_service = JobService(db)
            
            mesh_service.update(mesh_id, {"status": "failed", "error": str(e)})
            job_service.fail(job_id, str(e))
        
        raise


@celery_app.task(bind=True, base=MeshTask, name="tasks.convert_mesh")
def convert_mesh(
    self,
    mesh_id: str,
    input_format: str,
    output_format: str,
    job_id: str,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert mesh between formats.
    
    Args:
        mesh_id: Mesh record ID
        input_format: Source format
        output_format: Target format
        job_id: Job tracking ID
        project_id: Project for WebSocket updates
        
    Returns:
        Conversion result
    """
    logger.info(
        "convert_mesh_started",
        mesh_id=mesh_id,
        input_format=input_format,
        output_format=output_format,
    )
    
    ws_manager = get_websocket_manager()
    
    try:
        with get_db_context() as db:
            mesh_service = MeshService(db)
            job_service = JobService(db)
            
            job_service.update_progress(job_id, 0.1, "Converting mesh format")
            
            # Get mesh
            mesh = mesh_service.get(mesh_id)
            if not mesh:
                raise ValueError(f"Mesh not found: {mesh_id}")
            
            # Import meshio
            import meshio
            
            job_service.update_progress(job_id, 0.5, "Reading mesh")
            
            # Read mesh
            input_mesh = meshio.read(mesh.file_path)
            
            job_service.update_progress(job_id, 0.7, "Writing mesh")
            
            # Write converted mesh
            output_path = mesh.file_path.replace(f".{input_format}", f".{output_format}")
            meshio.write(output_path, input_mesh)
            
            job_service.update_progress(job_id, 0.9, "Finalizing")
            
            # Update mesh record
            mesh_service.update(mesh_id, {
                "file_path": output_path,
                "format": output_format,
            })
            
            job_service.complete(job_id, {"output_path": output_path})
            
            return {"mesh_id": mesh_id, "output_path": output_path}
            
    except Exception as e:
        logger.error("convert_mesh_failed", mesh_id=mesh_id, error=str(e))
        
        with get_db_context() as db:
            job_service = JobService(db)
            job_service.fail(job_id, str(e))
        
        raise