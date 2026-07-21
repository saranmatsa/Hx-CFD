"""Private local workflow endpoints used by the HX CFD desktop shell.

These routes are not a public web product.  Tauri owns their lifecycle and
forwards typed desktop commands to the managed FastAPI sidecar.
"""

from __future__ import annotations

import hmac
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from cfd_backend.services.workflow_service import (
    LocalWorkflowService,
    WorkflowPrerequisiteError,
)
from cfd_backend.services.engineering_orchestrator import EngineeringExecutionError

def _require_desktop_token(request: Request) -> None:
    """Allow only the Tauri process that launched this loopback API.

    The workflow router is mounted only for the managed desktop process.  A
    per-launch bearer token prevents another local process from guessing the
    ephemeral port and mutating an engineer's project.  The guard is a no-op
    for the headless/test application so its documented API remains usable.
    """
    if os.environ.get("CFD_PLATFORM_TAURI") != "1":
        return

    expected = os.environ.get("CFD_PLATFORM_TAURI_TOKEN", "")
    authorization = request.headers.get("authorization", "")
    prefix = "Bearer "
    supplied = authorization[len(prefix) :] if authorization.startswith(prefix) else ""
    if not expected or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The HX CFD desktop session token is required.",
        )


router = APIRouter(dependencies=[Depends(_require_desktop_token)])


class StageConfigurationRequest(BaseModel):
    """A validated semantic recipe for one workflow stage."""

    configuration: dict[str, Any] = Field(default_factory=dict)


class JobCreateRequest(BaseModel):
    """A durable job intent. Worker adapters own subsequent execution."""

    recipe: Optional[dict[str, Any]] = None


class JobTransitionRequest(BaseModel):
    """An internal worker transition persisted before UI publication."""

    state: str = Field(..., min_length=3, max_length=16)
    error: Optional[str] = Field(default=None, max_length=4000)
    log_artifact_id: Optional[str] = Field(default=None, max_length=255)


class StageExecuteRequest(BaseModel):
    """Optional recipe override for a real local stage execution."""

    recipe: Optional[dict[str, Any]] = None


class ArtifactExportRequest(BaseModel):
    """A native-dialog destination for one project-owned artifact."""

    destination: str = Field(..., min_length=1, max_length=4096)


class ProjectCreateRequest(BaseModel):
    """The stable project identifier selected in the desktop shell."""

    project_id: str = Field(..., min_length=1, max_length=120)


class ProjectRenameRequest(BaseModel):
    """A new validated local-first project identifier."""

    new_project_id: str = Field(..., min_length=1, max_length=120)


def _workflow_service(request: Request) -> LocalWorkflowService:
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The local HX CFD service is still starting.",
        )
    return container.workflow


def _workflow_error(error: ValueError) -> HTTPException:
    code = (
        status.HTTP_409_CONFLICT
        if isinstance(error, WorkflowPrerequisiteError)
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(status_code=code, detail=str(error))


@router.get("/engines")
async def get_engine_inventory(
    request: Request,
    refresh: bool = Query(default=False),
) -> dict[str, Any]:
    """List the canonical fourteen engines and their current local capability."""
    workflow = _workflow_service(request)
    return {"engines": await workflow.engines.inventory(refresh=refresh)}


@router.get("/projects")
async def list_local_projects(
    request: Request,
    include_archived: bool = Query(default=False),
) -> dict[str, Any]:
    """List project manifests owned by the local HX CFD workspace."""
    workflow = _workflow_service(request)
    return {"projects": await workflow.list_projects(include_archived=include_archived)}


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_local_project(
    payload: ProjectCreateRequest,
    request: Request,
) -> dict[str, Any]:
    """Initialize a durable project and workflow ledger."""
    workflow = _workflow_service(request)
    try:
        return {"project": await workflow.create_project(payload.project_id)}
    except ValueError as error:
        raise _workflow_error(error) from error


@router.post("/projects/{project_id}/open")
async def open_local_project(project_id: str, request: Request) -> dict[str, Any]:
    """Open an existing project without silently creating it."""
    workflow = _workflow_service(request)
    try:
        return {"project": await workflow.open_project(project_id)}
    except ValueError as error:
        raise _workflow_error(error) from error


@router.patch("/projects/{project_id}")
async def rename_local_project(
    project_id: str,
    payload: ProjectRenameRequest,
    request: Request,
) -> dict[str, Any]:
    """Rename one project and its manifest inside the local store."""
    workflow = _workflow_service(request)
    try:
        return {"project": await workflow.rename_project(project_id, payload.new_project_id)}
    except ValueError as error:
        raise _workflow_error(error) from error


@router.post("/projects/{project_id}/archive")
async def archive_local_project(project_id: str, request: Request) -> dict[str, Any]:
    """Move a project to the local archive without deleting its evidence."""
    workflow = _workflow_service(request)
    try:
        return {"project": await workflow.archive_project(project_id)}
    except ValueError as error:
        raise _workflow_error(error) from error


@router.delete("/projects/{project_id}")
async def delete_local_project(project_id: str, request: Request) -> dict[str, Any]:
    """Delete a project only after service-level path validation."""
    workflow = _workflow_service(request)
    try:
        return {"project": await workflow.delete_project(project_id)}
    except ValueError as error:
        raise _workflow_error(error) from error


@router.get("/projects/{project_id}")
async def get_workflow_snapshot(
    project_id: str,
    request: Request,
    refresh_engines: bool = Query(default=False),
) -> dict[str, Any]:
    """Return local workflow readiness, durable jobs, and engine availability."""
    workflow = _workflow_service(request)
    try:
        return await workflow.snapshot(project_id, refresh_engines=refresh_engines)
    except ValueError as error:
        raise _workflow_error(error) from error


@router.get("/projects/{project_id}/artifacts")
async def list_workflow_artifacts(
    project_id: str,
    request: Request,
    stage_id: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """List opaque artifact descriptors for the active local project.

    Absolute paths stay inside the workflow service.  The desktop receives only
    catalog IDs and display metadata, then uses the read/export routes below.
    """
    workflow = _workflow_service(request)
    try:
        return {"artifacts": await workflow.list_artifacts(project_id, stage_id)}
    except ValueError as error:
        raise _workflow_error(error) from error


@router.get("/projects/{project_id}/artifacts/{artifact_id}")
async def read_workflow_artifact(
    project_id: str,
    artifact_id: str,
    request: Request,
) -> dict[str, Any]:
    """Return bounded local artifact content by opaque catalog ID."""
    workflow = _workflow_service(request)
    try:
        return await workflow.read_artifact(project_id, artifact_id)
    except ValueError as error:
        raise _workflow_error(error) from error


@router.post("/projects/{project_id}/artifacts/{artifact_id}/export")
async def export_workflow_artifact(
    project_id: str,
    artifact_id: str,
    payload: ArtifactExportRequest,
    request: Request,
) -> dict[str, Any]:
    """Export one validated artifact to a native-dialog-selected location."""
    workflow = _workflow_service(request)
    try:
        return await workflow.export_artifact(project_id, artifact_id, payload.destination)
    except ValueError as error:
        raise _workflow_error(error) from error


@router.put("/projects/{project_id}/stages/{stage_id}")
async def configure_workflow_stage(
    project_id: str,
    stage_id: str,
    payload: StageConfigurationRequest,
    request: Request,
) -> dict[str, Any]:
    """Persist a stage recipe once its configuration prerequisites exist."""
    workflow = _workflow_service(request)
    try:
        return await workflow.configure_stage(project_id, stage_id, payload.configuration)
    except ValueError as error:
        raise _workflow_error(error) from error


@router.post("/projects/{project_id}/stages/{stage_id}/jobs", status_code=status.HTTP_201_CREATED)
async def create_workflow_job(
    project_id: str,
    stage_id: str,
    payload: JobCreateRequest,
    request: Request,
) -> dict[str, Any]:
    """Record a job before a local engine worker is dispatched."""
    workflow = _workflow_service(request)
    try:
        return await workflow.create_job(project_id, stage_id, payload.recipe)
    except ValueError as error:
        raise _workflow_error(error) from error


@router.post("/projects/{project_id}/stages/{stage_id}/execute")
async def execute_workflow_stage(
    project_id: str,
    stage_id: str,
    payload: StageExecuteRequest,
    request: Request,
) -> dict[str, Any]:
    """Execute a configured workflow stage through the real local adapter."""
    workflow = _workflow_service(request)
    try:
        return await workflow.execute_stage(project_id, stage_id, payload.recipe)
    except EngineeringExecutionError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except ValueError as error:
        raise _workflow_error(error) from error


@router.patch("/projects/{project_id}/jobs/{job_id}")
async def transition_workflow_job(
    project_id: str,
    job_id: str,
    payload: JobTransitionRequest,
    request: Request,
) -> dict[str, Any]:
    """Persist an internal worker transition and its evidence reference."""
    workflow = _workflow_service(request)
    try:
        return await workflow.transition_job(
            project_id,
            job_id,
            payload.state,
            error=payload.error,
            log_artifact_id=payload.log_artifact_id,
        )
    except ValueError as error:
        raise _workflow_error(error) from error
