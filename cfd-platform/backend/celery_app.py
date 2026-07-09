"""
Celery application configuration.
"""

from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "cfd_platform",
    include=[
        "backend.tasks.mesh_tasks",
        "backend.tasks.simulation_tasks",
        "backend.tasks.optimization_tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    # Broker settings
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task routing
    task_routes={
        "tasks.generate_mesh": {"queue": "mesh"},
        "tasks.refine_mesh": {"queue": "mesh"},
        "tasks.convert_mesh": {"queue": "mesh"},
        "tasks.run_simulation": {"queue": "simulation"},
        "tasks.stop_simulation": {"queue": "simulation"},
        "tasks.extract_results": {"queue": "simulation"},
        "tasks.post_process": {"queue": "simulation"},
        "tasks.run_optimization": {"queue": "optimization"},
        "tasks.stop_optimization": {"queue": "optimization"},
        "tasks.apply_optimized_parameters": {"queue": "optimization"},
        "tasks.multi_objective_optimization": {"queue": "optimization"},
    },
    
    # Queue configuration
    task_default_queue="default",
    task_default_exchange="cfd_platform",
    task_default_routing_key="default",
    
    # Result settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,
    
    # Beat schedule (for periodic tasks)
    beat_schedule={},
)


@worker_ready.connect
def on_worker_ready(**kwargs):
    """Handle worker ready event."""
    from backend.websocket.manager import get_websocket_manager
    from celery.utils.log import get_task_logger
    
    logger = get_task_logger(__name__)
    logger.info("celery_worker_ready")
    
    # Initialize WebSocket manager
    ws_manager = get_websocket_manager()
    logger.info("websocket_manager_initialized")


@worker_shutdown.connect
def on_worker_shutdown(**kwargs):
    """Handle worker shutdown event."""
    from celery.utils.log import get_task_logger
    
    logger = get_task_logger(__name__)
    logger.info("celery_worker_shutdown")


def get_task_info(task_id: str) -> dict:
    """
    Get task information.
    
    Args:
        task_id: Task ID
        
    Returns:
        Task info dict
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback if result.failed() else None,
    }


def revoke_task(task_id: str, terminate: bool = False) -> bool:
    """
    Revoke (cancel) a task.
    
    Args:
        task_id: Task ID to revoke
        terminate: Whether to forcefully terminate
        
    Returns:
        True if revoked successfully
    """
    celery_app.control.revoke(task_id, terminate=terminate)
    return True


# Health check
@celery_app.task(name="health.check", bind=True)
def health_check(self):
    """Health check task."""
    return {
        "status": "healthy",
        "worker": celery_app.conf.worker_hostname,
    }