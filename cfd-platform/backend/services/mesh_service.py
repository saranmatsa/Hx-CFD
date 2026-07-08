import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from core.config import settings
from core.errors import MeshGenerationError

logger = logging.getLogger(__name__)


class MeshService:
    def __init__(self):
        self.gmsh_bin = settings.GMSH_BIN
        self.data_dir = settings.DATA_DIR
    
    def generate_mesh(
        self,
        geometry_file: str,
        output_file: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Dispatch mesh generation to Celery task.
        
        This method dispatches the actual mesh generation to a background
        Celery task instead of returning stub data.
        """
        try:
            from backend.tasks.mesh_tasks import generate_mesh
            
            element_size = config.get("element_size", 0.1)
            growth_rate = config.get("growth_rate", 1.2)
            num_boundary_layers = config.get("num_boundary_layers", 3)
            
            logger.info(f"Dispatching mesh generation from {geometry_file}")
            logger.info(f"Element size: {element_size}, Growth rate: {growth_rate}")
            
            # Dispatch to Celery task and return task ID for tracking
            task = generate_mesh.delay(
                mesh_id=config.get("mesh_id"),
                geometry_id=config.get("geometry_id"),
                job_id=config.get("job_id"),
                mesh_config={
                    "element_size": element_size,
                    "growth_rate": growth_rate,
                    "num_boundary_layers": num_boundary_layers,
                    "output_path": output_file,
                },
                project_id=config.get("project_id"),
            )
            
            return {
                "task_id": task.id,
                "status": "dispatched",
                "message": "Mesh generation dispatched to background task",
            }
        except Exception as e:
            logger.error(f"Mesh generation dispatch failed: {str(e)}")
            raise MeshGenerationError(str(e))
    
    def validate_mesh(self, mesh_file: str) -> bool:
        if not os.path.exists(mesh_file):
            return False
        
        file_ext = Path(mesh_file).suffix.lower()
        valid_extensions = [".msh", ".stl", ".obj", ".vtk", ".vtu", ".vtp"]
        
        return file_ext in valid_extensions
    
    def get_mesh_info(self, mesh_file: str) -> Dict[str, Any]:
        return {
            "num_cells": 0,
            "num_points": 0,
            "bounding_box": {
                "min": [0, 0, 0],
                "max": [1, 1, 1]
            }
        }