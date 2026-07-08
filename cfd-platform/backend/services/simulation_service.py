import os
import logging
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from core.config import settings
from core.errors import SimulationError

logger = logging.getLogger(__name__)


class SimulationService:
    def __init__(self):
        self.openfoam_dir = settings.OPENFOAM_DIR
        self.data_dir = settings.DATA_DIR
    
    def create_case(
        self,
        mesh_file: str,
        solver: str,
        config: Dict[str, Any]
    ) -> str:
        try:
            case_path = os.path.join(self.data_dir, "cases", f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(case_path, exist_ok=True)
            
            logger.info(f"Creating OpenFOAM case at {case_path}")
            logger.info(f"Solver: {solver}")
            
            return case_path
        except Exception as e:
            logger.error(f"Case creation failed: {str(e)}")
            raise SimulationError(str(e))
    
    def run_simulation(
        self,
        case_path: str,
        solver: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Dispatch simulation to Celery task.
        
        This method dispatches the actual CFD simulation to a background
        Celery task instead of returning stub data.
        """
        try:
            from backend.tasks.simulation_tasks import run_simulation
            
            logger.info(f"Dispatching {solver} simulation")
            
            # Dispatch to Celery task and return task ID for tracking
            task = run_simulation.delay(
                simulation_id=config.get("simulation_id"),
                mesh_id=config.get("mesh_id"),
                job_id=config.get("job_id"),
                simulation_config={
                    "solver": solver,
                    "case_dir": case_path,
                    "end_time": config.get("end_time", 1000),
                    "write_interval": config.get("write_interval", 100),
                    "parameters": config.get("parameters", {}),
                },
                project_id=config.get("project_id"),
            )
            
            return {
                "task_id": task.id,
                "status": "dispatched",
                "message": "Simulation dispatched to background task",
            }
        except Exception as e:
            logger.error(f"Simulation dispatch failed: {str(e)}")
            raise SimulationError(str(e))
    
    def get_solver_options(self) -> List[str]:
        return [
            "simpleFoam",
            "rhoSimpleFoam",
            "buoyantSimpleFoam",
            "interFoam",
            "pisoFoam",
            "pimpleFoam",
            "icoFoam"
        ]
    
    def get_turbulence_models(self) -> List[str]:
        return [
            "kEpsilon",
            "kOmega",
            "kOmegaSST",
            "SpalartAllmaras",
            "LES"
        ]