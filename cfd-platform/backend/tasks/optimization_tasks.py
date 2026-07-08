"""
Celery tasks for optimization operations.
"""

from typing import Dict, Any, Optional, List, Callable
from celery import Task
from celery.utils.log import get_task_logger
import numpy as np

from backend.celery_app import celery_app
from backend.services.base import OptimizationService, SimulationService, JobService
from backend.websocket.manager import get_websocket_manager, EventType
from core.config import get_settings
from core.database import get_db_context

logger = get_task_logger(__name__)
settings = get_settings()


class OptimizationTask(Task):
    """Base task for optimization operations."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error("optimization_task_failed", task_id=task_id, error=str(exc))
        
        optimization_id = kwargs.get("optimization_id")
        job_id = kwargs.get("job_id")
        
        if optimization_id:
            with get_db_context() as db:
                opt_service = OptimizationService(db)
                opt_service.update(optimization_id, {"status": "failed", "error": str(exc)})
        
        if job_id:
            ws_manager = get_websocket_manager()
            logger.info("optimization_failed_emit", job_id=job_id)


def _create_objective_function(
    optimization_id: str,
    objective_config: Dict[str, Any],
    project_id: Optional[str],
) -> Callable:
    """
    Create objective function for optimization.
    
    Args:
        optimization_id: Optimization record ID
        objective_config: Objective configuration
        project_id: Project for WebSocket updates
        
    Returns:
        Objective function
    """
    ws_manager = get_websocket_manager()
    
    def objective(x: np.ndarray) -> float:
        """Evaluate objective function."""
        try:
            # Update progress
            ws_manager.broadcast(
                EventType.OPTIMIZATION_ITERATION,
                {
                    "optimization_id": optimization_id,
                    "parameters": x.tolist(),
                    "status": "evaluating",
                },
                project_id=project_id,
            )
            
            # Run simulation with current parameters
            with get_db_context() as db:
                sim_service = SimulationService(db)
                job_service = JobService(db)
                
                # Create simulation
                sim_data = {
                    "name": f"opt_{optimization_id}_eval",
                    "project_id": objective_config.get("project_id"),
                    "mesh_id": objective_config.get("mesh_id"),
                    "config": {
                        "parameters": dict(zip(
                            objective_config.get("parameter_names", []),
                            x.tolist(),
                        )),
                    },
                }
                
                simulation = sim_service.create(sim_data)
                
                # Run simulation task synchronously (or dispatch)
                from backend.tasks.simulation_tasks import run_simulation
                result = run_simulation.apply(
                    args=[
                        simulation.id,
                        simulation.mesh_id,
                        None,  # job_id
                        simulation.config,
                    ],
                    kwargs={"project_id": project_id},
                )
                
                # Get results
                results = result.get()
                
                # Calculate objective value
                objective_type = objective_config.get("type", "drag")
                
                if objective_type == "drag":
                    value = results.get("results", {}).get("drag_coefficient", 0)
                elif objective_type == "lift":
                    value = -results.get("results", {}).get("lift_coefficient", 0)  # Maximize lift
                elif objective_type == "pressure_drop":
                    value = results.get("results", {}).get("pressure_drop", 0)
                elif objective_type == "custom":
                    # Custom objective calculation
                    value = objective_config.get("custom_function", lambda r: 0)(results)
                else:
                    value = 0
                
                return value
                
        except Exception as e:
            logger.error("objective_evaluation_failed", error=str(e))
            return float("inf")
    
    return objective


@celery_app.task(bind=True, base=OptimizationTask, name="tasks.run_optimization")
def run_optimization(
    self,
    optimization_id: str,
    job_id: str,
    optimization_config: Dict[str, Any],
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run shape/parameter optimization.
    
    Args:
        optimization_id: Optimization record ID
        job_id: Job tracking ID
        optimization_config: Optimization parameters
        project_id: Project for WebSocket updates
        
    Returns:
        Optimization result
    """
    logger.info("run_optimization_started", optimization_id=optimization_id)
    
    ws_manager = get_websocket_manager()
    
    try:
        with get_db_context() as db:
            opt_service = OptimizationService(db)
            job_service = JobService(db)
            
            # Update status
            job_service.update_progress(job_id, 0.05, "Initializing optimization")
            opt_service.update(optimization_id, {"status": "running"})
            
            # Get optimization
            optimization = opt_service.get(optimization_id)
            if not optimization:
                raise ValueError(f"Optimization not found: {optimization_id}")
            
            job_service.update_progress(job_id, 0.1, "Setting up optimizer")
            
            # Import nevergrad
            import nevergrad as ng
            
            # Setup optimization parameters
            param_names = optimization_config.get("parameter_names", [])
            param_bounds = optimization_config.get("parameter_bounds", [])
            
            instrumentation = ng.p.Instrumentation(
                *[ng.p.Scalar(lower=b[0], upper=b[1]) for b in param_bounds]
            )
            
            # Select optimizer
            optimizer_name = optimization_config.get("optimizer", "NGOpt")
            budget = optimization_config.get("budget", 100)
            
            optimizer = ng.optimizers.registry[optimizer_name](
                parametrization=instrumentation,
                budget=budget,
            )
            
            # Create objective function
            objective_config = {
                **optimization_config.get("objective", {}),
                "project_id": optimization.project_id,
            }
            objective = _create_objective_function(optimization_id, objective_config, project_id)
            
            job_service.update_progress(job_id, 0.15, "Running optimization")
            
            # Run optimization with progress monitoring
            best_value = float("inf")
            best_params = None
            iteration = 0
            
            def progress_callback(x: np.ndarray, value: float):
                """Callback for optimization progress."""
                nonlocal best_value, best_params, iteration
                iteration += 1
                
                # Update best if improved
                if value < best_value:
                    best_value = value
                    best_params = x.tolist()
                
                # Update job progress (0.15 to 0.9 range)
                progress = 0.15 + (iteration / budget) * 0.75
                job_service.update_progress(
                    job_id,
                    progress,
                    f"Optimization iteration {iteration}/{budget} - best: {best_value:.4f}",
                )
                
                # Emit iteration event
                ws_manager.broadcast(
                    EventType.OPTIMIZATION_ITERATION,
                    {
                        "optimization_id": optimization_id,
                        "iteration": iteration,
                        "budget": budget,
                        "current_value": value,
                        "best_value": best_value,
                        "best_parameters": best_params,
                        "progress": progress,
                    },
                    project_id=project_id,
                )
            
            # Run optimization
            recommendation = optimizer.minimize(objective)
            
            job_service.update_progress(job_id, 0.95, "Finalizing")
            
            # Get results
            best_parameters = recommendation.value[0] if isinstance(recommendation.value, tuple) else recommendation.value
            if hasattr(best_parameters, "asarray"):
                best_parameters = best_parameters.asarray().tolist()
            
            optimization_result = {
                "best_parameters": dict(zip(param_names, best_parameters)),
                "best_value": float(recommendation.loss),
                "iterations": budget,
                "optimizer": optimizer_name,
            }
            
            # Update optimization record
            opt_service.update(optimization_id, {
                "status": "completed",
                "result": optimization_result,
            })
            
            job_service.complete(job_id, optimization_result)
            
            # Emit completion event
            ws_manager.broadcast(
                EventType.OPTIMIZATION_COMPLETED,
                {
                    "optimization_id": optimization_id,
                    "result": optimization_result,
                },
                project_id=project_id,
            )
            
            logger.info("run_optimization_completed", optimization_id=optimization_id)
            
            return {
                "optimization_id": optimization_id,
                "result": optimization_result,
            }
            
    except Exception as e:
        logger.error("run_optimization_failed", optimization_id=optimization_id, error=str(e))
        
        with get_db_context() as db:
            opt_service = OptimizationService(db)
            job_service = JobService(db)
            
            opt_service.update(optimization_id, {"status": "failed", "error": str(e)})
            job_service.fail(job_id, str(e))
        
        ws_manager.broadcast(
            EventType.JOB_FAILED,
            {"job_id": job_id, "error": str(e)},
            project_id=project_id,
        )
        
        raise


@celery_app.task(bind=True, base=OptimizationTask, name="tasks.stop_optimization")
def stop_optimization(
    self,
    optimization_id: str,
    job_id: str,
) -> Dict[str, Any]:
    """
    Stop a running optimization.
    
    Args:
        optimization_id: Optimization to stop
        job_id: Job tracking ID
        
    Returns:
        Stop result
    """
    logger.info("stop_optimization_requested", optimization_id=optimization_id)
    
    try:
        with get_db_context() as db:
            opt_service = OptimizationService(db)
            job_service = JobService(db)
            
            # Update status
            opt_service.update(optimization_id, {"status": "stopped"})
            job_service.complete(job_id, {"stopped": True})
            
            return {"optimization_id": optimization_id, "stopped": True}
            
    except Exception as e:
        logger.error("stop_optimization_failed", optimization_id=optimization_id, error=str(e))
        
        with get_db_context() as db:
            job_service = JobService(db)
            job_service.fail(job_id, str(e))
        
        raise


@celery_app.task(bind=True, base=OptimizationTask, name="tasks.apply_optimized_parameters")
def apply_optimized_parameters(
    self,
    optimization_id: str,
    target_type: str,
    target_id: str,
    job_id: str,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Apply optimized parameters to geometry or simulation.
    
    Args:
        optimization_id: Optimization with results
        target_type: Type of target (geometry, simulation)
        target_id: Target record ID
        job_id: Job tracking ID
        project_id: Project for WebSocket updates
        
    Returns:
        Application result
    """
    logger.info(
        "apply_optimized_parameters_started",
        optimization_id=optimization_id,
        target_type=target_type,
        target_id=target_id,
    )
    
    try:
        with get_db_context() as db:
            opt_service = OptimizationService(db)
            job_service = JobService(db)
            
            job_service.update_progress(job_id, 0.1, "Applying parameters")
            
            # Get optimization
            optimization = opt_service.get(optimization_id)
            if not optimization:
                raise ValueError(f"Optimization not found: {optimization_id}")
            
            if not optimization.result:
                raise ValueError("Optimization has no results")
            
            best_params = optimization.result.get("best_parameters", {})
            
            if target_type == "geometry":
                from backend.services.base import GeometryService
                geom_service = GeometryService(db)
                
                # Update geometry parameters
                geom_service.update(target_id, {
                    "parameters": best_params,
                })
                
            elif target_type == "simulation":
                from backend.services.base import SimulationService
                sim_service = SimulationService(db)
                
                # Update simulation config
                simulation = sim_service.get(target_id)
                if simulation:
                    config = dict(simulation.config) if simulation.config else {}
                    config["parameters"] = best_params
                    sim_service.update(target_id, {"config": config})
            
            else:
                raise ValueError(f"Unknown target type: {target_type}")
            
            job_service.update_progress(job_id, 0.9, "Finalizing")
            job_service.complete(job_id, {
                "applied_parameters": best_params,
                "target_type": target_type,
                "target_id": target_id,
            })
            
            return {
                "optimization_id": optimization_id,
                "applied_parameters": best_params,
                "target_type": target_type,
                "target_id": target_id,
            }
            
    except Exception as e:
        logger.error(
            "apply_optimized_parameters_failed",
            optimization_id=optimization_id,
            error=str(e),
        )
        
        with get_db_context() as db:
            job_service = JobService(db)
            job_service.fail(job_id, str(e))
        
        raise


@celery_app.task(bind=True, base=OptimizationTask, name="tasks.multi_objective_optimization")
def multi_objective_optimization(
    self,
    optimization_id: str,
    job_id: str,
    optimization_config: Dict[str, Any],
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run multi-objective optimization.
    
    Args:
        optimization_id: Optimization record ID
        job_id: Job tracking ID
        optimization_config: Optimization parameters
        project_id: Project for WebSocket updates
        
    Returns:
        Pareto front results
    """
    logger.info("multi_objective_optimization_started", optimization_id=optimization_id)
    
    ws_manager = get_websocket_manager()
    
    try:
        with get_db_context() as db:
            opt_service = OptimizationService(db)
            job_service = JobService(db)
            
            job_service.update_progress(job_id, 0.05, "Initializing multi-objective optimization")
            opt_service.update(optimization_id, {"status": "running"})
            
            # Import nevergrad
            import nevergrad as ng
            
            # Setup optimization parameters
            param_names = optimization_config.get("parameter_names", [])
            param_bounds = optimization_config.get("parameter_bounds", [])
            
            instrumentation = ng.p.Instrumentation(
                *[ng.p.Scalar(lower=b[0], upper=b[1]) for b in param_bounds]
            )
            
            # Multi-objective optimizer
            optimizer = ng.optimizers.NGOpt(
                parametrization=instrumentation,
                budget=optimization_config.get("budget", 200),
            )
            
            # Create multi-objective function
            objectives = optimization_config.get("objectives", [])
            
            def multi_objective(x: np.ndarray) -> np.ndarray:
                """Evaluate multiple objectives."""
                values = []
                for obj_config in objectives:
                    # Run evaluation (simplified - would need proper simulation)
                    value = 0  # Placeholder
                    values.append(value)
                return np.array(values)
            
            job_service.update_progress(job_id, 0.15, "Running optimization")
            
            # Run optimization
            recommendation = optimizer.minimize(multi_objective)
            
            job_service.update_progress(job_id, 0.95, "Finalizing")
            
            # Get Pareto front
            pareto_front = optimizer.pareto_frontier_
            
            optimization_result = {
                "pareto_front": [
                    {
                        "parameters": dict(zip(param_names, p.value[0].asarray().tolist())),
                        "objectives": p.losses.tolist() if hasattr(p, "losses") else [],
                    }
                    for p in pareto_front
                ],
                "best_compromise": {
                    "parameters": dict(zip(param_names, recommendation.value[0].asarray().tolist())),
                },
                "optimizer": "NGOpt",
            }
            
            opt_service.update(optimization_id, {
                "status": "completed",
                "result": optimization_result,
            })
            
            job_service.complete(job_id, optimization_result)
            
            ws_manager.broadcast(
                EventType.OPTIMIZATION_COMPLETED,
                {
                    "optimization_id": optimization_id,
                    "result": optimization_result,
                },
                project_id=project_id,
            )
            
            return {
                "optimization_id": optimization_id,
                "result": optimization_result,
            }
            
    except Exception as e:
        logger.error(
            "multi_objective_optimization_failed",
            optimization_id=optimization_id,
            error=str(e),
        )
        
        with get_db_context() as db:
            opt_service = OptimizationService(db)
            job_service = JobService(db)
            
            opt_service.update(optimization_id, {"status": "failed", "error": str(e)})
            job_service.fail(job_id, str(e))
        
        raise