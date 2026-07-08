"""Monitoring and metrics collection for the CFD platform."""
import time
import logging
from functools import wraps
from typing import Callable, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import psutil
import os

logger = logging.getLogger(__name__)

# Metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

active_simulations = Gauge(
    'active_simulations_total',
    'Number of currently running simulations'
)

system_memory_usage = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes'
)

system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)


def track_requests(endpoint: str = None):
    """Decorator to track HTTP requests."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            method = kwargs.get('method', 'GET')
            
            try:
                result = await func(*args, **kwargs)
                status = getattr(result, 'status_code', 200)
                request_count.labels(
                    method=method,
                    endpoint=endpoint or func.__name__,
                    status=status
                ).inc()
                return result
            except Exception as e:
                request_count.labels(
                    method=method,
                    endpoint=endpoint or func.__name__,
                    status=500
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                request_duration.labels(
                    method=method,
                    endpoint=endpoint or func.__name__
                ).observe(duration)
        
        return wrapper
    return decorator


def update_system_metrics():
    """Update system-level metrics."""
    try:
        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.used)
        
        # CPU usage
        cpu = psutil.cpu_percent(interval=1)
        system_cpu_usage.set(cpu)
    except Exception as e:
        logger.error(f"Failed to update system metrics: {e}")


def get_metrics() -> Response:
    """Return Prometheus metrics in the text format."""
    update_system_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


class MetricsMiddleware:
    """Middleware to automatically track all requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            start_time = time.time()
            method = scope['method']
            path = scope['path']
            
            # Intercept status code from response
            status_code = 200
            
            async def send_wrapper(message):
                nonlocal status_code
                if message['type'] == 'http.response.start':
                    status_code = message['status']
                await send(message)
            
            try:
                await self.app(scope, receive, send_wrapper)
                request_count.labels(
                    method=method,
                    endpoint=path,
                    status=status_code
                ).inc()
            except Exception as e:
                request_count.labels(
                    method=method,
                    endpoint=path,
                    status=500
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                request_duration.labels(
                    method=method,
                    endpoint=path
                ).observe(duration)
        else:
            await self.app(scope, receive, send)
