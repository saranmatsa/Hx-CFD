"""
CFD Backend - FastAPI application for CFD orchestration.

This module provides the main entry point for the CFD backend service,
including API routes, service initialization, and lifecycle management.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cfd_backend.core.config import Settings, get_settings
from cfd_backend.core.logging import configure_logging, get_logger
from cfd_backend.services.engine_registry import EngineRegistry
from cfd_backend.services.engineering_orchestrator import EngineeringExecutionError
from cfd_backend.services.workflow_service import LocalWorkflowService

if TYPE_CHECKING:
    from cfd_backend.services.container import ServiceContainer


# Global service container
_service_container: Optional["ServiceContainer"] = None
_LOCAL_CONTRACT_FLAGS = frozenset(
    {
        "--engine-inventory",
        "--workflow-snapshot",
        "--workflow-config",
        "--workflow-job",
        "--workflow-execute",
        "--workflow-transition",
        "--workflow-artifacts",
        "--workflow-artifact-read",
        "--workflow-artifact-export",
        "--project-list",
        "--project-create",
        "--project-open",
        "--project-rename",
        "--project-archive",
        "--project-delete",
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global _service_container
    # Keep the full HTTP API container out of the private desktop-command path.
    # The local workflow bridge uses only its own service graph and must not
    # fail because an unrelated REST route has an unavailable dependency.
    from cfd_backend.services.container import ServiceContainer
    
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
    
    # The desktop shell owns a narrow, token-protected workflow API.  It uses
    # the same long-lived service container as a normal backend process rather
    # than re-launching a one-shot Python CLI for every frontend action.
    if os.environ.get("CFD_PLATFORM_TAURI") == "1":
        from cfd_backend.api.v1.workflow import router as workflow_router

        app.include_router(workflow_router, prefix="/api/v1/workflow")
    else:
        from cfd_backend.api import api_router
        from cfd_backend.core.exceptions import setup_exception_handlers

        setup_exception_handlers(app)
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


app = FastAPI() if any(flag in sys.argv[1:] for flag in _LOCAL_CONTRACT_FLAGS) else create_app()


def main():
    """Main entry point for production."""
    if _run_local_contract_cli():
        return

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


def _run_local_contract_cli() -> bool:
    """Handle private desktop bridge calls without opening a network listener.

    The Tauri shell invokes this mode for local inventory and workflow metadata
    until the long-lived private IPC transport takes ownership of the same
    service contract.  It is never presented as a user command.
    """
    arguments = sys.argv[1:]
    if not any(command in arguments for command in _LOCAL_CONTRACT_FLAGS):
        return False

    try:
        result = asyncio.run(_execute_local_contract(arguments))
    except (ValueError, OSError, json.JSONDecodeError, EngineeringExecutionError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        raise SystemExit(2) from error

    print(json.dumps(result, sort_keys=True))
    return True


async def _execute_local_contract(arguments: list[str]) -> dict:
    """Execute a narrow, typed local desktop contract."""
    settings = get_settings()
    engines = EngineRegistry(settings)
    workflow = LocalWorkflowService(settings, engines)

    if "--engine-inventory" in arguments:
        return {"engines": await engines.inventory(refresh=True)}

    if "--project-list" in arguments:
        include_archived = "--include-archived" in arguments
        return {"projects": await workflow.list_projects(include_archived=include_archived)}

    if "--project-create" in arguments:
        project_id = _argument_value(arguments, "--project-create")
        return {"project": await workflow.create_project(project_id)}

    if "--project-open" in arguments:
        project_id = _argument_value(arguments, "--project-open")
        return {"project": await workflow.open_project(project_id)}

    if "--project-rename" in arguments:
        index = arguments.index("--project-rename")
        if len(arguments) <= index + 2:
            raise ValueError("Project rename requires a project id and new project id.")
        project_id, new_project_id = arguments[index + 1], arguments[index + 2]
        return {"project": await workflow.rename_project(project_id, new_project_id)}

    if "--project-archive" in arguments:
        project_id = _argument_value(arguments, "--project-archive")
        return {"project": await workflow.archive_project(project_id)}

    if "--project-delete" in arguments:
        project_id = _argument_value(arguments, "--project-delete")
        return {"project": await workflow.delete_project(project_id)}

    if "--workflow-snapshot" in arguments:
        project_id = _argument_value(arguments, "--workflow-snapshot")
        return await workflow.snapshot(project_id)

    if "--workflow-artifacts" in arguments:
        index = arguments.index("--workflow-artifacts")
        if len(arguments) <= index + 1:
            raise ValueError("Artifact listing requires a project id.")
        project_id = arguments[index + 1]
        stage_id = arguments[index + 2] if len(arguments) > index + 2 else None
        return {"artifacts": await workflow.list_artifacts(project_id, stage_id)}

    if "--workflow-artifact-read" in arguments:
        index = arguments.index("--workflow-artifact-read")
        if len(arguments) <= index + 2:
            raise ValueError("Artifact reading requires a project id and artifact id.")
        project_id, artifact_id = arguments[index + 1], arguments[index + 2]
        return await workflow.read_artifact(project_id, artifact_id)

    if "--workflow-artifact-export" in arguments:
        index = arguments.index("--workflow-artifact-export")
        if len(arguments) <= index + 2:
            raise ValueError("Artifact export requires a project id and artifact id.")
        project_id, artifact_id = arguments[index + 1], arguments[index + 2]
        payload = _read_contract_payload()
        return await workflow.export_artifact(project_id, artifact_id, str(payload.get("destination") or ""))

    if "--workflow-config" in arguments:
        index = arguments.index("--workflow-config")
        if len(arguments) <= index + 2:
            raise ValueError("Workflow configuration requires a project id and stage id.")
        project_id, stage_id = arguments[index + 1], arguments[index + 2]
        configuration = _read_contract_payload()
        return await workflow.configure_stage(project_id, stage_id, configuration)

    if "--workflow-job" in arguments:
        index = arguments.index("--workflow-job")
        if len(arguments) <= index + 2:
            raise ValueError("Workflow job creation requires a project id and stage id.")
        project_id, stage_id = arguments[index + 1], arguments[index + 2]
        recipe = _read_contract_payload() if not sys.stdin.isatty() else None
        return await workflow.create_job(project_id, stage_id, recipe)

    if "--workflow-execute" in arguments:
        index = arguments.index("--workflow-execute")
        if len(arguments) <= index + 2:
            raise ValueError("Workflow execution requires a project id and stage id.")
        project_id, stage_id = arguments[index + 1], arguments[index + 2]
        recipe = _read_contract_payload() if not sys.stdin.isatty() else None
        return await workflow.execute_stage(project_id, stage_id, recipe)

    index = arguments.index("--workflow-transition")
    if len(arguments) <= index + 3:
        raise ValueError("Workflow transition requires a project id, job id, and state.")
    project_id, job_id, state = arguments[index + 1], arguments[index + 2], arguments[index + 3]
    payload = _read_contract_payload() if not sys.stdin.isatty() else {}
    return await workflow.transition_job(
        project_id,
        job_id,
        state,
        error=payload.get("error"),
        log_artifact_id=payload.get("log_artifact_id"),
    )


def _argument_value(arguments: list[str], flag: str) -> str:
    """Return a required positional value following a desktop bridge flag."""
    index = arguments.index(flag)
    if len(arguments) <= index + 1:
        raise ValueError(f"{flag} requires a project id.")
    return arguments[index + 1]


def _read_contract_payload() -> dict:
    """Read JSON from the private bridge, accepting Windows UTF-8 BOM input."""
    raw = sys.stdin.buffer.read().decode("utf-8-sig")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Workflow payload must be a JSON object.")
    return value


if __name__ == "__main__":
    main()
