"""
Core logging configuration for the CFD Platform.
Provides structured logging using structlog.
"""

import structlog
import logging
import sys
from typing import Any
from datetime import datetime


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO)
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: The name of the logger (typically __name__)
    
    Returns:
        A configured structlog logger
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class that provides logging capabilities to any class."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get a logger for this class."""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)


def log_function_call(
    logger: structlog.stdlib.BoundLogger,
    func_name: str,
    **kwargs: Any
) -> None:
    """
    Log a function call with its arguments.
    
    Args:
        logger: The logger instance
        func_name: Name of the function being called
        **kwargs: Function arguments to log
    """
    logger.info(
        "function_called",
        function=func_name,
        arguments=kwargs
    )


def log_function_result(
    logger: structlog.stdlib.BoundLogger,
    func_name: str,
    success: bool,
    duration: float,
    **kwargs: Any
) -> None:
    """
    Log a function result.
    
    Args:
        logger: The logger instance
        func_name: Name of the function
        success: Whether the function succeeded
        duration: Execution duration in seconds
        **kwargs: Additional result information
    """
    log_level = "info" if success else "error"
    getattr(logger, log_level)(
        "function_completed",
        function=func_name,
        success=success,
        duration_seconds=duration,
        **kwargs
    )


# Initialize logging on module import
setup_logging()