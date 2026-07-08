import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class OptimizationService:
    def __init__(self):
        self.data_dir = "/data"
    
    def create_optimization(
        self,
        name: str,
        project_id: str,
        simulation_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        optimization_id = str(uuid.uuid4())
        
        return {
            "id": optimization_id,
            "name": name,
            "project_id": project_id,
            "simulation_id": simulation_id,
            "config": config,
            "status": "pending",
            "progress": 0.0,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def run_optimization(
        self,
        optimization_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Dispatch optimization to Celery task.
        
        This method dispatches the actual optimization to a background
        Celery task instead of returning stub data.
        """
        try:
            from backend.tasks.optimization_tasks import run_optimization
            
            logger.info(f"Dispatching optimization {optimization_id}")
            
            # Dispatch to Celery task and return task ID for tracking
            task = run_optimization.delay(
                optimization_id=optimization_id,
                job_id=config.get("job_id"),
                optimization_config={
                    "algorithm": config.get("algorithm", "ngopt"),
                    "max_iterations": config.get("max_iterations", 100),
                    "parameters": config.get("parameters", []),
                    "objectives": config.get("objectives", {}),
                    "constraints": config.get("constraints", []),
                },
                project_id=config.get("project_id"),
            )
            
            return {
                "task_id": task.id,
                "status": "dispatched",
                "message": "Optimization dispatched to background task",
            }
        except Exception as e:
            logger.error(f"Optimization dispatch failed: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    def get_algorithm_options(self) -> List[str]:
        return ["ngopt", "cmaes", "pso", "cobyla", "Nelder-Mead"]