"""
WebSocket API routes for real-time updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from core.database import get_db
from core.security import verify_token
from backend.websocket.manager import get_websocket_manager, EventType
from backend.celery_app import get_task_info

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time updates.
    
    Connect with: ws://host/ws?token=<jwt_token>
    
    Subscribe to events:
    - Send: {"type": "subscribe", "channels": ["job:<job_id>", "simulation:<sim_id>"]}
    
    Receive events:
    - {"type": "job_progress", "data": {"job_id": "...", "progress": 50, "message": "..."}}
    - {"type": "simulation_update", "data": {"simulation_id": "...", "status": "..."}}
    - {"type": "error", "data": {"message": "..."}}
    """
    manager = get_websocket_manager()
    
    # Verify token if provided
    user_id = None
    if token:
        try:
            payload = verify_token(token)
            user_id = payload.get("sub")
        except Exception:
            # Invalid token, but allow anonymous connections for now
            pass
    
    # Connect
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "subscribe":
                    # Subscribe to channels
                    channels = message.get("channels", [])
                    for channel in channels:
                        await manager.subscribe(websocket, channel)
                    
                    await websocket.send_json({
                        "type": "subscribed",
                        "channels": channels,
                    })
                
                elif msg_type == "unsubscribe":
                    # Unsubscribe from channels
                    channels = message.get("channels", [])
                    for channel in channels:
                        await manager.unsubscribe(websocket, channel)
                    
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channels": channels,
                    })
                
                elif msg_type == "ping":
                    # Heartbeat
                    await websocket.send_json({"type": "pong"})
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Unknown message type: {msg_type}"},
                    })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"},
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_endpoint(
    websocket: WebSocket,
    job_id: str,
    token: Optional[str] = Query(None),
):
    """
    Dedicated WebSocket endpoint for a specific job.
    
    Connect with: ws://host/ws/jobs/<job_id>?token=<jwt_token>
    """
    manager = get_websocket_manager()
    channel = f"job:{job_id}"
    
    # Verify token if provided
    user_id = None
    if token:
        try:
            payload = verify_token(token)
            user_id = payload.get("sub")
        except Exception:
            pass
    
    # Connect and subscribe
    await manager.connect(websocket, user_id)
    await manager.subscribe(websocket, channel)
    
    try:
        while True:
            # Receive message (for heartbeat)
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "get_status":
                    # Return current job status
                    task_id = message.get("task_id")
                    if task_id:
                        task_info = get_task_info(task_id)
                        await websocket.send_json({
                            "type": "job_status",
                            "data": task_info,
                        })
            
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/simulations/{simulation_id}")
async def websocket_simulation_endpoint(
    websocket: WebSocket,
    simulation_id: str,
    token: Optional[str] = Query(None),
):
    """
    Dedicated WebSocket endpoint for a specific simulation.
    
    Connect with: ws://host/ws/simulations/<simulation_id>?token=<jwt_token>
    """
    manager = get_websocket_manager()
    channel = f"simulation:{simulation_id}"
    
    # Verify token if provided
    user_id = None
    if token:
        try:
            payload = verify_token(token)
            user_id = payload.get("sub")
        except Exception:
            pass
    
    # Connect and subscribe
    await manager.connect(websocket, user_id)
    await manager.subscribe(websocket, channel)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)