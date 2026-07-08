"""
WebSocket connection manager for real-time updates.
"""

import json
from typing import Dict, Set, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import structlog

from core.logging import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    """WebSocket event types."""
    # Job events
    JOB_CREATED = "job:created"
    JOB_PROGRESS = "job:progress"
    JOB_COMPLETED = "job:completed"
    JOB_FAILED = "job:failed"
    
    # Project events
    PROJECT_CREATED = "project:created"
    PROJECT_UPDATED = "project:updated"
    PROJECT_DELETED = "project:deleted"
    
    # Geometry events
    GEOMETRY_CREATED = "geometry:created"
    GEOMETRY_UPDATED = "geometry:updated"
    
    # Mesh events
    MESH_CREATED = "mesh:created"
    MESH_PROGRESS = "mesh:progress"
    MESH_COMPLETED = "mesh:completed"
    
    # Simulation events
    SIMULATION_STARTED = "simulation:started"
    SIMULATION_PROGRESS = "simulation:progress"
    SIMULATION_RESIDUALS = "simulation:residuals"
    SIMULATION_COMPLETED = "simulation:completed"
    
    # Optimization events
    OPTIMIZATION_STARTED = "optimization:started"
    OPTIMIZATION_ITERATION = "optimization:iteration"
    OPTIMIZATION_COMPLETED = "optimization:completed"
    
    # AI events
    AI_MESSAGE = "ai:message"
    AI_STREAM = "ai:stream"
    
    # System events
    CONNECTED = "connected"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    event: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "event": self.event.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
        })

    @classmethod
    def from_json(cls, data: str) -> "WebSocketMessage":
        """Deserialize from JSON."""
        parsed = json.loads(data)
        return cls(
            event=EventType(parsed["event"]),
            data=parsed["data"],
            timestamp=datetime.fromisoformat(parsed["timestamp"]),
            correlation_id=parsed.get("correlation_id"),
        )


@dataclass
class Connection:
    """WebSocket connection info."""
    connection_id: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    subscriptions: Set[EventType] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.
    """

    def __init__(self):
        self._connections: Dict[str, Connection] = {}
        self._project_subscriptions: Dict[str, Set[str]] = {}  # project_id -> connection_ids
        self._user_subscriptions: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self._logger = logger.bind(component="WebSocketManager")

    async def connect(
        self,
        connection_id: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Connection:
        """
        Register a new WebSocket connection.
        
        Args:
            connection_id: Unique connection identifier
            user_id: Optional user ID
            project_id: Optional project ID for project-scoped subscriptions
            metadata: Additional connection metadata
            
        Returns:
            Connection object
        """
        async with self._lock:
            connection = Connection(
                connection_id=connection_id,
                user_id=user_id,
                project_id=project_id,
                metadata=metadata or {},
            )
            
            self._connections[connection_id] = connection
            
            # Track project subscriptions
            if project_id:
                if project_id not in self._project_subscriptions:
                    self._project_subscriptions[project_id] = set()
                self._project_subscriptions[project_id].add(connection_id)
            
            # Track user subscriptions
            if user_id:
                if user_id not in self._user_subscriptions:
                    self._user_subscriptions[user_id] = set()
                self._user_subscriptions[user_id].add(connection_id)
            
            self._logger.info(
                "connection_established",
                connection_id=connection_id,
                user_id=user_id,
                project_id=project_id,
            )
            
            return connection

    async def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if connection_id not in self._connections:
                return
            
            connection = self._connections[connection_id]
            
            # Remove from project subscriptions
            if connection.project_id and connection.project_id in self._project_subscriptions:
                self._project_subscriptions[connection.project_id].discard(connection_id)
            
            # Remove from user subscriptions
            if connection.user_id and connection.user_id in self._user_subscriptions:
                self._user_subscriptions[connection.user_id].discard(connection_id)
            
            del self._connections[connection_id]
            
            self._logger.info("connection_disconnected", connection_id=connection_id)

    async def subscribe(self, connection_id: str, event_types: Set[EventType]) -> None:
        """Subscribe a connection to event types."""
        async with self._lock:
            if connection_id not in self._connections:
                return
            
            connection = self._connections[connection_id]
            connection.subscriptions.update(event_types)
            
            self._logger.debug(
                "subscription_added",
                connection_id=connection_id,
                events=[e.value for e in event_types],
            )

    async def unsubscribe(self, connection_id: str, event_types: Set[EventType]) -> None:
        """Unsubscribe a connection from event types."""
        async with self._lock:
            if connection_id not in self._connections:
                return
            
            connection = self._connections[connection_id]
            connection.subscriptions -= event_types
            
            self._logger.debug(
                "subscription_removed",
                connection_id=connection_id,
                events=[e.value for e in event_types],
            )

    async def broadcast(
        self,
        event: EventType,
        data: Dict[str, Any],
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> int:
        """
        Broadcast a message to matching connections.
        
        Args:
            event: Event type
            data: Event data
            project_id: Optional project filter
            user_id: Optional user filter
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Number of connections that received the message
        """
        message = WebSocketMessage(
            event=event,
            data=data,
            correlation_id=correlation_id,
        )
        
        # Determine target connections
        target_ids: Set[str] = set()
        
        if project_id and project_id in self._project_subscriptions:
            target_ids.update(self._project_subscriptions[project_id])
        
        if user_id and user_id in self._user_subscriptions:
            target_ids.update(self._user_subscriptions[user_id])
        
        # If no specific filters, broadcast to all
        if not target_ids:
            target_ids = set(self._connections.keys())
        
        # Filter by subscription
        recipients = []
        async with self._lock:
            for conn_id in target_ids:
                if conn_id in self._connections:
                    conn = self._connections[conn_id]
                    if event in conn.subscriptions:
                        recipients.append(conn_id)
        
        # Call registered handlers
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    await handler(message)
                except Exception as e:
                    self._logger.error("handler_error", event=event.value, error=str(e))
        
        self._logger.debug(
            "broadcast_sent",
            event=event.value,
            recipients=len(recipients),
            project_id=project_id,
        )
        
        return len(recipients)

    async def send_to_connection(
        self,
        connection_id: str,
        event: EventType,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> bool:
        """
        Send a message to a specific connection.
        
        Args:
            connection_id: Target connection ID
            event: Event type
            data: Event data
            correlation_id: Optional correlation ID
            
        Returns:
            True if sent successfully
        """
        if connection_id not in self._connections:
            return False
        
        message = WebSocketMessage(
            event=event,
            data=data,
            correlation_id=correlation_id,
        )
        
        # Call registered handlers
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    await handler(message)
                except Exception as e:
                    self._logger.error("handler_error", event=event.value, error=str(e))
        
        return True

    def register_handler(self, event: EventType, handler: Callable) -> None:
        """Register a handler for an event type."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def unregister_handler(self, event: EventType, handler: Callable) -> None:
        """Unregister a handler for an event type."""
        if event in self._event_handlers:
            self._event_handlers[event].remove(handler)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Get connection info."""
        return self._connections.get(connection_id)

    def get_project_connections(self, project_id: str) -> List[Connection]:
        """Get all connections for a project."""
        conn_ids = self._project_subscriptions.get(project_id, set())
        return [
            self._connections[cid]
            for cid in conn_ids
            if cid in self._connections
        ]

    async def cleanup_idle_connections(self, max_idle_seconds: int = 3600) -> int:
        """
        Remove connections that haven't been active.
        
        Args:
            max_idle_seconds: Maximum idle time before cleanup
            
        Returns:
            Number of connections removed
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(seconds=max_idle_seconds)
        to_remove = []
        
        async with self._lock:
            for conn_id, conn in self._connections.items():
                if conn.last_activity < cutoff:
                    to_remove.append(conn_id)
        
        for conn_id in to_remove:
            await self.disconnect(conn_id)
        
        if to_remove:
            self._logger.info("idle_connections_cleaned", count=len(to_remove))
        
        return len(to_remove)


# Convenience functions for common events
async def emit_job_progress(
    ws_manager: WebSocketManager,
    job_id: str,
    progress: float,
    message: str,
    project_id: Optional[str] = None,
) -> None:
    """Emit a job progress update."""
    await ws_manager.broadcast(
        EventType.JOB_PROGRESS,
        {
            "job_id": job_id,
            "progress": progress,
            "message": message,
        },
        project_id=project_id,
    )


async def emit_job_completed(
    ws_manager: WebSocketManager,
    job_id: str,
    result: Dict[str, Any],
    project_id: Optional[str] = None,
) -> None:
    """Emit a job completion event."""
    await ws_manager.broadcast(
        EventType.JOB_COMPLETED,
        {
            "job_id": job_id,
            "result": result,
        },
        project_id=project_id,
    )


async def emit_job_failed(
    ws_manager: WebSocketManager,
    job_id: str,
    error: str,
    project_id: Optional[str] = None,
) -> None:
    """Emit a job failure event."""
    await ws_manager.broadcast(
        EventType.JOB_FAILED,
        {
            "job_id": job_id,
            "error": error,
        },
        project_id=project_id,
    )


async def emit_simulation_residuals(
    ws_manager: WebSocketManager,
    simulation_id: str,
    residuals: Dict[str, float],
    iteration: int,
    project_id: Optional[str] = None,
) -> None:
    """Emit simulation residual updates."""
    await ws_manager.broadcast(
        EventType.SIMULATION_RESIDUALS,
        {
            "simulation_id": simulation_id,
            "residuals": residuals,
            "iteration": iteration,
        },
        project_id=project_id,
    )


# Global WebSocket manager instance
_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager