"""Core Service Manager implementation."""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any

from .models import (
    ServiceStatus,
    ServiceInfo,
    ServiceConfig,
    HealthCheckResult,
    ServiceType,
)
from .services.port_detector import PortDetector
from .services.process_manager import ProcessManager
from .services.health_checker import HealthChecker
from .default_services import get_default_services

logger = logging.getLogger(__name__)


class ServiceManager:
    """
    Central manager for all local desktop services.

    Handles service lifecycle, health checks, and monitoring.
    """

    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._configs: Dict[str, ServiceConfig] = {}
        self._process_manager = ProcessManager()
        self._health_checker = HealthChecker()
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
        self._initialized = False

    def register_service(self, config: ServiceConfig) -> None:
        """
        Register a service configuration.

        Args:
            config: Service configuration
        """
        self._configs[config.name] = config

        # Initialize service info
        self._services[config.name] = ServiceInfo(
            name=config.name,
            service_type=config.service_type,
            status=ServiceStatus.STOPPED,
            config=config,
        )

        logger.info(f"Registered service: {config.name} (type: {config.service_type.value})")

    def register_default_services(self) -> None:
        """Register all default CFD platform services."""
        default_services = get_default_services()

        for config in default_services:
            self.register_service(config)

        logger.info(f"Registered {len(default_services)} default services")

    async def start_service(self, name: str, force: bool = False) -> ServiceInfo:
        """
        Start a registered service.

        Args:
            name: Service name
            force: Force start even if already running

        Returns:
            Updated ServiceInfo
        """
        if name not in self._configs:
            raise ValueError(f"Service '{name}' is not registered")

        service = self._services[name]
        config = self._configs[name]

        # Check if already running
        if service.status == ServiceStatus.RUNNING and not force:
            logger.info(f"Service '{name}' is already running")
            return service

        # Update status
        service.status = ServiceStatus.STARTING
        service.start_time = datetime.now(timezone.utc)

        try:
            # Determine port
            if config.default_port > 0:
                port, _ = PortDetector.get_port_for_service(
                    name, config.default_port
                )
                service.port = port
            else:
                port = None

            # Start process
            process = self._process_manager.start_process(
                name=name,
                command=config.command,
                args=config.args,
                env=config.env,
                working_dir=config.working_dir,
                port=port,
            )

            if process:
                service.pid = process.pid
                service.status = ServiceStatus.RUNNING
                service.error_message = None

                # Start health check loop
                self._start_health_check(name)

                logger.info(f"Service '{name}' started successfully (PID: {service.pid}, Port: {port})")
            else:
                service.status = ServiceStatus.FAILED
                service.error_message = "Failed to start process"

        except Exception as e:
            service.status = ServiceStatus.FAILED
            service.error_message = str(e)
            logger.exception(f"Failed to start service '{name}': {e}")

        return service

    def stop_service(self, name: str, force: bool = False) -> ServiceInfo:
        """
        Stop a running service.

        Args:
            name: Service name
            force: Force stop even if graceful shutdown fails

        Returns:
            Updated ServiceInfo
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")

        service = self._services[name]
        config = self._configs[name]

        if service.status == ServiceStatus.STOPPED:
            logger.info(f"Service '{name}' is already stopped")
            return service

        # Update status
        service.status = ServiceStatus.STOPPING

        # Stop health check
        self._stop_health_check(name)

        try:
            # Stop process
            success = self._process_manager.stop_process(
                name, timeout=config.stop_timeout if config else 30
            )

            if success:
                service.status = ServiceStatus.STOPPED
                service.pid = None
                service.port = None
                service.start_time = None
                service.error_message = None
                logger.info(f"Service '{name}' stopped successfully")
            else:
                service.status = ServiceStatus.FAILED
                service.error_message = "Failed to stop process"

        except Exception as e:
            service.status = ServiceStatus.FAILED
            service.error_message = str(e)
            logger.exception(f"Failed to stop service '{name}': {e}")

        return service

    async def restart_service(self, name: str) -> ServiceInfo:
        """
        Restart a service.

        Args:
            name: Service name

        Returns:
            Updated ServiceInfo
        """
        await self.stop_service(name)
        await asyncio.sleep(1)  # Brief pause
        return await self.start_service(name)

    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """Get service info."""
        return self._services.get(name)

    def get_all_services(self) -> List[ServiceInfo]:
        """Get all services."""
        return list(self._services.values())

    def get_service_status(self, name: str) -> ServiceStatus:
        """Get service status."""
        service = self._services.get(name)
        return service.status if service else ServiceStatus.STOPPED

    async def check_service_health(self, name: str) -> HealthCheckResult:
        """
        Perform health check on a service.

        Args:
            name: Service name

        Returns:
            HealthCheckResult
        """
        if name not in self._services:
            return HealthCheckResult(
                healthy=False,
                status="unknown",
                message=f"Service '{name}' is not registered",
            )

        service = self._services[name]
        config = self._configs.get(name)

        if not config:
            return HealthCheckResult(
                healthy=False,
                status="unknown",
                message=f"Service '{name}' has no configuration",
            )

        result = await self._health_checker.check_service_health(
            service_name=name,
            port=service.port,
            pid=service.pid,
            health_check_path=config.health_check_path,
        )

        # Update service health status
        service.health_status = result.status
        service.last_health_check = datetime.now(timezone.utc)
        service.health_check_result = result.to_dict()

        if not result.healthy and service.status == ServiceStatus.RUNNING:
            service.status = ServiceStatus.UNHEALTHY

        return result

    def _start_health_check(self, name: str) -> None:
        """Start periodic health check for a service."""
        if name in self._health_check_tasks:
            return  # Already running

        async def health_check_loop():
            config = self._configs.get(name)
            interval = config.health_check_interval if config else 30

            while not self._shutdown_event.is_set():
                service = self._services.get(name)
                if service and service.status == ServiceStatus.RUNNING:
                    await self.check_service_health(name)
                await asyncio.sleep(interval)

        task = asyncio.create_task(health_check_loop())
        self._health_check_tasks[name] = task
        logger.debug(f"Started health check for '{name}'")

    def _stop_health_check(self, name: str) -> None:
        """Stop periodic health check for a service."""
        if name in self._health_check_tasks:
            self._health_check_tasks[name].cancel()
            del self._health_check_tasks[name]
            logger.debug(f"Stopped health check for '{name}'")

    async def start_all_auto_start(self) -> List[ServiceInfo]:
        """Start all services marked for auto-start."""
        started = []
        for name, config in self._configs.items():
            if config.auto_start:
                try:
                    service = await self.start_service(name)
                    started.append(service)
                except Exception as e:
                    logger.exception(f"Failed to auto-start '{name}': {e}")
        return started

    async def stop_all(self) -> List[ServiceInfo]:
        """Stop all running services."""
        stopped = []
        for name in self._services.keys():
            try:
                service = await self.stop_service(name)
                stopped.append(service)
            except Exception as e:
                logger.exception(f"Failed to stop '{name}': {e}")
        return stopped

    def initialize(self) -> None:
        """Initialize the service manager."""
        if self._initialized:
            return

        self.register_default_services()
        self._initialized = True
        logger.info("Service Manager initialized")

    async def shutdown(self) -> None:
        """Shutdown all services gracefully."""
        logger.info("Service Manager shutting down...")
        self._shutdown_event.set()

        # Stop all health check tasks
        for name in self._health_check_tasks.keys():
            self._stop_health_check(name)

        # Stop all services
        await self.stop_all()

        logger.info("Service Manager shutdown complete")

    def get_logs(self, name: str, lines: int = 100) -> str:
        """
        Get recent logs for a service.

        Args:
            name: Service name
            lines: Number of lines to retrieve

        Returns:
            Log content as string
        """
        # This would integrate with the logging system
        # For now, return placeholder
        return f"Logs for {name} (last {lines} lines)\n[Log retrieval not yet implemented]"

    def update_service_metrics(self) -> None:
        """Update CPU and memory metrics for all services."""
        for name, service in self._services.items():
            if service.status == ServiceStatus.RUNNING:
                info = self._process_manager.get_process_info(name)
                if info:
                    service.cpu_percent = info.get("cpu_percent", 0)
                    service.memory_mb = info.get("memory_mb", 0)
                    service.uptime_seconds = info.get("uptime_seconds")


# Global service manager instance
_service_manager: Optional[ServiceManager] = None


def get_service_manager() -> ServiceManager:
    """Get the global Service Manager instance."""
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager