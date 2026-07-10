"""
Logging configuration for CFD Backend.

Provides structured logging with structlog, supporting both JSON and console
output formats with proper context binding and log levels.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict, Processor

from cfd_backend.core.config import Settings, get_settings


def add_service_context(logger: structlog.BoundLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service context to log entries."""
    settings = get_settings()
    event_dict["service"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def add_timestamp(logger: structlog.BoundLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO timestamp to log entries."""
    import datetime
    event_dict["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_log_level(logger: structlog.BoundLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to event dict."""
    event_dict["level"] = method_name.upper()
    return event_dict


def filter_sensitive_data(logger: structlog.BoundLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Filter sensitive data from logs."""
    sensitive_keys = {"password", "secret", "token", "api_key", "authorization", "credential"}
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(settings: Optional[Settings] = None) -> None:
    """Configure structured logging for the application."""
    if settings is None:
        settings = get_settings()
    
    # Ensure logs directory exists
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Configure structlog processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_timestamp,
        add_service_context,
        add_log_level,
        filter_sensitive_data,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set up file logging if configured
    if settings.log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            settings.log_file,
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, settings.log_level.upper()))
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggingContext:
    """Context manager for adding structured context to logs."""
    
    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self.token = None
    
    def __enter__(self) -> "LoggingContext":
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.token:
            structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_function_call(logger: structlog.BoundLogger, func_name: str, **kwargs: Any) -> None:
    """Log a function call with parameters."""
    logger.debug("Function called", function=func_name, **kwargs)


def log_function_result(logger: structlog.BoundLogger, func_name: str, result: Any, duration_ms: float) -> None:
    """Log a function result with duration."""
    logger.debug("Function completed", function=func_name, duration_ms=duration_ms, result_type=type(result).__name__)


def log_error(logger: structlog.BoundLogger, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Log an error with context."""
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        **(context or {}),
        exc_info=True,
    )