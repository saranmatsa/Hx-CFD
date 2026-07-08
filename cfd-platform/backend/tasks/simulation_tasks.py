"""
Celery tasks for simulation operations.
"""

from typing import Dict, Any, Optional, List
from celery import Task
from celery.utils.log import get_task_logger
import asyncio

from backend.celery_app import celery_app
from backend.services.integration import OpenFOAMClient
from backend.services.base import SimulationService, JobService
from backend.websocket.manager import get_websocket_manager, EventType
from core.config import get_settings
from core.database import get_db_context

logger = get_task_logger(__name__)
settings = get_settings()


class SimulationTask(Task):
    """Base task for simulation operations."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error("simulation_task_failed", task_id=task_id, error=str(exc))
        
        simulation_id = kwargs.get("simulation_id")
        job_id = kwargs.get("job_id")
        
        if simulation_id:
            with get_db_context() as db:
                sim_service = SimulationService(db)
                sim_service.update(simulation_id, {"status": "failed", "error": str(exc)})
        
        if job_id:
            ws_manager = get_websocket_manager()
            logger.info("simulation_failed_emit", job_id=job_id)


@celery_app.task(bind=True, base=SimulationTask, name="tasks.run_simulation")
def run_simulation(
    self,
    simulation_id: str,
    mesh_id: str,
    job_id: str,
    simulation_config: Dict[str, Any],
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run CFD simulation.
    
    Args:
        simulation_id: Simulation record ID
        mesh_id: Mesh to simulate
        job_id: Job tracking ID
        simulation_config: Simulation parameters
        project_id: Project for WebSocket updates
        
    Returns:
        Simulation result
    """
    logger.info("run_simulation_started", simulation_id=simulation_id, mesh_id=mesh_id)
    
    ws_manager = get_websocket_manager()
    
    try:
        with get_db_context() as db:
            sim_service = SimulationService(db)
            job_service = JobService(db)
            
            # Update status
            job_service.update_progress(job_id, 0.05, "Initializing simulation")
            sim_service.update(simulation_id, {"status": "running"})
            
            # Get mesh
            from backend.services.base import MeshService
            mesh_service = MeshService(db)
            mesh = mesh_service.get(mesh_id)
            
            if not mesh:
                raise ValueError(f"Mesh not found: {mesh_id}")
            
            # Initialize OpenFOAM client
            of_client = OpenFOAMClient(
                case_dir=simulation_config.get("case_dir"),
                solver=simulation_config.get("solver", "simpleFoam"),
            )
            
            job_service.update_progress(job_id, 0.1, "Setting up case")
            
            # Setup case
            case_path = of_client.setup_case(
                mesh_path=mesh.file_path,
                solver=simulation_config.get("solver", "simpleFoam"),
                parameters=simulation_config.get("parameters", {}),
            )
            
            job_service.update_progress(job_id, 0.2, "Starting simulation")
            
            # Run simulation with progress monitoring
            def progress_callback(progress: float, residuals: Dict[str, float], iteration: int):
                """Callback for simulation progress."""
                # Update job progress (0.2 to 0.9 range)
                job_progress = 0.2 + (progress * 0.7)
                job_service.update_progress(
                    job_id,
                    job_progress,
                    f"Running simulation - iteration {iteration}",
                )
                
                # Emit residuals via WebSocket
                ws_manager.broadcast(
                    EventType.SIMULATION_RESIDUALS,
                    {
                        "simulation_id": simulation_id,
                        "residuals": residuals,
                        "iteration": iteration,
                        "progress": progress,
                    },
                    project_id=project_id,
                )
                
                # Emit progress event
                ws_manager.broadcast(
                    EventType.SIMULATION_PROGRESS,
                    {
                        "simulation_id": simulation_id,
                        "progress": job_progress,
                        "iteration": iteration,
                    },
                    project_id=project_id,
                )
            
            results = of_client.run_simulation(
                case_path=case_path,
                end_time=simulation_config.get("end_time", 1000),
                write_interval=simulation_config.get("write_interval", 100),
                progress_callback=progress_callback,
            )
            
            job_service.update_progress(job_id, 0.95, "Processing results")
            
            # Get results
            results_data = of_client.get_results(case_path)
            
            # Update simulation record
            sim_service.update(simulation_id, {
                "status": "completed",
                "results": results_data,
                "final_residuals": results.get("final_residuals", {}),
            })
            
            job_service.complete(job_id, {
                "simulation_id": simulation_id,
                "results": results_data,
            })
            
            # Emit completion event
            ws_manager.broadcast(
                EventType.SIMULATION_COMPLETED,
                {
                    "simulation_id": simulation_id,
                    "results": results_data,
                },
                project_id=project_id,
            )
            
            logger.info("run_simulation_completed", simulation_id=simulation_id)
            
            return {
                "simulation_id": simulation_id,
                "results": results_data,
            }
            
    except Exception as e:
        logger.error("run_simulation_failed", simulation_id=simulation_id, error=str(e))
        
        with get_db_context() as db:
            sim_service = SimulationService(db)
            job_service = JobService(db)
            
            sim_service.update(simulation_id, {"status": "failed", "error": str(e)})
            job_service.fail(job_id, str(e))
        
        ws_manager.broadcast(
            EventType.JOB_FAILED,
            {"job_id": job_id, "error": str(e)},
            project_id=project_id,
        )
        
        raise


@celery_app.task(bind=True, base=SimulationTask, name="tasks.stop_simulation")
def stop_simulation(
    self,
    simulation_id: str,
    job_id: str,
) -> Dict[str, Any]:
    """
    Stop a running simulation.
    
    Args:
        simulation_id: Simulation to stop
        job_id: Job tracking ID
        
    Returns:
        Stop result
    """
    logger.info("stop_simulation_requested", simulation_id=simulation_id)
    
    try:
        with get_db_context() as db:
            sim_service = SimulationService(db)
            job_service = JobService(db)
            
            # Get simulation
            simulation = sim_service.get(simulation_id)
            if not simulation:
                raise ValueError(f"Simulation not found: {simulation_id}")
            
            # Initialize OpenFOAM client
            of_client = OpenFOAMClient()
            
            # Stop simulation
            of_client.stop_simulation(simulation.case_path)
            
            # Update status
            sim_service.update(simulation_id, {"status": "stopped"})
            job_service.complete(job_id, {"stopped": True})
            
            return {"simulation_id": simulation_id, "stopped": True}
            
    except Exception as e:
        logger.error("stop_simulation_failed", simulation_id=simulation_id, error=str(e))
        
        with get_db_context() as db:
            job_service = JobService(db)
            job_service.fail(job_id, str(e))
        
        raise


@celery_app.task(bind=True, base=SimulationTask, name="tasks.extract_results")
def extract_results(
    self,
    simulation_id: str,
    extraction_config: Dict[str, Any],
    job_id: str,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract results from simulation.
    
    Args:
        simulation_id: Simulation to extract from
        extraction_config: Extraction parameters
        job_id: Job tracking ID
        project_id: Project for WebSocket updates
        
    Returns:
        Extracted results
    """
    logger.info("extract_results_started", simulation_id=simulation_id)
    
    try:
        with get_db_context() as db:
            sim_service = SimulationService(db)
            job_service = JobService(db)
            
            job_service.update_progress(job_id, 0.1, "Extracting results")
            
            # Get simulation
            simulation = sim_service.get(simulation_id)
            if not simulation:
                raise ValueError(f"Simulation not found: {simulation_id}")
            
            # Initialize OpenFOAM client
            of_client = OpenFOAMClient()
            
            # Extract results based on type
            extraction_type = extraction_config.get("type", "fields")
            
            if extraction_type == "fields":
                results = of_client.get_results(simulation.case_path)
            elif extraction_type == "residuals":
                results = of_client.get_residuals(simulation.case_path)
            elif extraction_type == "forces":
                results = of_client.get_forces(simulation.case_path)
            elif extraction_type == "slices":
                results = of_client.extract_slices(
                    simulation.case_path,
                    extraction_config.get("positions", []),
                    extraction_config.get("fields", []),
                )
            else:
                raise ValueError(f"Unknown extraction type: {extraction_type}")
            
            job_service.update_progress(job_id, 0.9, "Finalizing")
            job_service.complete(job_id, {"results": results})
            
            return {"simulation_id": simulation_id, "results": results}
            
    except Exception as e:
        logger.error("extract_results_failed", simulation_id=simulation_id, error=str(e))
        
        with get_db_context() as db:
            job_service = JobService(db)
            job_service.fail(job_id, str(e))
        
        raise


@celery_app.task(bind=True, base=SimulationTask, name="tasks.post_process")
def post_process(
    self,
    simulation_id: str,
    post_config: Dict[str, Any],
    job_id: str,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Post-process simulation results.
    
    Args:
        simulation_id: Simulation to post-process
        post_config: Post-processing parameters
        job_id: Job tracking ID
        project_id: Project for WebSocket updates
        
    Returns:
        Post-processing result
    """
    logger.info("post_process_started", simulation_id=simulation_id)
    
    ws_manager = get_websocket_manager()
    
    try:
        with get_db_context() as db:
            sim_service = SimulationService(db)
            job_service = JobService(db)
            
            job_service.update_progress(job_id, 0.1, "Starting post-processing")
            
            # Get simulation
            simulation = sim_service.get(simulation_id)
            if not simulation:
                raise ValueError(f"Simulation not found: {simulation_id}")
            
            # Initialize OpenFOAM client
            of_client = OpenFOAMClient()
            
            post_results = {}
            
            # Calculate statistics
            if post_config.get("calculate_statistics", True):
                job_service.update_progress(job_id, 0.3, "Calculating statistics")
                stats = of_client.calculate_statistics(
                    simulation.case_path,
                    post_config.get("fields", ["U", "p"]),
                )
                post_results["statistics"] = stats
            
            # Generate report
            if post_config.get("generate_report", False):
                job_service.update_progress(job_id, 0.6, "Generating report")
                report = of_client.generate_report(
                    simulation.case_path,
                    post_config.get("report_format", "json"),
                )
                post_results["report"] = report
            
            # Export data
            if post_config.get("export_data", False):
                job_service.update_progress(job_id, 0.8, "Exporting data")
                export_path = of_client.export_results(
                    simulation.case_path,
                    post_config.get("export_format", "csv"),
                    post_config.get("fields", []),
                )
                post_results["export_path"] = export_path
            
            job_service.update_progress(job_id, 0.95, "Finalizing")
            job_service.complete(job_id, post_results)
            
            # Update simulation with post-processed data
            sim_service.update(simulation_id, {
                "post_results": post_results,
            })
            
            ws_manager.broadcast(
                EventType.SIMULATION_COMPLETED,
                {
                    "simulation_id": simulation_id,
                    "post_results": post_results,
                },
                project_id=project_id,
            )
            
            return {"simulation_id": simulation_id, "post_results": post_results}
            
    except Exception as e:
        logger.error("post_process_failed", simulation_id=simulation_id, error=str(e))
        
        with get_db_context() as db:
            job_service = JobService(db)
            job_service.fail(job_id, str(e))
        
        raise