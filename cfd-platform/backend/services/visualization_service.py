import os
import logging
from typing import Optional, Dict, Any, List
import numpy as np

from core.config import settings
from core.errors import VisualizationError

logger = logging.getLogger(__name__)


class VisualizationService:
    def __init__(self):
        self.data_dir = settings.DATA_DIR
        self._vtk_client = None
    
    def _get_vtk_client(self):
        """Lazy-load VTK client to avoid import errors."""
        if self._vtk_client is None:
            from backend.services.integration import VTKClient
            self._vtk_client = VTKClient()
        return self._vtk_client
    
    def get_mesh_geometry(self, case_path: Optional[str]) -> Dict[str, Any]:
        """
        Get mesh geometry from VTK data.
        
        Args:
            case_path: Path to simulation case directory
            
        Returns:
            Mesh geometry data
        """
        try:
            if not case_path or not os.path.exists(case_path):
                raise VisualizationError(f"Case path not found: {case_path}")
            
            vtk_client = self._get_vtk_client()
            geometry = vtk_client.read_mesh(case_path)
            
            return {
                "points": geometry["points"],
                "connectivity": geometry["connectivity"],
                "bounding_box": geometry["bounding_box"],
                "num_cells": geometry["num_cells"],
                "num_points": geometry["num_points"],
            }
        except Exception as e:
            logger.error(f"Failed to get mesh geometry: {str(e)}")
            raise VisualizationError(str(e))
    
    def get_scalar_field(
        self,
        results_path: Optional[str],
        field_name: str,
        time_step: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get scalar field data from VTK results.
        
        Args:
            results_path: Path to simulation results
            field_name: Name of the scalar field
            time_step: Optional time step to extract
            
        Returns:
            Scalar field data
        """
        try:
            if not results_path or not os.path.exists(results_path):
                raise VisualizationError(f"Results path not found: {results_path}")
            
            vtk_client = self._get_vtk_client()
            field_data = vtk_client.read_scalar_field(
                results_path,
                field_name,
                time_step=time_step,
            )
            
            return {
                "field_name": field_name,
                "points": field_data["points"],
                "values": field_data["values"],
                "min_value": field_data["min_value"],
                "max_value": field_data["max_value"],
                "time_step": time_step or 0.0,
            }
        except Exception as e:
            logger.error(f"Failed to get scalar field: {str(e)}")
            raise VisualizationError(str(e))
    
    def get_vector_field(
        self,
        results_path: Optional[str],
        field_name: str,
        time_step: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get vector field data from VTK results.
        
        Args:
            results_path: Path to simulation results
            field_name: Name of the vector field
            time_step: Optional time step to extract
            
        Returns:
            Vector field data
        """
        try:
            if not results_path or not os.path.exists(results_path):
                raise VisualizationError(f"Results path not found: {results_path}")
            
            vtk_client = self._get_vtk_client()
            field_data = vtk_client.read_vector_field(
                results_path,
                field_name,
                time_step=time_step,
            )
            
            return {
                "field_name": field_name,
                "points": field_data["points"],
                "vectors": field_data["vectors"],
                "scale": field_data.get("scale", 1.0),
                "time_step": time_step or 0.0,
            }
        except Exception as e:
            logger.error(f"Failed to get vector field: {str(e)}")
            raise VisualizationError(str(e))
    
    def get_available_fields(self, results_path: Optional[str]) -> List[str]:
        """
        Get list of available fields in results.
        
        Args:
            results_path: Path to simulation results
            
        Returns:
            List of available field names
        """
        try:
            if not results_path or not os.path.exists(results_path):
                return ["p", "U", "T", "k", "epsilon", "omega", "nuTilda"]
            
            vtk_client = self._get_vtk_client()
            return vtk_client.list_fields(results_path)
        except Exception as e:
            logger.warning(f"Failed to list fields, returning defaults: {e}")
            return ["p", "U", "T", "k", "epsilon", "omega", "nuTilda"]
    
    def get_time_steps(self, results_path: Optional[str]) -> List[float]:
        """
        Get list of available time steps in results.
        
        Args:
            results_path: Path to simulation results
            
        Returns:
            List of available time steps
        """
        try:
            if not results_path or not os.path.exists(results_path):
                return [0.0]
            
            vtk_client = self._get_vtk_client()
            return vtk_client.list_time_steps(results_path)
        except Exception as e:
            logger.warning(f"Failed to list time steps, returning default: {e}")
            return [0.0]