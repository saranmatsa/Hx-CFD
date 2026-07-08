"""Service Manager API routes."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import asyncio
import json

from ..manager import get_service_manager
from ..models import ServiceInfo, ServiceStatus, ServiceConfig, HealthCheckResult, ServiceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/services", tags=["services"])


# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@router.get("", response_model=List[dict])
async def list_services():
    """List all registered services with their current status."""
    sm = get_service_manager()
    services = sm.get_all_services()
    return [s.to_dict() for s in services]


@router.get("/{service_name}", response_model=dict)
async def get_service(service_name: str):
    """Get detailed information about a specific service."""
    sm = get_service_manager()
    service = sm.get_service(service_name)

    if not service:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found",
            headers={"X-Error-Code": "SERVICE_NOT_FOUND"},
        )

    return service.to_dict()


@router.post("/{service_name}/start")
async def start_service(service_name: str, force: bool = False):
    """Start a service."""
    sm = get_service_manager()

    try:
        service = await sm.start_service(service_name, force=force)

        # Broadcast update
        await manager.broadcast({
            "type": "service_updated",
            "service": service.to_dict(),
        })

        return service.to_dict()
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
            headers={"X-Error-Code": "SERVICE_NOT_FOUND"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start service: {str(e)}",
            headers={"X-Error-Code": "START_FAILED"},
        )


@router.post("/{service_name}/stop")
async def stop_service(service_name: str):
    """Stop a service."""
    sm = get_service_manager()

    try:
        service = await sm.stop_service(service_name)

        # Broadcast update
        await manager.broadcast({
            "type": "service_updated",
            "service": service.to_dict(),
        })

        return service.to_dict()
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
            headers={"X-Error-Code": "SERVICE_NOT_FOUND"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop service: {str(e)}",
            headers={"X-Error-Code": "STOP_FAILED"},
        )


@router.post("/{service_name}/restart")
async def restart_service(service_name: str):
    """Restart a service."""
    sm = get_service_manager()

    try:
        service = await sm.restart_service(service_name)

        # Broadcast update
        await manager.broadcast({
            "type": "service_updated",
            "service": service.to_dict(),
        })

        return service.to_dict()
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
            headers={"X-Error-Code": "SERVICE_NOT_FOUND"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart service: {str(e)}",
            headers={"X-Error-Code": "RESTART_FAILED"},
        )


@router.get("/{service_name}/health", response_model=dict)
async def check_health(service_name: str):
    """Perform a health check on a service."""
    sm = get_service_manager()

    result = await sm.check_service_health(service_name)
    return result.to_dict()


@router.get("/{service_name}/logs")
async def get_service_logs(service_name: str, lines: int = 100):
    """Get recent logs for a service."""
    sm = get_service_manager()

    logs = sm.get_logs(service_name, lines)
    return {"service": service_name, "logs": logs}


@router.post("/start-all")
async def start_all_services():
    """Start all services marked for auto-start."""
    sm = get_service_manager()

    try:
        services = await sm.start_all_auto_start()

        # Broadcast update
        await manager.broadcast({
            "type": "all_services_started",
            "services": [s.to_dict() for s in services],
        })

        return {"started": [s.to_dict() for s in services]}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start services: {str(e)}",
            headers={"X-Error-Code": "START_ALL_FAILED"},
        )


@router.post("/stop-all")
async def stop_all_services():
    """Stop all running services."""
    sm = get_service_manager()

    try:
        services = await sm.stop_all()

        # Broadcast update
        await manager.broadcast({
            "type": "all_services_stopped",
            "services": [s.to_dict() for s in services],
        })

        return {"stopped": [s.to_dict() for s in services]}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop services: {str(e)}",
            headers={"X-Error-Code": "STOP_ALL_FAILED"},
        )


@router.get("/status/summary")
async def get_status_summary():
    """Get a summary of all services status."""
    sm = get_service_manager()
    services = sm.get_all_services()

    summary = {
        "total": len(services),
        "running": sum(1 for s in services if s.status == ServiceStatus.RUNNING),
        "stopped": sum(1 for s in services if s.status == ServiceStatus.STOPPED),
        "failed": sum(1 for s in services if s.status == ServiceStatus.FAILED),
        "unhealthy": sum(1 for s in services if s.status == ServiceStatus.UNHEALTHY),
        "starting": sum(1 for s in services if s.status == ServiceStatus.STARTING),
        "services": [s.to_dict() for s in services],
    }

    return summary


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time service updates."""
    await manager.connect(websocket)

    try:
        # Send initial state
        sm = get_service_manager()
        services = sm.get_all_services()
        await websocket.send_json({
            "type": "initial_state",
            "services": [s.to_dict() for s in services],
        })

        # Keep connection alive and handle messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(data)

                # Handle client messages
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "refresh":
                    services = sm.get_all_services()
                    await websocket.send_json({
                        "type": "services_update",
                        "services": [s.to_dict() for s in services],
                    })

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Background task to periodically update metrics
async def update_metrics_periodically():
    """Periodically update service metrics."""
    while True:
        try:
            sm = get_service_manager()
            sm.update_service_metrics()

            # Broadcast metrics update
            services = sm.get_all_services()
            await manager.broadcast({
                "type": "metrics_update",
                "services": [s.to_dict() for s in services],
            })

        except Exception as e:
            logger.exception(f"Error updating metrics: {e}")

        await asyncio.sleep(5)  # Update every 5 seconds