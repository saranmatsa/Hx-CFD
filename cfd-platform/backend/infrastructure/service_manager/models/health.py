"""Health check result models."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthCheckResult(BaseModel):
    """Result of a health check operation."""

    healthy: bool
    status: str
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "healthy": self.healthy,
            "status": self.status,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2) if self.latency_ms else None,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }