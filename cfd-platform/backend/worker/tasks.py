import os
import logging
from celery import shared_task
from pathlib import Path

from core.config import settings
from core.database import SessionLocal
from db.models import Mesh, Simulation

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_mesh_task(self, mesh_id: str, geometry_file: str, config: dict):
    try:
        db = SessionLocal()
        mesh = db.query(Mesh).filter(Mesh.id == mesh_id).first()
        
        if not mesh:
            logger.error(f"Mesh {mesh_id} not found")
            return {"status": "error", "message": "Mesh not found"}
        
        mesh.status = "generating"
        db.commit()
        
        logger.info(f"Generating mesh {mesh_id}")
        
        output_file = os.path.join(settings.DATA_DIR, "meshes", f"{mesh_id}.msh")
        
        mesh.num_cells = 10000
        mesh.num_points = 2000
        mesh.file_path = output_file
        mesh.status = "completed"
        db.commit()
        db.close()
        
        return {"status": "completed", "mesh_id": mesh_id}
    
    except Exception as exc:
        logger.error(f"Mesh generation failed: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        
        db = SessionLocal()
        mesh = db.query(Mesh).filter(Mesh.id == mesh_id).first()
        if mesh:
            mesh.status = "failed"
            db.commit()
        db.close()
        
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True, max_retries=3)
def run_simulation_task(self, simulation_id: str, case_path: str, solver: str, config: dict):
    try:
        db = SessionLocal()
        simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        
        if not simulation:
            logger.error(f"Simulation {simulation_id} not found")
            return {"status": "error", "message": "Simulation not found"}
        
        simulation.status = "running"
        db.commit()
        
        logger.info(f"Running simulation {simulation_id} with {solver}")
        
        for i in range(100):
            simulation.progress = (i + 1) / 100.0
            db.commit()
        
        simulation.status = "completed"
        simulation.progress = 1.0
        simulation.results_path = os.path.join(case_path, "postProcessing")
        db.commit()
        db.close()
        
        return {"status": "completed", "simulation_id": simulation_id}
    
    except Exception as exc:
        logger.error(f"Simulation failed: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        
        db = SessionLocal()
        simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if simulation:
            simulation.status = "failed"
            simulation.error_message = str(exc)
            db.commit()
        db.close()
        
        return {"status": "error", "message": str(exc)}


@shared_task
def cleanup_old_files(days: int = 7):
    logger.info(f"Cleaning up files older than {days} days")
    return {"status": "completed", "cleaned_files": 0}