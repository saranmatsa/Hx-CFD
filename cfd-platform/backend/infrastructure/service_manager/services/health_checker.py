"""Health checking for local services."""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any

import httpx

from ..models import HealthCheckResult, ServiceStatus

logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs health checks on local services."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._health_cache: Dict[str, HealthCheckResult] = {}
        self._cache_ttl: Dict[str, float] = {}

    async def check_http_health(
        self,
        url: str,
        expected_status: int = 200,
        service_name: str = "unknown",
    ) -> HealthCheckResult:
        """
        Perform HTTP health check.

        Args:
            url: Health check URL
            expected_status: Expected HTTP status code
            service_name: Name of the service

        Returns:
            HealthCheckResult
        """
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == expected_status:
                    return HealthCheckResult(
                        healthy=True,
                        status="healthy",
                        message=f"Service '{service_name}' is healthy",
                        latency_ms=latency_ms,
                        details={"status_code": response.status_code},
                    )
                else:
                    return HealthCheckResult(
                        healthy=False,
                        status="unhealthy",
                        message=f"Service '{service_name}' returned status {response.status_code}",
                        latency_ms=latency_ms,
                        details={"status_code": response.status_code, "expected": expected_status},
                    )

        except httpx.TimeoutException:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                healthy=False,
                status="unhealthy",
                message=f"Service '{service_name}' health check timed out",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                healthy=False,
                status="unhealthy",
                message=f"Service '{service_name}' health check failed: {str(e)}",
                latency_ms=latency_ms,
            )

    def check_process_health(self, pid: Optional[int], service_name: str = "unknown") -> HealthCheckResult:
        """
        Check if a process is healthy.

        Args:
            pid: Process ID
            service_name: Name of the service

        Returns:
            HealthCheckResult
        """
        if pid is None:
            return HealthCheckResult(
                healthy=False,
                status="unhealthy",
                message=f"Service '{service_name}' has no PID",
            )

        try:
            import psutil
            proc = psutil.Process(pid)

            if not proc.is_running():
                return HealthCheckResult(
                    healthy=False,
                    status="unhealthy",
                    message=f"Service '{service_name}' process is not running",
                )

            # Check if process is responding
            try:
                proc.status()
            except psutil.NoSuchProcess:
                return HealthCheckResult(
                    healthy=False,
                    status="unhealthy",
                    message=f"Service '{service_name}' process no longer exists",
                )

            return HealthCheckResult(
                healthy=True,
                status="healthy",
                message=f"Service '{service_name}' process is running",
                details={"pid": pid, "status": proc.status()},
            )

        except ImportError:
            # psutil not available, assume healthy if we have a PID
            return HealthCheckResult(
                healthy=True,
                status="healthy",
                message=f"Service '{service_name}' process is running (psutil not available)",
                details={"pid": pid},
            )
        except psutil.NoSuchProcess:
            return HealthCheckResult(
                healthy=False,
                status="unhealthy",
                message=f"Service '{service_name}' process no longer exists",
            )
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                status="unhealthy",
                message=f"Service '{service_name}' health check failed: {str(e)}",
            )

    async def check_service_health(
        self,
        service_name: str,
        port: Optional[int],
        pid: Optional[int],
        health_check_path: Optional[str] = "/health",
        host: str = "127.0.0.1",
    ) -> HealthCheckResult:
        """
        Perform comprehensive health check on a service.

        Args:
            service_name: Name of the service
            port: Service port
            pid: Process ID
            health_check_path: Path for HTTP health check
            host: Host address

        Returns:
            HealthCheckResult
        """
        # First check if process is running
        process_result = self.check_process_health(pid, service_name)
        if not process_result.healthy:
            return process_result

        # If port is available, try HTTP health check
        if port and health_check_path:
            url = f"http://{host}:{port}{health_check_path}"
            http_result = await self.check_http_health(url, service_name=service_name)
            return http_result

        # Fall back to process check only
        return process_result

    def get_cached_health(self, service_name: str, max_age: float = 30.0) -> Optional[HealthCheckResult]:
        """
        Get cached health result if still valid.

        Args:
            service_name: Name of the service
            max_age: Maximum age in seconds

        Returns:
            Cached HealthCheckResult or None
        """
        if service_name not in self._health_cache:
            return None

        if service_name not in self._cache_ttl:
            return None

        age = time.time() - self._cache_ttl[service_name]
        if age > max_age:
            return None

        return self._health_cache[service_name]

    def cache_health(self, service_name: str, result: HealthCheckResult) -> None:
        """Cache a health check result."""
        self._health_cache[service_name] = result
        self._cache_ttl[service_name] = time.time()

    def clear_cache(self, service_name: Optional[str] = None) -> None:
        """Clear health check cache."""
        if service_name:
            self._health_cache.pop(service_name, None)
            self._cache_ttl.pop(service_name, None)
        else:
            self._health_cache.clear()
            self._cache_ttl.clear()