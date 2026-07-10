"""
CFD Backend - FastAPI application for CFD orchestration.

This module provides the main entry point for the CFD backend service,
including API routes, service initialization, and lifecycle management.
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cfd_backend.api import api_router
from cfd_backend.core.config import Settings, get_settings
from cfd_backend.core.dependencies import get_service_container
from cfd_backend.core.exceptions import CFDException, setup_exception_handlers
from cfd_backend.core.logging import configure_logging, get_logger
from cfd_backend.services.container import ServiceContainer


# Global service container
_service_container: Optional[ServiceContainer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global _service_container
    
    settings = get_settings()
    logger = get_logger(__name__)
    
    # Startup
    logger.info("Starting CFD Backend", version=settings.app_version)
    
    # Initialize service container
    _service_container = ServiceContainer(settings)
    await _service_container.initialize()
    
    # Store in app state
    app.state.service_container = _service_container
    
    logger.info("CFD Backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CFD Backend")
    if _service_container:
        await _service_container.shutdown()
    logger.info("CFD Backend shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    # Configure logging first
    configure_logging(settings)
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="CFD Platform Backend - High-performance CFD orchestration service",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.app_version}
    
    @app.get("/health/ready", tags=["Health"])
    async def readiness_check(request: Request):
        """Readiness check endpoint."""
        container = request.app.state.service_container
        if container and await container.is_ready():
            return {"status": "ready"}
        return JSONResponse(
            status_code=503,
            content={"status": "not ready"}
        )
    
    return app


app = create_app()


def main():
    """Main entry point for production."""
    settings = get_settings()
    
    uvicorn.run(
        "cfd_backend.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_config=None,  # We use structlog
        access_log=False,
    )


def dev_main():
    """Main entry point for development with auto-reload."""
    settings = get_settings()
    
    uvicorn.run(
        "cfd_backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()