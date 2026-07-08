"""Service information and configuration models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from .service_status import ServiceStatus, ServiceType


class ServiceConfig(BaseModel):
    """Configuration for a managed service."""

    name: str
    service_type: ServiceType
    default_port: int
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    working_dir: Optional[str] = None
    health_check_path: Optional[str] = None
    health_check_interval: int = 30  # seconds
    start_timeout: int = 60  # seconds
    stop_timeout: int = 30  # seconds
    auto_start: bool = True
    required: bool = False


class ServiceInfo(BaseModel):
    """Information about a running service."""

    name: str
    service_type: ServiceType
    status: ServiceStatus
    port: Optional[int] = None
    pid: Optional[int] = None
    process: Optional[Any] = None  # Will hold the actual process object
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    uptime_seconds: Optional[float] = None
    health_status: str = "unknown"
    last_health_check: Optional[datetime] = None
    health_check_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    config: Optional[ServiceConfig] = None

    class Config:
        arbitrary_types_allowed = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "service_type": self.service_type.value,
            "status": self.status.value,
            "port": self.port,
            "pid": self.pid,
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_mb": round(self.memory_mb, 2),
            "uptime_seconds": round(self.uptime_seconds, 2) if self.uptime_seconds else None,
            "health_status": self.health_status,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "error_message": self.error_message,
            "start_time": self.start_time.isoformat() if self.start_time else None,
        }