"""Durable local workflow state for the HX CFD desktop application.

This service keeps only workflow intent, local jobs, and provenance references.
Large CAD, mesh, and result payloads remain artifact files owned by the engine
workers.  The service deliberately does not infer a successful engineering run
from a child-process exit.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from cfd_backend.core.config import Settings
from cfd_backend.services.engineering_orchestrator import (
    FREECAD_GEOMETRY_SOURCE_EXTENSIONS,
    GMSH_SOLID_CAD_EXTENSIONS,
    EngineeringExecutionError,
    EngineeringOrchestrator,
)
from cfd_backend.services.engine_registry import EngineRegistry


@dataclass(frozen=True)
class WorkflowStage:
    """A user-facing workflow stage and its prerequisite configuration."""

    id: str
    label: str
    prerequisites: tuple[str, ...]


WORKFLOW_STAGES: tuple[WorkflowStage, ...] = (
    WorkflowStage("geometry", "Geometry", ()),
    WorkflowStage("meshing", "Meshing", ("geometry",)),
    WorkflowStage("physics", "Physics", ("meshing",)),
    WorkflowStage("solver", "Solver", ("meshing", "physics")),
    WorkflowStage("results", "Results", ("solver",)),
    WorkflowStage("reports", "Reports", ("results",)),
    WorkflowStage("optimization", "Optimization", ("solver",)),
    WorkflowStage("surrogate", "Surrogate assist", ("results",)),
)


# Artifact payloads are intentionally addressed through opaque IDs at the
# desktop boundary.  The engineering adapters continue to use real paths
# internally, but neither the webview nor a report reader needs to know where
# a local project happens to be stored.
_MAX_ARTIFACT_READ_BYTES = 8 * 1024 * 1024
_MAX_TEXT_ARTIFACT_READ_BYTES = 512 * 1024
_TEXT_ARTIFACT_EXTENSIONS = frozenset(
    {
        ".csv",
        ".html",
        ".htm",
        ".json",
        ".log",
        ".md",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)
_PREVIEW_ARTIFACT_EXTENSIONS = frozenset({".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"})


class WorkflowPrerequisiteError(ValueError):
    """Raised when the requested workflow state cannot safely progress."""


class LocalWorkflowService:
    """Own the durable local metadata for workflow recipes and job state."""

    _valid_project_id = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    _valid_job_states = {
        "QUEUED",
        "STAGING",
        "RUNNING",
        "VALIDATING",
        "PUBLISHING",
        "SUCCEEDED",
        "FAILED",
        "CANCELED",
        "ORPHANED",
    }

    def __init__(self, settings: Settings, engines: EngineRegistry):
        self.settings = settings
        self.engines = engines
        self.orchestrator = EngineeringOrchestrator(settings, engines)

    async def snapshot(self, project_id: str, refresh_engines: bool = False) -> dict[str, Any]:
        """Return workflow state, local jobs, artifact evidence, and engine inventory."""
        project_path = await self._ensure_project(project_id)
        stages, jobs = await asyncio.to_thread(self._read_snapshot, project_path)
        latest_outputs = await asyncio.to_thread(self._read_latest_outputs, project_path)
        artifacts = await asyncio.to_thread(self._artifact_catalog, project_id, project_path, None)
        engine_inventory = await self.engines.inventory(refresh=refresh_engines)
        return {
            "project_id": project_id,
            "stages": self._stage_snapshot(stages),
            "jobs": self._public_jobs(jobs, artifacts),
            # A run response is intentionally not the only source of UI
            # state.  These are the project-owned references that survive
            # route changes, desktop restarts, and reopening a project.
            "latest_outputs": self._public_outputs(latest_outputs, artifacts, project_path),
            "engines": engine_inventory,
        }

    async def list_projects(self, include_archived: bool = False) -> list[dict[str, Any]]:
        """List locally stored projects without creating or modifying any project.

        Project folders are the local-first source of truth.  Hidden storage
        folders (such as ``.archive``) are deliberately excluded from the
        default list so an archived project cannot be opened accidentally.
        """
        return await asyncio.to_thread(self._list_projects, include_archived)

    async def create_project(self, project_id: str) -> dict[str, Any]:
        """Create a new, empty local project with an initialized workflow ledger."""
        return await asyncio.to_thread(self._create_project, project_id)

    async def open_project(self, project_id: str) -> dict[str, Any]:
        """Open an existing local project without silently creating a new one."""
        project_path = await asyncio.to_thread(self._existing_project_path, project_id)
        await asyncio.to_thread(self._initialize_project, project_id, project_path)
        return await self.snapshot(project_id)

    async def rename_project(self, project_id: str, new_project_id: str) -> dict[str, Any]:
        """Rename a local project folder and update its durable manifest."""
        return await asyncio.to_thread(self._rename_project, project_id, new_project_id)

    async def archive_project(self, project_id: str) -> dict[str, Any]:
        """Move an active project into the local archive without deleting data."""
        return await asyncio.to_thread(self._archive_project, project_id)

    async def delete_project(self, project_id: str) -> dict[str, Any]:
        """Permanently delete one validated local project directory.

        The directory is resolved and checked to be a direct child of
        ``projects_dir`` immediately before deletion.  Symlinked projects are
        never accepted, so this operation cannot recurse into an arbitrary
        path outside HX CFD's project store.
        """
        return await asyncio.to_thread(self._delete_project, project_id)

    async def list_artifacts(
        self, project_id: str, stage_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List published files and workflow logs without exposing source paths.

        The catalog is rebuilt from project-owned references on every request.
        A caller therefore cannot retain an arbitrary filesystem path and use it
        after a project is renamed, invalidated, or deleted.
        """
        project_path = await self._ensure_project(project_id)
        return await asyncio.to_thread(
            self._artifact_catalog,
            project_id,
            project_path,
            stage_id,
        )

    async def read_artifact(self, project_id: str, artifact_id: str) -> dict[str, Any]:
        """Read a bounded project artifact identified by an opaque catalog ID."""
        project_path = await self._ensure_project(project_id)
        artifacts = await asyncio.to_thread(self._artifact_catalog, project_id, project_path, None)
        return await asyncio.to_thread(
            self._read_catalog_artifact,
            artifact_id,
            artifacts,
            project_path,
        )

    async def export_artifact(
        self, project_id: str, artifact_id: str, destination: str
    ) -> dict[str, Any]:
        """Copy a catalog artifact to a user-selected location atomically.

        The destination is supplied only after a native save dialog.  The
        workflow service still owns the source lookup and rejects attempts to
        export arbitrary files or overwrite project evidence in place.
        """
        project_path = await self._ensure_project(project_id)
        artifacts = await asyncio.to_thread(self._artifact_catalog, project_id, project_path, None)
        return await asyncio.to_thread(
            self._export_catalog_artifact,
            artifact_id,
            destination,
            artifacts,
            project_path,
        )

    async def configure_stage(
        self, project_id: str, stage_id: str, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        """Persist a canonical configuration after prerequisite validation."""
        stage = self._stage(stage_id)
        project_path = await self._ensure_project(project_id)
        stages, _ = await asyncio.to_thread(self._read_snapshot, project_path)
        blocked_by = self._blocked_by(stage, stages)
        if blocked_by:
            raise WorkflowPrerequisiteError(
                f"{stage.label} is blocked until {', '.join(blocked_by)} is configured."
            )

        normalized = self._normalize_configuration(stage_id, configuration)
        await asyncio.to_thread(
            self._write_stage,
            project_path,
            stage_id,
            normalized,
            "configured",
        )
        # Preserve prior run directories for provenance, but remove their
        # "latest" pointers.  A new recipe must never make an earlier mesh,
        # solve, or report appear to be evidence for the changed inputs.
        await asyncio.to_thread(self._invalidate_references, project_path, stage_id)
        return await self.snapshot(project_id)

    async def create_job(
        self,
        project_id: str,
        stage_id: str,
        recipe: Optional[dict[str, Any]] = None,
        *,
        verify_engines: bool = True,
    ) -> dict[str, Any]:
        """Create a durable job ledger entry for a validated, configured stage.

        A worker adapter must transition the job through the remaining states.
        This function records intent only; it never claims that a mesh or solve
        has run when no local worker was dispatched.
        """
        stage = self._stage(stage_id)
        project_path = await self._ensure_project(project_id)
        stages, _ = await asyncio.to_thread(self._read_snapshot, project_path)
        blocked_by = self._blocked_by(stage, stages)
        if blocked_by:
            raise WorkflowPrerequisiteError(
                f"{stage.label} cannot start until {', '.join(blocked_by)} is configured."
            )
        stage_state = stages.get(stage_id)
        if not stage_state or stage_state["status"] != "configured":
            raise WorkflowPrerequisiteError(
                f"{stage.label} must be configured before a local job can be created."
            )

        configuration = stage_state["configuration"]
        if verify_engines:
            required_engines = await self._required_engines(stage_id, configuration)
            available, unavailable = await self.engines.requirements_available(required_engines)
            if not available:
                names = ", ".join(engine["display_name"] for engine in unavailable)
                raise WorkflowPrerequisiteError(
                    f"{stage.label} cannot start because {names} is unavailable."
                )

        job = {
            "id": str(uuid.uuid4()),
            "stage": stage_id,
            "state": "QUEUED",
            "recipe": self._normalize_configuration(stage_id, recipe or configuration),
            "created_at": self._now(),
            "updated_at": self._now(),
            "error": None,
            "log_artifact_id": None,
        }
        await asyncio.to_thread(self._write_job, project_path, job)
        return job

    async def transition_job(
        self,
        project_id: str,
        job_id: str,
        state: str,
        *,
        error: Optional[str] = None,
        log_artifact_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Persist a job transition before the worker emits it to the UI."""
        state = state.upper()
        if state not in self._valid_job_states:
            raise ValueError(f"Unsupported job state: {state}")
        project_path = await self._ensure_project(project_id)
        return await asyncio.to_thread(
            self._transition_job,
            project_path,
            job_id,
            state,
            error,
            log_artifact_id,
        )

    async def execute_stage(
        self,
        project_id: str,
        stage_id: str,
        recipe: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run a configured stage through its real local-engine adapter.

        A successful response is only returned after the adapter created and
        published artifacts. Engine failures are stored against the durable job
        and propagated to Tauri; no synthetic progress or result is emitted.
        """
        project_path = await self._ensure_project(project_id)
        job = await self.create_job(project_id, stage_id, recipe, verify_engines=False)
        await self.transition_job(project_id, job["id"], "STAGING")
        try:
            await self.transition_job(project_id, job["id"], "RUNNING")
            output = await self.orchestrator.execute(
                project_path,
                stage_id,
                job["recipe"],
                job["id"],
            )
            await self.transition_job(project_id, job["id"], "VALIDATING")
            await self.transition_job(project_id, job["id"], "PUBLISHING")
            completed = await self.transition_job(
                project_id,
                job["id"],
                "SUCCEEDED",
                log_artifact_id=output["log_artifact_id"],
            )
            artifacts = await asyncio.to_thread(
                self._artifact_catalog, project_id, project_path, None
            )
            return {
                "job": self._public_jobs([completed], artifacts)[0],
                "output": self._public_output(output, artifacts, project_path),
            }
        except Exception as error:
            log_path = project_path / "logs" / f"{job['id']}.log"
            await self.transition_job(
                project_id,
                job["id"],
                "FAILED",
                error=str(error),
                log_artifact_id=str(log_path) if log_path.is_file() else None,
            )
            raise

    def _artifact_catalog(
        self,
        project_id: str,
        project_path: Path,
        stage_id: Optional[str],
    ) -> list[dict[str, Any]]:
        """Build a safe, current catalog from published references and job logs.

        Engine adapters persist absolute paths in their internal provenance
        files.  This method is the one-way boundary that converts those paths
        into opaque, project-scoped descriptors.  It deliberately accepts only
        real files resolved beneath the current project directory; directories,
        symlinks, stale paths, and externally supplied paths are never exposed.
        """
        if stage_id is not None:
            self._stage(stage_id)

        references = self._read_latest_references(project_path)
        _, jobs = self._read_snapshot(project_path)
        records: dict[str, tuple[dict[str, Any], Path]] = {}

        def add(
            raw_path: Any,
            artifact_stage: str,
            job_id: Optional[str],
            *,
            role: str,
        ) -> None:
            if stage_id is not None and artifact_stage != stage_id:
                return
            path = self._safe_artifact_file(project_path, raw_path)
            if path is None:
                return
            descriptor = self._artifact_descriptor(
                project_id,
                project_path,
                path,
                artifact_stage,
                job_id,
                role=role,
            )
            records.setdefault(descriptor["artifact_id"], (descriptor, path))

        for current_stage, reference in references.items():
            output = reference["output"]
            job_id = reference.get("job_id")
            artifact_paths = output.get("artifacts", [])
            if isinstance(artifact_paths, list):
                for raw_path in artifact_paths:
                    add(raw_path, current_stage, job_id, role="artifact")
            add(output.get("log_artifact_id"), current_stage, job_id, role="log")

        jobs_by_id = {str(job["id"]): job for job in jobs}
        for job in jobs:
            add(
                job.get("log_artifact_id"),
                str(job["stage"]),
                str(job["id"]),
                role="log",
            )

        # An interrupted adapter can have written its deterministic log before
        # the job state was persisted.  Include it only if its filename maps to
        # a known job ID and it remains under the project-owned logs directory.
        logs_root = project_path / "logs"
        if logs_root.is_dir() and (stage_id is None or any(job["stage"] == stage_id for job in jobs)):
            for log_path in logs_root.glob("*.log"):
                job = jobs_by_id.get(log_path.stem)
                if job is not None:
                    add(log_path, str(job["stage"]), str(job["id"]), role="log")

        stage_order = {stage.id: index for index, stage in enumerate(WORKFLOW_STAGES)}
        return [
            descriptor
            for descriptor, _ in sorted(
                records.values(),
                key=lambda record: (
                    stage_order.get(str(record[0]["stage_id"]), len(stage_order)),
                    str(record[0].get("created_at") or ""),
                    str(record[0]["name"]),
                ),
            )
        ]

    @staticmethod
    def _safe_artifact_file(project_path: Path, raw_path: Any) -> Optional[Path]:
        """Resolve one artifact only when it is a real file inside the project."""
        if not isinstance(raw_path, (str, os.PathLike)):
            return None
        try:
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                return None
            resolved = candidate.resolve(strict=True)
            root = project_path.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, RuntimeError, ValueError):
            return None
        if not resolved.is_file():
            return None
        return resolved

    @classmethod
    def _artifact_descriptor(
        cls,
        project_id: str,
        project_path: Path,
        artifact_path: Path,
        stage_id: str,
        job_id: Optional[str],
        *,
        role: str,
    ) -> dict[str, Any]:
        relative_path = artifact_path.relative_to(project_path.resolve(strict=True)).as_posix()
        token = "\x1f".join((project_id, stage_id, job_id or "", relative_path))
        artifact_id = "artifact_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
        suffix = artifact_path.suffix.lower()
        mime_type = mimetypes.guess_type(artifact_path.name)[0] or "application/octet-stream"
        created_at = datetime.fromtimestamp(artifact_path.stat().st_mtime, timezone.utc).isoformat()
        kind = "log" if role == "log" or suffix == ".log" else "report" if stage_id == "reports" else "artifact"
        return {
            "artifact_id": artifact_id,
            "name": artifact_path.name,
            "label": f"{cls._stage(stage_id).label} · {artifact_path.name}",
            "stage_id": stage_id,
            "job_id": job_id,
            "kind": kind,
            "mime_type": mime_type,
            "size_bytes": artifact_path.stat().st_size,
            "created_at": created_at,
            "readable": suffix in _TEXT_ARTIFACT_EXTENSIONS,
            "previewable": suffix in _PREVIEW_ARTIFACT_EXTENSIONS,
        }

    def _artifact_record(
        self,
        artifact_id: str,
        artifacts: list[dict[str, Any]],
        project_path: Path,
    ) -> tuple[dict[str, Any], Path]:
        if not isinstance(artifact_id, str) or not artifact_id.startswith("artifact_"):
            raise ValueError("Artifact reference is invalid.")
        for descriptor in artifacts:
            if descriptor["artifact_id"] != artifact_id:
                continue
            source = self._artifact_source_from_descriptor(project_path, descriptor)
            if source is not None:
                return descriptor, source
        raise ValueError("The requested project artifact is no longer available.")

    def _artifact_source_from_descriptor(
        self, project_path: Path, descriptor: dict[str, Any]
    ) -> Optional[Path]:
        """Resolve a descriptor through the current catalog instead of decoding its ID."""
        # Descriptors intentionally carry no path.  Match the deterministic ID
        # against current project evidence so an ID cannot be used as a path or
        # as a capability to escape the active project.
        references = self._read_latest_references(project_path)
        _, jobs = self._read_snapshot(project_path)
        candidates: list[tuple[Any, str, Optional[str], str]] = []
        for current_stage, reference in references.items():
            output = reference["output"]
            job_id = reference.get("job_id")
            for raw_path in output.get("artifacts", []) if isinstance(output.get("artifacts"), list) else []:
                candidates.append((raw_path, current_stage, job_id, "artifact"))
            candidates.append((output.get("log_artifact_id"), current_stage, job_id, "log"))
        for job in jobs:
            candidates.append((job.get("log_artifact_id"), str(job["stage"]), str(job["id"]), "log"))
            candidates.append(
                (project_path / "logs" / f"{job['id']}.log", str(job["stage"]), str(job["id"]), "log")
            )

        for raw_path, stage_id, job_id, role in candidates:
            path = self._safe_artifact_file(project_path, raw_path)
            if path is None:
                continue
            current = self._artifact_descriptor(
                project_path.name,
                project_path,
                path,
                stage_id,
                job_id,
                role=role,
            )
            if current["artifact_id"] == descriptor["artifact_id"]:
                return path
        return None

    def _read_catalog_artifact(
        self,
        artifact_id: str,
        artifacts: list[dict[str, Any]],
        project_path: Path,
    ) -> dict[str, Any]:
        descriptor, source = self._artifact_record(artifact_id, artifacts, project_path)
        byte_limit = _MAX_ARTIFACT_READ_BYTES if descriptor["previewable"] else _MAX_TEXT_ARTIFACT_READ_BYTES
        size = source.stat().st_size
        if size > byte_limit:
            raise ValueError("This artifact is too large for the in-app reader. Export it instead.")
        content = source.read_bytes()
        if descriptor["readable"]:
            return {
                "artifact": descriptor,
                "encoding": "utf-8",
                "content": content.decode("utf-8", errors="replace"),
            }
        return {
            "artifact": descriptor,
            "encoding": "base64",
            "content": base64.b64encode(content).decode("ascii"),
        }

    def _export_catalog_artifact(
        self,
        artifact_id: str,
        destination: str,
        artifacts: list[dict[str, Any]],
        project_path: Path,
    ) -> dict[str, Any]:
        descriptor, source = self._artifact_record(artifact_id, artifacts, project_path)
        if not isinstance(destination, str) or not destination.strip():
            raise ValueError("Choose a destination in the native save dialog.")
        try:
            destination_path = Path(destination).expanduser()
            if not destination_path.is_absolute() or (
                destination_path.exists() and destination_path.is_dir()
            ):
                raise ValueError("invalid destination")
            if destination_path.exists() and destination_path.is_symlink():
                raise ValueError("invalid destination")
            parent = destination_path.parent.resolve(strict=True)
            if not parent.is_dir():
                raise ValueError("invalid destination")
            resolved_destination = (parent / destination_path.name).resolve(strict=False)
        except ValueError:
            raise ValueError("Choose a valid writable destination in the native save dialog.") from None
        except (OSError, RuntimeError):
            raise ValueError("Choose a valid writable destination in the native save dialog.") from None
        try:
            resolved_destination.relative_to(project_path.resolve(strict=True))
        except ValueError:
            pass
        else:
            raise ValueError("Choose an export location outside the active HX CFD project.")

        temporary = parent / f".{destination_path.name}.{uuid.uuid4().hex}.part"
        try:
            with source.open("rb") as source_file, temporary.open("xb") as destination_file:
                shutil.copyfileobj(source_file, destination_file)
                destination_file.flush()
                os.fsync(destination_file.fileno())
            os.replace(temporary, destination_path)
        except OSError as error:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise ValueError("HX CFD could not export that project artifact.") from error
        return {
            "artifact_id": descriptor["artifact_id"],
            "name": destination_path.name,
            "size_bytes": source.stat().st_size,
            "exported": True,
        }

    def _public_jobs(
        self, jobs: list[dict[str, Any]], artifacts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        log_ids = {
            (artifact.get("stage_id"), artifact.get("job_id"), artifact.get("kind")): artifact["artifact_id"]
            for artifact in artifacts
            if artifact.get("kind") == "log"
        }
        return [
            {
                "id": job["id"],
                "stage": job["stage"],
                "state": job["state"],
                "created_at": job["created_at"],
                "updated_at": job["updated_at"],
                "error": job["error"],
                "log_artifact_id": log_ids.get((job["stage"], job["id"], "log")),
            }
            for job in jobs
        ]

    def _public_outputs(
        self,
        outputs: dict[str, dict[str, Any]],
        artifacts: list[dict[str, Any]],
        project_path: Path,
    ) -> dict[str, dict[str, Any]]:
        return {
            stage_id: self._public_output(output, artifacts, project_path)
            for stage_id, output in outputs.items()
        }

    def _public_output(
        self,
        output: dict[str, Any],
        artifacts: list[dict[str, Any]],
        project_path: Path,
    ) -> dict[str, Any]:
        """Project an engine result into a path-free desktop response."""
        raw_to_descriptor = self._raw_artifact_descriptors(project_path, artifacts)

        def convert(value: Any, key: Optional[str] = None) -> Any:
            if isinstance(value, dict):
                projected: dict[str, Any] = {}
                for child_key, child_value in value.items():
                    if child_key in {"run_path", "stdout"}:
                        continue
                    if child_key == "artifacts":
                        if isinstance(child_value, list):
                            projected["artifacts"] = [
                                raw_to_descriptor[path]
                                for raw in child_value
                                if (path := self._safe_artifact_file(project_path, raw)) in raw_to_descriptor
                            ]
                        continue
                    if child_key == "log_artifact_id":
                        path = self._safe_artifact_file(project_path, child_value)
                        descriptor = raw_to_descriptor.get(path) if path else None
                        projected["log_artifact_id"] = descriptor["artifact_id"] if descriptor else None
                        continue
                    if isinstance(child_value, str):
                        path = self._safe_artifact_file(project_path, child_value)
                        descriptor = raw_to_descriptor.get(path) if path else None
                        if descriptor is not None:
                            projected[f"{child_key}_artifact"] = descriptor
                        elif self._looks_like_absolute_path(child_value):
                            # A source CAD path or a case directory is a valid
                            # internal relationship, but never desktop data.
                            projected[f"{child_key}_available"] = True
                        else:
                            projected[child_key] = child_value
                        continue
                    projected[child_key] = convert(child_value, child_key)
                return projected
            if isinstance(value, list):
                return [convert(item, key) for item in value]
            return value

        return convert(output)

    def _raw_artifact_descriptors(
        self, project_path: Path, artifacts: list[dict[str, Any]]
    ) -> dict[Path, dict[str, Any]]:
        """Reconstruct source paths only inside the service implementation."""
        references = self._read_latest_references(project_path)
        _, jobs = self._read_snapshot(project_path)
        descriptors_by_id = {descriptor["artifact_id"]: descriptor for descriptor in artifacts}
        raw: dict[Path, dict[str, Any]] = {}

        candidates: list[tuple[Any, str, Optional[str], str]] = []
        for stage_id, reference in references.items():
            output = reference["output"]
            job_id = reference.get("job_id")
            for value in output.get("artifacts", []) if isinstance(output.get("artifacts"), list) else []:
                candidates.append((value, stage_id, job_id, "artifact"))
            candidates.append((output.get("log_artifact_id"), stage_id, job_id, "log"))
        for job in jobs:
            candidates.append((job.get("log_artifact_id"), str(job["stage"]), str(job["id"]), "log"))

        for value, stage_id, job_id, role in candidates:
            path = self._safe_artifact_file(project_path, value)
            if path is None:
                continue
            descriptor = self._artifact_descriptor(
                project_path.name, project_path, path, stage_id, job_id, role=role
            )
            public_descriptor = descriptors_by_id.get(descriptor["artifact_id"])
            if public_descriptor is not None:
                raw[path] = public_descriptor
        return raw

    @staticmethod
    def _looks_like_absolute_path(value: str) -> bool:
        """Recognize local path-like values without echoing them back to UI."""
        return Path(value).is_absolute() or bool(re.match(r"^[A-Za-z]:[\\/]", value))

    def _projects_root(self) -> Path:
        """Return the resolved local project root, creating it if necessary."""
        root = self.settings.projects_dir.resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _project_entry(self, project_id: str) -> Path:
        if not self._valid_project_id.fullmatch(project_id):
            raise ValueError("Project id must contain only letters, numbers, dots, dashes, or underscores.")
        return self._projects_root() / project_id

    def _project_path(self, project_id: str) -> Path:
        """Resolve a project directory and prove it remains inside projects_dir."""
        root = self._projects_root()
        project_path = self._project_entry(project_id).resolve(strict=False)
        self._assert_project_child(project_path, root)
        return project_path

    def _existing_project_path(self, project_id: str) -> Path:
        """Return a real active project directory while rejecting symlink traversal."""
        entry = self._project_entry(project_id)
        if entry.is_symlink():
            raise ValueError("Symlinked project directories are not supported.")
        project_path = self._project_path(project_id)
        if not entry.exists() or not project_path.is_dir():
            raise ValueError(f"Project '{project_id}' was not found in the local project store.")
        return project_path

    def _existing_archived_project_path(self, project_id: str) -> Path:
        """Return a real archived project directory while rejecting symlink traversal."""
        # Reuse active-path validation for the project id before constructing a
        # private archive path from it.
        self._project_entry(project_id)
        archive_root = self._archive_root()
        entry = archive_root / project_id
        if entry.is_symlink():
            raise ValueError("Symlinked project directories are not supported.")
        project_path = entry.resolve(strict=False)
        self._assert_project_child(project_path, self._projects_root(), archived=True)
        if not entry.exists() or not project_path.is_dir():
            raise ValueError(f"Archived project '{project_id}' was not found in the local project store.")
        return project_path

    async def _ensure_project(self, project_id: str) -> Path:
        entry = self._project_entry(project_id)
        if entry.is_symlink():
            raise ValueError("Symlinked project directories are not supported.")
        project_path = self._project_path(project_id)
        await asyncio.to_thread(self._initialize_project, project_id, project_path)
        return project_path

    def _list_projects(self, include_archived: bool) -> list[dict[str, Any]]:
        root = self._projects_root()
        projects = self._project_summaries(root, archived=False)
        if include_archived:
            projects.extend(self._project_summaries(self._archive_root(), archived=True))
        return sorted(projects, key=lambda project: project["updated_at"], reverse=True)

    def _project_summaries(self, directory: Path, *, archived: bool) -> list[dict[str, Any]]:
        if not directory.exists():
            return []

        summaries: list[dict[str, Any]] = []
        for entry in directory.iterdir():
            if entry.name.startswith(".") or not entry.is_dir() or entry.is_symlink():
                continue
            if not self._valid_project_id.fullmatch(entry.name):
                continue
            project_path = entry.resolve(strict=False)
            try:
                self._assert_project_child(project_path, self._projects_root(), archived=archived)
            except ValueError:
                continue
            summaries.append(self._project_summary(project_path, archived=archived))
        return summaries

    def _project_summary(self, project_path: Path, *, archived: bool) -> dict[str, Any]:
        manifest: dict[str, Any]
        manifest_error: Optional[str] = None
        try:
            manifest = self._read_manifest(project_path)
        except ValueError as error:
            # A corrupt manifest must not hide other local projects.  Its
            # presence is reported honestly to the desktop UI for recovery.
            manifest = {}
            manifest_error = str(error)

        timestamps = [project_path.stat().st_mtime]
        for metadata_path in (project_path / "manifest.json", project_path / "project.sqlite"):
            if metadata_path.exists():
                timestamps.append(metadata_path.stat().st_mtime)
        updated_at = datetime.fromtimestamp(max(timestamps), timezone.utc).isoformat()
        summary: dict[str, Any] = {
            "id": project_path.name,
            "project_id": project_path.name,
            "created_at": manifest.get("created_at"),
            "updated_at": updated_at,
            "archived": archived,
        }
        if manifest_error:
            summary["warning"] = manifest_error
        return summary

    def _create_project(self, project_id: str) -> dict[str, Any]:
        entry = self._project_entry(project_id)
        project_path = self._project_path(project_id)
        if entry.exists() or entry.is_symlink():
            raise ValueError(f"Project '{project_id}' already exists in the local project store.")
        entry.mkdir()
        self._initialize_project(project_id, project_path)
        return self._project_summary(project_path, archived=False)

    def _rename_project(self, project_id: str, new_project_id: str) -> dict[str, Any]:
        source_path = self._existing_project_path(project_id)
        destination_entry = self._project_entry(new_project_id)
        destination_path = self._project_path(new_project_id)
        if destination_entry.exists() or destination_entry.is_symlink():
            raise ValueError(f"Project '{new_project_id}' already exists in the local project store.")

        manifest = self._read_manifest(source_path)
        source_path.rename(destination_path)
        manifest.update(
            {
                "project_id": new_project_id,
                "updated_at": self._now(),
            }
        )
        self._atomic_json_write(destination_path / "manifest.json", manifest)
        return self._project_summary(destination_path, archived=False)

    def _archive_project(self, project_id: str) -> dict[str, Any]:
        source_path = self._existing_project_path(project_id)
        archive_root = self._archive_root()
        destination_entry = archive_root / project_id
        destination_path = destination_entry.resolve(strict=False)
        self._assert_project_child(destination_path, self._projects_root(), archived=True)
        if destination_entry.exists() or destination_entry.is_symlink():
            raise ValueError(f"An archived project named '{project_id}' already exists.")

        manifest = self._read_manifest(source_path)
        source_path.rename(destination_path)
        manifest.update(
            {
                "project_id": project_id,
                "archived_at": self._now(),
                "updated_at": self._now(),
                "state": "archived",
            }
        )
        self._atomic_json_write(destination_path / "manifest.json", manifest)
        return self._project_summary(destination_path, archived=True)

    def _delete_project(self, project_id: str) -> dict[str, Any]:
        active_entry = self._project_entry(project_id)
        if active_entry.exists() or active_entry.is_symlink():
            project_path = self._existing_project_path(project_id)
            archived = False
        else:
            project_path = self._existing_archived_project_path(project_id)
            archived = True
        # Revalidate immediately before the only recursive filesystem action.
        self._assert_project_child(project_path, self._projects_root(), archived=archived)
        if project_path.is_symlink() or not project_path.is_dir():
            raise ValueError("Only a real local project directory can be deleted.")
        shutil.rmtree(project_path)
        return {
            "id": project_id,
            "project_id": project_id,
            "archived": archived,
            "deleted": True,
        }

    def _archive_root(self) -> Path:
        root = self._projects_root()
        archive_entry = root / ".archive"
        if archive_entry.is_symlink():
            raise ValueError("The local project archive may not be a symlink.")
        archive_path = archive_entry.resolve(strict=False)
        try:
            archive_path.relative_to(root)
        except ValueError as error:
            raise ValueError("The local project archive must remain inside projects_dir.") from error
        archive_path.mkdir(parents=True, exist_ok=True)
        if not archive_path.is_dir():
            raise ValueError("The local project archive path is not a directory.")
        return archive_path

    @staticmethod
    def _assert_project_child(project_path: Path, root: Path, *, archived: bool = False) -> None:
        """Require an exact project child, never the root or an arbitrary subtree."""
        try:
            relative = project_path.relative_to(root)
        except ValueError as error:
            raise ValueError("Project path must remain inside the local project store.") from error

        expected_parts = 2 if archived else 1
        if len(relative.parts) != expected_parts:
            raise ValueError("Project path must be a direct local project directory.")
        if archived and relative.parts[0] != ".archive":
            raise ValueError("Archived project path must remain inside the local archive.")

    @staticmethod
    def _read_manifest(project_path: Path) -> dict[str, Any]:
        manifest_path = project_path / "manifest.json"
        if not manifest_path.exists():
            return {}
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Project '{project_path.name}' has an unreadable manifest.") from error
        if not isinstance(manifest, dict):
            raise ValueError(f"Project '{project_path.name}' has an invalid manifest.")
        return manifest

    def _initialize_project(self, project_id: str, project_path: Path) -> None:
        project_path.mkdir(parents=True, exist_ok=True)
        for child in ("objects", "runs", "refs", "logs"):
            (project_path / child).mkdir(exist_ok=True)
        manifest_path = project_path / "manifest.json"
        if not manifest_path.exists():
            created_at = self._now()
            manifest = {
                "schema_version": 1,
                "project_id": project_id,
                "created_at": created_at,
                "updated_at": created_at,
                "storage": "local-first",
            }
            self._atomic_json_write(manifest_path, manifest)
        with self._connection(project_path) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS workflow_stages (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    configuration_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_jobs (
                    id TEXT PRIMARY KEY,
                    stage TEXT NOT NULL,
                    state TEXT NOT NULL,
                    recipe_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error TEXT,
                    log_artifact_id TEXT
                );
                """
            )

    def _read_snapshot(self, project_path: Path) -> tuple[dict[str, dict], list[dict]]:
        with self._connection(project_path) as connection:
            stage_rows = connection.execute(
                "SELECT id, status, configuration_json, updated_at FROM workflow_stages"
            ).fetchall()
            job_rows = connection.execute(
                """
                SELECT id, stage, state, recipe_json, created_at, updated_at, error, log_artifact_id
                FROM workflow_jobs
                ORDER BY created_at DESC
                LIMIT 50
                """
            ).fetchall()
        stages = {
            row["id"]: {
                "status": row["status"],
                "configuration": json.loads(row["configuration_json"]),
                "updated_at": row["updated_at"],
            }
            for row in stage_rows
        }
        jobs = [
            {
                "id": row["id"],
                "stage": row["stage"],
                "state": row["state"],
                "recipe": json.loads(row["recipe_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "error": row["error"],
                "log_artifact_id": row["log_artifact_id"],
            }
            for row in job_rows
        ]
        return stages, jobs

    @staticmethod
    def _read_latest_references(project_path: Path) -> dict[str, dict[str, Any]]:
        """Read valid internal stage references without publishing their paths.

        A job can be successful while its evidence is intentionally invalidated
        by a later configuration change.  The latest reference is therefore
        the authoritative source for a previewable output and the artifact
        catalog.  This helper is internal-only; callers project its values into
        opaque descriptors before returning them to Tauri or FastAPI.
        """
        references: dict[str, dict[str, Any]] = {}
        for stage in WORKFLOW_STAGES:
            reference = project_path / "refs" / stage.id / "latest.json"
            if not reference.is_file():
                continue
            try:
                payload = json.loads(reference.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            output = payload.get("output") if isinstance(payload, dict) else None
            if isinstance(output, dict):
                job_id = payload.get("job_id") if isinstance(payload, dict) else None
                references[stage.id] = {
                    "job_id": str(job_id) if isinstance(job_id, str) else None,
                    "output": output,
                }
        return references

    @classmethod
    def _read_latest_outputs(cls, project_path: Path) -> dict[str, dict[str, Any]]:
        """Return raw internal outputs only to the workflow service itself."""
        return {
            stage_id: reference["output"]
            for stage_id, reference in cls._read_latest_references(project_path).items()
        }

    @staticmethod
    def _invalidate_references(project_path: Path, stage_id: str) -> None:
        """Remove stale latest pointers for a stage and all dependent stages.

        Historical engine artifacts remain under ``runs/``; only the mutable
        pointers used by the desktop are cleared.  Workflow stages are listed
        in prerequisite order, but the fixed-point walk also handles future
        branching additions safely.
        """
        invalidated = {stage_id}
        changed = True
        while changed:
            changed = False
            for stage in WORKFLOW_STAGES:
                if stage.id in invalidated:
                    continue
                if any(prerequisite in invalidated for prerequisite in stage.prerequisites):
                    invalidated.add(stage.id)
                    changed = True
        for invalidated_stage in invalidated:
            reference = project_path / "refs" / invalidated_stage / "latest.json"
            if reference.exists():
                reference.unlink()

    def _write_stage(
        self, project_path: Path, stage_id: str, configuration: dict[str, Any], status: str
    ) -> None:
        with self._connection(project_path) as connection:
            connection.execute(
                """
                INSERT INTO workflow_stages(id, status, configuration_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    configuration_json = excluded.configuration_json,
                    updated_at = excluded.updated_at
                """,
                (stage_id, status, json.dumps(configuration, sort_keys=True), self._now()),
            )

    def _write_job(self, project_path: Path, job: dict[str, Any]) -> None:
        with self._connection(project_path) as connection:
            connection.execute(
                """
                INSERT INTO workflow_jobs(
                    id, stage, state, recipe_json, created_at, updated_at, error, log_artifact_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["id"],
                    job["stage"],
                    job["state"],
                    json.dumps(job["recipe"], sort_keys=True),
                    job["created_at"],
                    job["updated_at"],
                    job["error"],
                    job["log_artifact_id"],
                ),
            )

    def _transition_job(
        self,
        project_path: Path,
        job_id: str,
        state: str,
        error: Optional[str],
        log_artifact_id: Optional[str],
    ) -> dict[str, Any]:
        with self._connection(project_path) as connection:
            row = connection.execute(
                """
                SELECT id, stage, state, recipe_json, created_at, updated_at, error, log_artifact_id
                FROM workflow_jobs WHERE id = ?
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Workflow job {job_id} was not found.")
            connection.execute(
                """
                UPDATE workflow_jobs
                SET state = ?, updated_at = ?, error = ?, log_artifact_id = ?
                WHERE id = ?
                """,
                (
                    state,
                    self._now(),
                    error if error is not None else row["error"],
                    log_artifact_id if log_artifact_id is not None else row["log_artifact_id"],
                    job_id,
                ),
            )
            updated = connection.execute(
                """
                SELECT id, stage, state, recipe_json, created_at, updated_at, error, log_artifact_id
                FROM workflow_jobs WHERE id = ?
                """,
                (job_id,),
            ).fetchone()
        assert updated is not None
        return {
            "id": updated["id"],
            "stage": updated["stage"],
            "state": updated["state"],
            "recipe": json.loads(updated["recipe_json"]),
            "created_at": updated["created_at"],
            "updated_at": updated["updated_at"],
            "error": updated["error"],
            "log_artifact_id": updated["log_artifact_id"],
        }

    def _stage_snapshot(self, configured: dict[str, dict]) -> list[dict[str, Any]]:
        return [
            {
                "id": stage.id,
                "label": stage.label,
                "status": self._stage_status(stage, configured),
                "blocked_by": self._blocked_by(stage, configured),
                "configuration": configured.get(stage.id, {}).get("configuration", {}),
                "updated_at": configured.get(stage.id, {}).get("updated_at"),
            }
            for stage in WORKFLOW_STAGES
        ]

    def _stage_status(self, stage: WorkflowStage, configured: dict[str, dict]) -> str:
        if self._blocked_by(stage, configured):
            return "blocked"
        if configured.get(stage.id, {}).get("status") == "configured":
            return "configured"
        return "required"

    @staticmethod
    def _blocked_by(stage: WorkflowStage, configured: dict[str, dict]) -> list[str]:
        return [
            prerequisite
            for prerequisite in stage.prerequisites
            if configured.get(prerequisite, {}).get("status") != "configured"
        ]

    @staticmethod
    def _normalize_configuration(stage_id: str, configuration: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(configuration, dict):
            raise ValueError("Workflow configuration must be a JSON object.")
        normalized = json.loads(json.dumps(configuration, sort_keys=True))
        if stage_id == "meshing":
            # The default Gmsh adapter publishes an unstructured tetrahedral
            # volume mesh.  cfMesh is exposed as a separate OpenFOAM-native
            # Cartesian route only when explicitly selected.
            route = normalized.get("route", "tetrahedral")
            # Migrate the historical default rather than making existing
            # projects impossible to run. It was only a label; prior runs
            # have always used the same tetrahedral adapter.
            if route == "hex_dominant":
                route = "tetrahedral"
            if route not in {"tetrahedral", "cfmesh_cartesian"}:
                raise ValueError(
                    "The installed meshing adapters support only 'tetrahedral' and 'cfmesh_cartesian'."
                )
            normalized["route"] = route
            normalized.setdefault("boundary_layers", {})
            normalized.setdefault("quality_policy", {})
            try:
                # Persist the user-approved Gmsh surface selections as a
                # canonical recipe.  The engine validates those IDs against
                # the prepared CAD at execution time, when the real entity
                # set is available.
                normalized["boundary_groups"] = EngineeringOrchestrator.normalize_mesh_boundary_groups(
                    normalized
                )
            except EngineeringExecutionError as error:
                raise ValueError(str(error)) from error
        if stage_id == "physics":
            try:
                # Validate the user-supplied recipe while it is still a
                # configuration error. The solver additionally validates its
                # patch names against the converted OpenFOAM mesh at run time.
                normalized["boundary_recipe"] = EngineeringOrchestrator.normalize_boundary_recipe(normalized)
            except EngineeringExecutionError as error:
                raise ValueError(str(error)) from error
        return normalized

    @staticmethod
    def _fields(configuration: dict[str, Any]) -> dict[str, Any]:
        fields = configuration.get("fields", configuration)
        return fields if isinstance(fields, dict) else {}

    async def _required_engines(
        self, stage_id: str, configuration: dict[str, Any]
    ) -> tuple[str, ...]:
        if stage_id == "geometry":
            fields = self._fields(configuration)
            source = configuration.get("source_path") or fields.get("Source")
            suffix = Path(str(source or "")).suffix.lower()
            freecad = await self.engines.capability("freecad")
            if freecad.status in {"ready", "bundled"}:
                # FreeCAD is the primary geometry adapter for every supported
                # import format, including STL and OBJ surface meshes.
                if suffix in FREECAD_GEOMETRY_SOURCE_EXTENSIONS:
                    return ("freecad",)
            if suffix in GMSH_SOLID_CAD_EXTENSIONS:
                # Gmsh remains a truthful local fallback only for solid CAD
                # exchange files when FreeCAD is not installed.
                return ("gmsh",)
            if suffix in FREECAD_GEOMETRY_SOURCE_EXTENSIONS:
                # Make the unavailable prerequisite explicit for STL/OBJ;
                # otherwise a missing FreeCAD install would look like an
                # unsupported source format.
                return ("freecad",)
            # Let the execution adapter return the precise unsupported-format
            # error instead of masking it as an unrelated missing engine.
            return ()
        if stage_id == "meshing":
            route = self._normalize_configuration(stage_id, configuration).get("route", "tetrahedral")
            if route == "cfmesh_cartesian":
                return ("cfmesh", "gmsh")
            return ("gmsh", "meshio", "vtk", "pyvista")
        if stage_id == "solver":
            return ("openfoam",)
        if stage_id == "results":
            return ("openfoam", "vtk", "pyvista")
        if stage_id == "reports":
            return ("vtk", "pyvista")
        if stage_id == "optimization":
            return ("openmdao", "nevergrad")
        if stage_id == "surrogate":
            return ("physicsnemo", "physicsnemo_cfd")
        return ()

    @staticmethod
    def _connect(project_path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(project_path / "project.sqlite")
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    @contextmanager
    def _connection(project_path: Path) -> Iterator[sqlite3.Connection]:
        """Commit or roll back a short-lived project transaction, then close it.

        ``sqlite3.Connection`` used as a context manager only manages its
        transaction; it does not close the file handle.  Explicit close is
        essential on Windows so completed workflow projects can immediately
        be renamed, archived, or deleted.
        """
        connection = LocalWorkflowService._connect(project_path)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
        temporary_path.replace(path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _stage(stage_id: str) -> WorkflowStage:
        for stage in WORKFLOW_STAGES:
            if stage.id == stage_id:
                return stage
        raise ValueError(f"Unknown workflow stage: {stage_id}")
