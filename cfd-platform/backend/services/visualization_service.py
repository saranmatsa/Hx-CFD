import os
import logging
from typing import Optional, Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)


class VisualizationService:
    def __init__(self):
        self.data_dir = "/data"
    
    def get_mesh_geometry(self, case_path: Optional[str]) -> Dict[str, Any]:
        if not case_path or not os.path.exists(case_path):
            num_points = 1000
            points = np.random.rand(num_points, 3).tolist()
            connectivity = []
            for i in range(0, num_points - 2, 3):
                connectivity.extend([i, i + 1, i + 2])
        else:
            points = [[0, 0, 0], [1, 0, 0], [0.5, 1, 0], [0.5, 0.5, 1]]
            connectivity = [0, 1, 2, 0, 1, 3, 0, 2, 3, 1, 2, 3]
        
        return {
            "points": points,
            "connectivity": connectivity,
            "bounding_box": {
                "min": [0, 0, 0],
                "max": [1, 1, 1]
            }
        }
    
    def get_scalar_field(
        self,
        results_path: Optional[str],
        field_name: str,
        time_step: Optional[float] = None
    ) -> Dict[str, Any]:
        num_points = 1000
        values = np.random.rand(num_points).tolist()
        
        return {
            "field_name": field_name,
            "points": np.random.rand(num_points, 3).tolist(),
            "values": values,
            "min_value": min(values),
            "max_value": max(values),
            "time_step": time_step or 0.0
        }
    
    def get_vector_field(
        self,
        results_path: Optional[str],
        field_name: str,
        time_step: Optional[float] = None
    ) -> Dict[str, Any]:
        num_points = 500
        points = np.random.rand(num_points, 3).tolist()
        vectors = np.random.rand(num_points, 3).tolist()
        
        return {
            "field_name": field_name,
            "points": points,
            "vectors": vectors,
            "scale": 1.0,
            "time_step": time_step or 0.0
        }
    
    def get_available_fields(self, results_path: Optional[str]) -> List[str]:
        return ["p", "U", "T", "k", "epsilon", "omega", "nuTilda"]
    
    def get_time_steps(self, results_path: Optional[str]) -> List[float]:
        return [0.0, 0.05, 0.1, 0.15, 0.2]