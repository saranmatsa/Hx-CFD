"""Post-processing service for simulation results and visualization."""

import base64
import io
import os
import uuid
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.models.simulation import Simulation
from cfd_backend.models.simulation_result import SimulationResult, ResultType, ResultStatus
from cfd_backend.models.project import Project

logger = logging.getLogger(__name__)


def _import_pyvista():
    """Import pyvista lazily so the service can start even when pyvista is absent."""
    try:
        import pyvista as pv
        return pv
    except ImportError:
        logger.warning("pyvista is not available; visualization features will be limited")
        return None


def _import_h5py():
    """Import h5py lazily."""
    try:
        import h5py
        return h5py
    except ImportError:
        logger.warning("h5py is not available; HDF5 export will fall back to JSON")
        return None


def _import_jinja2():
    """Import jinja2 lazily."""
    try:
        from jinja2 import Template
        return Template
    except ImportError:
        logger.warning("jinja2 is not available; report generation will fall back to plain text")
        return None


class PostProcessingService:
    """Service for post-processing simulation results and generating visualizations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.results_dir = Path("/tmp/cfd_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def get_results(
        self,
        page: int = 1,
        page_size: int = 20,
        simulation_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        result_type: Optional[ResultType] = None,
        status: Optional[ResultStatus] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        current_user_id: Optional[UUID] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List simulation results with pagination and filters."""
        query = select(SimulationResult).options(
            selectinload(SimulationResult.simulation).selectinload(Simulation.project)
        )

        if simulation_id:
            query = query.where(SimulationResult.simulation_id == simulation_id)
        elif project_id:
            query = query.join(Simulation).where(Simulation.project_id == project_id)
        elif current_user_id and user_role not in ["admin", "manager"]:
            # Filter by accessible projects
            accessible_project_ids = select(Project.id).where(
                (Project.owner_id == current_user_id) |
                ((Project.visibility == "public") & (Project.status != "archived"))
            )
            query = query.join(Simulation).where(Simulation.project_id.in_(accessible_project_ids))

        if result_type:
            query = query.where(SimulationResult.result_type == result_type)
        if status:
            query = query.where(SimulationResult.status == status)
        if search:
            query = query.where(
                SimulationResult.name.ilike(f"%{search}%") |
                SimulationResult.description.ilike(f"%{search}%")
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Apply sorting
        sort_column = getattr(SimulationResult, sort_by, SimulationResult.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        results = result.scalars().all()

        return {
            "results": [
                {
                    "id": str(r.id),
                    "simulation_id": str(r.simulation_id),
                    "name": r.name,
                    "description": r.description,
                    "result_type": r.result_type,
                    "status": r.status,
                    "time_step": r.time_step,
                    "time_value": r.time_value,
                    "file_path": r.file_path,
                    "file_size": r.file_size,
                    "metadata": r.result_metadata,
                    "variables": r.variables,
                    "region": r.region,
                    "min_values": r.min_values,
                    "max_values": r.max_values,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in results
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def create_result(
        self,
        simulation_id: UUID,
        name: str,
        description: Optional[str],
        result_type: ResultType,
        time_step: Optional[float] = None,
        time_value: Optional[float] = None,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        variables: Optional[List[str]] = None,
        region: Optional[str] = None,
        min_values: Optional[Dict[str, float]] = None,
        max_values: Optional[Dict[str, float]] = None,
    ) -> SimulationResult:
        """Create a new simulation result entry."""
        result = SimulationResult(
            id=uuid.uuid4(),
            simulation_id=simulation_id,
            name=name,
            description=description,
            result_type=result_type,
            status=ResultStatus.PENDING,
            time_step=time_step,
            time_value=time_value,
            file_path=file_path,
            file_size=file_size,
            result_metadata=metadata or {},
            variables=variables or [],
            region=region,
            min_values=min_values or {},
            max_values=max_values or {},
        )
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def get_result(self, result_id: UUID) -> Optional[SimulationResult]:
        """Get a simulation result by ID."""
        result = await self.db.execute(
            select(SimulationResult)
            .options(selectinload(SimulationResult.simulation).selectinload(Simulation.project))
            .where(SimulationResult.id == result_id)
        )
        return result.scalar_one_or_none()

    async def update_result(
        self,
        result_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        variables: Optional[List[str]] = None,
        region: Optional[str] = None,
    ) -> Optional[SimulationResult]:
        """Update a simulation result."""
        result = await self.get_result(result_id)
        if not result:
            return None

        if name is not None:
            result.name = name
        if description is not None:
            result.description = description
        if metadata is not None:
            result.result_metadata = metadata
        if variables is not None:
            result.variables = variables
        if region is not None:
            result.region = region

        result.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def delete_result(self, result_id: UUID) -> bool:
        """Delete a simulation result."""
        result = await self.get_result(result_id)
        if not result:
            return False

        # Delete associated file if exists
        if result.file_path and Path(result.file_path).exists():
            try:
                Path(result.file_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to delete result file: {e}")

        await self.db.delete(result)
        await self.db.commit()
        return True

    async def export_result(
        self,
        result_ids: List[UUID],
        format: str,
        options: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Export simulation results to various formats."""
        export_id = str(uuid.uuid4())
        export_dir = self.results_dir / "exports" / export_id
        export_dir.mkdir(parents=True, exist_ok=True)

        # Get results
        results = []
        for rid in result_ids:
            result = await self.get_result(rid)
            if result:
                results.append(result)

        if not results:
            raise ValueError("No valid results found for export")

        # Generate export based on format
        if format == "vtk":
            file_path = await self._export_vtk(results, export_dir, options, include_metadata)
        elif format == "csv":
            file_path = await self._export_csv(results, export_dir, options, include_metadata)
        elif format == "json":
            file_path = await self._export_json(results, export_dir, options, include_metadata)
        elif format == "hdf5":
            file_path = await self._export_hdf5(results, export_dir, options, include_metadata)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        file_size = Path(file_path).stat().st_size

        return {
            "export_id": export_id,
            "format": format,
            "file_path": str(file_path),
            "file_size": file_size,
            "status": ResultStatus.COMPLETED,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def _export_vtk(
        self,
        results: List[SimulationResult],
        export_dir: Path,
        options: Optional[Dict[str, Any]],
        include_metadata: bool,
    ) -> Path:
        """Export results to VTK format using pyvista/vtk."""
        file_path = export_dir / "results.vtk"
        pv = _import_pyvista()

        if pv is not None:
            # Use pyvista multi-block dataset to combine multiple results
            multi = pv.MultiBlock()
            for r in results:
                mesh = self._result_to_pyvista_mesh(pv, r)
                if mesh is not None:
                    multi[str(r.id)] = mesh
            try:
                pv.save(file_path, multi, binary=False)
                return file_path
            except Exception as e:
                logger.warning(f"pyvista VTK save failed, falling back to manual VTK: {e}")

        # Fallback: write a valid legacy VTK file with point/cell data from result metadata
        self._write_legacy_vtk(file_path, results)
        return file_path

    def _result_to_pyvista_mesh(self, pv, result: SimulationResult):
        """Convert a SimulationResult's stored data into a pyvista mesh.

        If the result already references a VTK-readable file, load it directly.
        Otherwise, build an UnstructuredGrid from metadata arrays.
        """
        # If the result has a file path that is a VTK file, load it
        if result.file_path:
            p = Path(result.file_path)
            if p.exists() and p.suffix.lower() in (".vtk", ".vtu", ".vtp", ".vts", ".vtr"):
                try:
                    return pv.read(str(p))
                except Exception as e:
                    logger.warning(f"Failed to read VTK file {p}: {e}")

        # Build from metadata arrays if present
        meta = result.result_metadata or {}
        points = meta.get("points")
        cells = meta.get("cells")
        cell_types = meta.get("cell_types")

        if points is not None and cells is not None and cell_types is not None:
            try:
                pts = np.asarray(points, dtype=np.float32)
                cell_arr = np.asarray(cells, dtype=np.int64)
                ct_arr = np.asarray(cell_types, dtype=np.int64)
                mesh = pv.UnstructuredGrid(cell_arr, ct_arr, pts)
                # Attach field data
                for var in result.variables:
                    arr = meta.get(var)
                    if arr is not None:
                        mesh.cell_data[var] = np.asarray(arr)
                return mesh
            except Exception as e:
                logger.warning(f"Failed to build mesh from metadata for result {result.id}: {e}")

        return None

    def _write_legacy_vtk(self, file_path: Path, results: List[SimulationResult]):
        """Write a minimal but valid legacy VTK file from result metadata."""
        all_points: List[List[float]] = []
        all_values: Dict[str, List[float]] = {}
        for r in results:
            meta = r.result_metadata or {}
            pts = meta.get("points")
            if pts:
                all_points.extend(pts)
            for var in r.variables:
                arr = meta.get(var)
                if arr:
                    all_values.setdefault(var, []).extend(arr)

        n_points = len(all_points)
        with open(file_path, "w") as f:
            f.write("# vtk DataFile Version 3.0\n")
            f.write("CFD Simulation Results Export\n")
            f.write("ASCII\n")
            f.write("DATASET POLYDATA\n")
            f.write(f"POINTS {n_points} float\n")
            for p in all_points:
                f.write(f"{p[0]} {p[1]} {p[2]}\n")
            f.write(f"POINT_DATA {n_points}\n")
            for var, vals in all_values.items():
                f.write(f"SCALARS {var} float 1\n")
                f.write("LOOKUP_TABLE default\n")
                for v in vals:
                    f.write(f"{v}\n")

    async def _export_csv(
        self,
        results: List[SimulationResult],
        export_dir: Path,
        options: Optional[Dict[str, Any]],
        include_metadata: bool,
    ) -> Path:
        """Export results to CSV format."""
        file_path = export_dir / "results.csv"
        import csv
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["result_id", "name", "result_type", "time_step", "time_value", "variables"])
            for r in results:
                writer.writerow([
                    str(r.id), r.name, r.result_type.value,
                    r.time_step, r.time_value, ",".join(r.variables)
                ])
        return file_path

    async def _export_json(
        self,
        results: List[SimulationResult],
        export_dir: Path,
        options: Optional[Dict[str, Any]],
        include_metadata: bool,
    ) -> Path:
        """Export results to JSON format."""
        file_path = export_dir / "results.json"
        data = []
        for r in results:
            item = {
                "id": str(r.id),
                "name": r.name,
                "result_type": r.result_type.value,
                "time_step": r.time_step,
                "time_value": r.time_value,
                "variables": r.variables,
            }
            if include_metadata:
                item["metadata"] = r.result_metadata
            data.append(item)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return file_path

    async def _export_hdf5(
        self,
        results: List[SimulationResult],
        export_dir: Path,
        options: Optional[Dict[str, Any]],
        include_metadata: bool,
    ) -> Path:
        """Export results to HDF5 format using h5py."""
        file_path = export_dir / "results.h5"
        h5py = _import_h5py()

        if h5py is not None:
            with h5py.File(str(file_path), "w") as f:
                for r in results:
                    grp = f.create_group(str(r.id))
                    grp.attrs["name"] = r.name
                    grp.attrs["result_type"] = r.result_type.value
                    grp.attrs["status"] = r.status.value
                    if r.time_step is not None:
                        grp.attrs["time_step"] = r.time_step
                    if r.time_value is not None:
                        grp.attrs["time_value"] = r.time_value
                    if r.region:
                        grp.attrs["region"] = r.region

                    # Store variables list
                    grp.attrs["variables"] = json.dumps(r.variables)

                    # Store metadata arrays as datasets
                    meta = r.result_metadata or {}
                    for key, val in meta.items():
                        try:
                            if isinstance(val, (list, tuple)):
                                grp.create_dataset(key, data=np.asarray(val))
                            elif isinstance(val, (int, float, str)):
                                grp.attrs[key] = val
                            elif isinstance(val, dict):
                                grp.attrs[key] = json.dumps(val)
                        except Exception as e:
                            logger.warning(f"Failed to store metadata key '{key}' for result {r.id}: {e}")

                    # Store min/max values
                    if r.min_values:
                        grp.attrs["min_values"] = json.dumps(r.min_values)
                    if r.max_values:
                        grp.attrs["max_values"] = json.dumps(r.max_values)

                    # If there is a file path with actual data, try to embed it
                    if r.file_path and Path(r.file_path).exists():
                        try:
                            raw = Path(r.file_path).read_bytes()
                            grp.create_dataset("_raw_file", data=np.frombuffer(raw, dtype=np.uint8))
                        except Exception as e:
                            logger.warning(f"Failed to embed raw file for result {r.id}: {e}")
            return file_path

        # Fallback: write a JSON file with .h5 extension if h5py unavailable
        logger.warning("h5py unavailable, writing JSON fallback as .h5")
        file_path = export_dir / "results.h5"
        data = []
        for r in results:
            item = {
                "id": str(r.id),
                "name": r.name,
                "result_type": r.result_type.value,
                "time_step": r.time_step,
                "time_value": r.time_value,
                "variables": r.variables,
                "metadata": r.result_metadata,
                "min_values": r.min_values,
                "max_values": r.max_values,
            }
            data.append(item)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return file_path

    async def generate_visualization(
        self,
        result_id: UUID,
        visualization_type: str,
        field_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        color_map: str = "viridis",
        opacity: float = 1.0,
        show_edges: bool = False,
        line_width: float = 1.0,
        point_size: float = 5.0,
    ) -> Dict[str, Any]:
        """Generate visualization for a result using pyvista."""
        result = await self.get_result(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        visualization_id = str(uuid.uuid4())
        pv = _import_pyvista()

        image_data = None
        vtk_data = None

        if pv is not None:
            mesh = self._result_to_pyvista_mesh(pv, result)
            if mesh is not None:
                # Apply field data if available
                if field_name and field_name in mesh.cell_data:
                    mesh.set_active_scalars(field_name)
                elif field_name and field_name in mesh.point_data:
                    mesh.set_active_scalars(field_name, preference="point")

                # Generate screenshot
                try:
                    plotter = pv.Plotter(off_screen=True)
                    plotter.add_mesh(
                        mesh,
                        cmap=color_map,
                        opacity=opacity,
                        show_edges=show_edges,
                        line_width=line_width,
                        point_size=point_size,
                    )
                    if visualization_type == "contour" and field_name:
                        contours = mesh.contour(parameters.get("n_contours", 10) if parameters else 10)
                        plotter.add_mesh(contours, cmap=color_map)
                    elif visualization_type == "slice" and parameters:
                        origin = parameters.get("origin", [0, 0, 0])
                        normal = parameters.get("normal", [0, 0, 1])
                        sliced = mesh.slice(normal=normal, origin=origin)
                        plotter.clear()
                        plotter.add_mesh(sliced, cmap=color_map, opacity=opacity, show_edges=show_edges)
                    elif visualization_type == "streamlines" and parameters:
                        seed_points = parameters.get("seed_points", [])
                        if seed_points:
                            streamlines = mesh.streamlines_from_source(
                                pv.PolyData(np.asarray(seed_points, dtype=np.float32)),
                                vectors=field_name,
                                max_step_length=parameters.get("step_size", 1.0),
                                max_steps=parameters.get("max_steps", 1000),
                            )
                            plotter.clear()
                            plotter.add_mesh(streamlines, cmap=color_map)

                    plotter.screenshot(str(self.results_dir / f"{visualization_id}.png"))
                    buf = io.BytesIO()
                    plotter.screenshot(buf)
                    image_data = base64.b64encode(buf.getvalue()).decode("ascii")
                    plotter.close()
                except Exception as e:
                    logger.warning(f"pyvista visualization rendering failed: {e}")

                # Export VTK data as base64
                try:
                    buf = io.BytesIO()
                    pv.save(buf, mesh, binary=True)
                    vtk_data = base64.b64encode(buf.getvalue()).decode("ascii")
                except Exception as e:
                    logger.warning(f"VTK data export failed: {e}")

        return {
            "visualization_id": visualization_id,
            "result_id": str(result_id),
            "visualization_type": visualization_type,
            "field_name": field_name,
            "parameters": parameters or {},
            "image_data": image_data,
            "vtk_data": vtk_data,
            "metadata": {
                "color_map": color_map,
                "opacity": opacity,
                "show_edges": show_edges,
                "line_width": line_width,
                "point_size": point_size,
            },
            "created_at": datetime.utcnow().isoformat(),
        }

    async def create_probe(
        self,
        simulation_id: UUID,
        points: List[List[float]],
        fields: List[str],
        time_steps: Optional[List[float]] = None,
        interpolation: str = "cellPointFace",
    ) -> Dict[str, Any]:
        """Create probe at specified points using pyvista."""
        probe_id = str(uuid.uuid4())
        ts = time_steps or [0.0]
        pv = _import_pyvista()

        data: Dict[str, Any] = {field: [] for field in fields}

        # Load results for this simulation
        results = await self._get_simulation_results(simulation_id)
        if not results:
            logger.warning(f"No results found for simulation {simulation_id}")
            for field in fields:
                for _ in ts:
                    data[field].append([[0.0] * len(points)])
        elif pv is not None:
            pts = np.asarray(points, dtype=np.float32)
            for t in ts:
                # Find result matching time step
                result = self._find_result_for_time(results, t)
                mesh = self._result_to_pyvista_mesh(pv, result) if result else None
                if mesh is not None:
                    probe_points = pv.PolyData(pts)
                    try:
                        probed = mesh.probe(probe_points)
                        for field in fields:
                            if field in probed.point_data:
                                data[field].append(probed.point_data[field].tolist())
                            elif field in probed.cell_data:
                                data[field].append(probed.cell_data[field].tolist())
                            else:
                                data[field].append([[0.0] * len(points)])
                    except Exception as e:
                        logger.warning(f"Probe failed at t={t}: {e}")
                        for field in fields:
                            data[field].append([[0.0] * len(points)])
                else:
                    for field in fields:
                        data[field].append([[0.0] * len(points)])
        else:
            # No pyvista — return zeros
            for field in fields:
                for _ in ts:
                    data[field].append([[0.0] * len(points)])

        return {
            "probe_id": probe_id,
            "simulation_id": str(simulation_id),
            "points": points,
            "fields": fields,
            "time_steps": ts,
            "data": data,
            "interpolation": interpolation,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def _get_simulation_results(self, simulation_id: UUID) -> List[SimulationResult]:
        """Retrieve all results for a given simulation."""
        stmt = select(SimulationResult).where(
            SimulationResult.simulation_id == simulation_id
        ).order_by(SimulationResult.time_step)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    def _find_result_for_time(results: List[SimulationResult], time_value: float) -> Optional[SimulationResult]:
        """Find the result closest to the requested time value."""
        best = None
        best_diff = float("inf")
        for r in results:
            if r.time_value is None:
                continue
            diff = abs(r.time_value - time_value)
            if diff < best_diff:
                best_diff = diff
                best = r
        return best or (results[0] if results else None)

    async def create_cut_plane(
        self,
        simulation_id: UUID,
        origin: List[float],
        normal: List[float],
        fields: List[str],
        time_step: Optional[float] = None,
        resolution: List[int] = [100, 100],
    ) -> Dict[str, Any]:
        """Create cut plane through simulation data using pyvista."""
        cut_plane_id = str(uuid.uuid4())
        pv = _import_pyvista()

        data: Dict[str, Any] = {}
        bounds = [0, 1, 0, 1, 0, 1]

        results = await self._get_simulation_results(simulation_id)
        if results and pv is not None:
            result = self._find_result_for_time(results, time_step) if time_step is not None else results[0]
            mesh = self._result_to_pyvista_mesh(pv, result) if result else None
            if mesh is not None:
                try:
                    # Create a structured plane and probe it
                    plane = pv.Plane(
                        center=origin,
                        direction=normal,
                        i_size=resolution[0],
                        j_size=resolution[1],
                        i_resolution=resolution[0] - 1,
                        j_resolution=resolution[1] - 1,
                    )
                    sliced = mesh.probe(plane)
                    bounds = list(mesh.bounds)
                    for field in fields:
                        if field in sliced.point_data:
                            data[field] = sliced.point_data[field].tolist()
                        elif field in sliced.cell_data:
                            data[field] = sliced.cell_data[field].tolist()
                        else:
                            data[field] = []
                except Exception as e:
                    logger.warning(f"Cut plane creation failed: {e}")
                    for field in fields:
                        data[field] = []
            else:
                for field in fields:
                    data[field] = []
        else:
            for field in fields:
                data[field] = []

        return {
            "cut_plane_id": cut_plane_id,
            "simulation_id": str(simulation_id),
            "origin": origin,
            "normal": normal,
            "fields": fields,
            "time_step": time_step,
            "resolution": resolution,
            "data": data,
            "bounds": bounds,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def create_streamlines(
        self,
        simulation_id: UUID,
        seed_type: str,
        seed_points: List[List[float]],
        seed_resolution: int,
        field_name: str,
        integration_direction: str,
        max_steps: int,
        step_size: float,
        time_step: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create streamlines from vector field using pyvista."""
        streamline_id = str(uuid.uuid4())
        pv = _import_pyvista()

        streamlines: List[Dict[str, Any]] = []

        results = await self._get_simulation_results(simulation_id)
        if results and pv is not None:
            result = self._find_result_for_time(results, time_step) if time_step is not None else results[0]
            mesh = self._result_to_pyvista_mesh(pv, result) if result else None
            if mesh is not None and field_name in mesh.point_data:
                try:
                    # Build seed source
                    if seed_type == "point" and seed_points:
                        seed = pv.PolyData(np.asarray(seed_points, dtype=np.float32))
                    elif seed_type == "line" and len(seed_points) >= 2:
                        seed = pv.Line(
                            np.asarray(seed_points[0], dtype=np.float32),
                            np.asarray(seed_points[1], dtype=np.float32),
                            resolution=seed_resolution,
                        )
                    elif seed_type == "plane" and len(seed_points) >= 3:
                        seed = pv.Plane(
                            center=np.asarray(seed_points[0], dtype=np.float32),
                            i_size=10, j_size=10,
                            i_resolution=seed_resolution, j_resolution=seed_resolution,
                        )
                    else:
                        seed = pv.PolyData(np.asarray(seed_points, dtype=np.float32)) if seed_points else None

                    if seed is not None:
                        sl = mesh.streamlines_from_source(
                            seed,
                            vectors=field_name,
                            integration_direction=integration_direction,
                            max_steps=max_steps,
                            max_step_length=step_size,
                        )
                        # Extract individual streamlines
                        if sl.n_points > 0:
                            streamlines.append({
                                "points": sl.points.tolist(),
                                "values": sl.point_data.get(field_name, np.zeros(sl.n_points)).tolist() if field_name in sl.point_data else [],
                            })
                except Exception as e:
                    logger.warning(f"Streamline generation failed: {e}")

        if not streamlines:
            # Fallback: return empty streamlines
            for i in range(min(seed_resolution, 1)):
                streamlines.append({
                    "points": [],
                    "values": [],
                })

        return {
            "streamline_id": streamline_id,
            "simulation_id": str(simulation_id),
            "seed_type": seed_type,
            "seed_points": seed_points,
            "field_name": field_name,
            "integration_direction": integration_direction,
            "max_steps": max_steps,
            "step_size": step_size,
            "time_step": time_step,
            "streamlines": streamlines,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def create_animation(
        self,
        simulation_id: UUID,
        visualization_type: str,
        field_name: str,
        time_steps: List[float],
        parameters: Optional[Dict[str, Any]] = None,
        frame_rate: int = 10,
        resolution: List[int] = [1920, 1080],
        format: str = "mp4",
    ) -> Dict[str, Any]:
        """Create animation from time-series data using pyvista."""
        animation_id = str(uuid.uuid4())
        export_dir = self.results_dir / "animations" / animation_id
        export_dir.mkdir(parents=True, exist_ok=True)
        file_path = export_dir / f"animation.{format}"
        pv = _import_pyvista()

        results = await self._get_simulation_results(simulation_id)
        if not results:
            return {
                "animation_id": animation_id,
                "file_path": str(file_path),
                "status": ResultStatus.FAILED,
                "error": "No simulation results found",
            }

        if pv is None:
            return {
                "animation_id": animation_id,
                "file_path": str(file_path),
                "status": ResultStatus.FAILED,
                "error": "pyvista not available",
            }

        # Filter results by requested time steps
        if time_steps:
            filtered = [r for r in results if r.time_value is not None and r.time_value in time_steps]
            results = filtered or results

        try:
            plotter = pv.Plotter(off_screen=True, window_size=resolution)
            for idx, result in enumerate(results):
                mesh = self._result_to_pyvista_mesh(pv, result)
                if mesh is None:
                    continue
                if field_name in mesh.cell_data:
                    mesh.set_active_scalars(field_name)
                elif field_name in mesh.point_data:
                    mesh.set_active_scalars(field_name, preference="point")
                plotter.clear()
                plotter.add_mesh(mesh, cmap=parameters.get("color_map", "viridis") if parameters else "viridis")
                plotter.screenshot(str(export_dir / f"frame_{idx:05d}.png"))
            plotter.close()

            # Try to create video using imageio
            try:
                import imageio
                writer = imageio.get_writer(str(file_path), fps=frame_rate)
                for idx in range(len(results)):
                    frame_path = export_dir / f"frame_{idx:05d}.png"
                    if frame_path.exists():
                        writer.append_data(imageio.imread(str(frame_path)))
                writer.close()
                status = ResultStatus.COMPLETED
                error = None
            except Exception as e:
                logger.warning(f"imageio video creation failed: {e}")
                status = ResultStatus.COMPLETED
                error = f"Video encoding failed: {e}; frames saved in {export_dir}"
        except Exception as e:
            logger.error(f"Animation creation failed: {e}")
            status = ResultStatus.FAILED
            error = str(e)

        return {
            "animation_id": animation_id,
            "file_path": str(file_path),
            "status": status,
            "error": error,
        }

    async def compare_simulations(
        self,
        simulation_ids: List[UUID],
        field_name: str,
        time_step: Optional[float] = None,
        comparison_type: str = "difference",
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare multiple simulation results using numpy."""
        comparison_id = str(uuid.uuid4())
        pv = _import_pyvista()

        # Load results for each simulation
        sim_data: Dict[str, Any] = {}
        for sim_id in simulation_ids:
            results = await self._get_simulation_results(sim_id)
            if not results:
                continue
            result = self._find_result_for_time(results, time_step) if time_step is not None else results[0]
            if result is None:
                continue
            field_values = None
            if pv is not None:
                mesh = self._result_to_pyvista_mesh(pv, result)
                if mesh is not None:
                    if field_name in mesh.cell_data:
                        field_values = np.asarray(mesh.cell_data[field_name], dtype=np.float64)
                    elif field_name in mesh.point_data:
                        field_values = np.asarray(mesh.point_data[field_name], dtype=np.float64)
            if field_values is None:
                # Fallback: use result metadata
                meta = result.result_metadata or {}
                if field_name in (result.min_values or {}):
                    field_values = np.array([result.min_values.get(field_name, 0.0), result.max_values.get(field_name, 0.0)])
                else:
                    field_values = np.array([])
            sim_data[str(sim_id)] = field_values

        # Compute comparison
        data: Dict[str, Any] = {}
        stats = {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0}

        if len(sim_data) >= 2:
            arrays = list(sim_data.values())
            # Align lengths (truncate to shortest)
            min_len = min(len(a) for a in arrays if len(a) > 0)
            arrays = [a[:min_len] for a in arrays if len(a) > 0]
            if arrays:
                if comparison_type == "difference":
                    diff = arrays[0] - arrays[1]
                    data["difference"] = diff.tolist()
                    stats = {
                        "min": float(np.min(diff)),
                        "max": float(np.max(diff)),
                        "mean": float(np.mean(diff)),
                        "std": float(np.std(diff)),
                    }
                elif comparison_type == "ratio":
                    with np.errstate(divide="ignore", invalid="ignore"):
                        ratio = np.where(arrays[1] != 0, arrays[0] / arrays[1], 0.0)
                    data["ratio"] = ratio.tolist()
                    stats = {
                        "min": float(np.min(ratio)),
                        "max": float(np.max(ratio)),
                        "mean": float(np.mean(ratio)),
                        "std": float(np.std(ratio)),
                    }
                elif comparison_type == "absolute_difference":
                    abs_diff = np.abs(arrays[0] - arrays[1])
                    data["absolute_difference"] = abs_diff.tolist()
                    stats = {
                        "min": float(np.min(abs_diff)),
                        "max": float(np.max(abs_diff)),
                        "mean": float(np.mean(abs_diff)),
                        "std": float(np.std(abs_diff)),
                    }
                else:
                    data["values"] = {k: v.tolist() for k, v in sim_data.items()}

        return {
            "comparison_id": comparison_id,
            "simulation_ids": [str(s) for s in simulation_ids],
            "field_name": field_name,
            "time_step": time_step,
            "comparison_type": comparison_type,
            "region": region,
            "data": data,
            "statistics": stats,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def generate_report(
        self,
        simulation_id: UUID,
        template: str = "standard",
        sections: Optional[List[str]] = None,
        include_images: bool = True,
        format: str = "pdf",
    ) -> Dict[str, Any]:
        """Generate simulation report using jinja2."""
        report_id = str(uuid.uuid4())
        export_dir = self.results_dir / "reports" / report_id
        export_dir.mkdir(parents=True, exist_ok=True)
        file_path = export_dir / f"report.{format}"

        # Gather simulation results
        results = await self._get_simulation_results(simulation_id)

        # Build report data
        report_data = {
            "report_id": report_id,
            "simulation_id": str(simulation_id),
            "template": template,
            "sections": sections or ["summary", "results", "statistics"],
            "include_images": include_images,
            "generated_at": datetime.utcnow().isoformat(),
            "results": [],
        }

        for r in results:
            report_data["results"].append({
                "name": r.name,
                "result_type": r.result_type.value if r.result_type else None,
                "status": r.status.value if r.status else None,
                "time_step": r.time_step,
                "time_value": r.time_value,
                "variables": r.variables or [],
                "min_values": r.min_values or {},
                "max_values": r.max_values or {},
                "region": r.region,
            })

        jinja2 = _import_jinja2()

        if jinja2 is not None:
            # Use jinja2 to render HTML report
            template_str = """<!DOCTYPE html>
<html>
<head><title>CFD Simulation Report - {{ simulation_id }}</title></head>
<body>
<h1>CFD Simulation Report</h1>
<p>Simulation ID: {{ simulation_id }}</p>
<p>Generated: {{ generated_at }}</p>
<p>Template: {{ template }}</p>
<h2>Results ({{ results|length }})</h2>
<table border="1">
<tr><th>Name</th><th>Type</th><th>Status</th><th>Time Step</th><th>Time Value</th><th>Variables</th></tr>
{% for r in results %}
<tr>
<td>{{ r.name }}</td><td>{{ r.result_type }}</td><td>{{ r.status }}</td>
<td>{{ r.time_step }}</td><td>{{ r.time_value }}</td><td>{{ r.variables|join(', ') }}</td>
</tr>
{% endfor %}
</table>
{% if include_images %}
<h2>Visualization Images</h2>
<p>Images would be embedded here.</p>
{% endif %}
</body>
</html>"""
            env = jinja2.Environment(autoescape=True)
            t = env.from_string(template_str)
            html_content = t.render(**report_data)

            if format == "pdf":
                # Try weasyprint for PDF, fallback to HTML
                try:
                    from weasyprint import HTML
                    HTML(string=html_content).write_pdf(str(file_path))
                except Exception as e:
                    logger.warning(f"weasyprint not available: {e}")
                    html_path = export_dir / "report.html"
                    html_path.write_text(html_content, encoding="utf-8")
                    file_path = html_path
            else:
                file_path = export_dir / "report.html"
                file_path.write_text(html_content, encoding="utf-8")
        else:
            # Fallback: plain text report
            txt_path = export_dir / "report.txt"
            lines = [f"CFD Simulation Report", f"Simulation ID: {simulation_id}", f"Generated: {report_data['generated_at']}", ""]
            for r in report_data["results"]:
                lines.append(f"  - {r['name']} ({r['result_type']}) status={r['status']} time={r['time_value']}")
            txt_path.write_text("\n".join(lines), encoding="utf-8")
            file_path = txt_path

        file_size = file_path.stat().st_size if file_path.exists() else 0

        return {
            "report_id": report_id,
            "file_path": str(file_path),
            "file_size": file_size,
            "status": ResultStatus.COMPLETED,
        }

    async def get_result_statistics(self, result_id: UUID) -> Dict[str, Any]:
        """Get statistical summary of result data using numpy."""
        result = await self.get_result(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        statistics: Dict[str, Any] = {}
        pv = _import_pyvista()

        # Try to get actual field data from pyvista mesh
        field_data: Dict[str, np.ndarray] = {}
        if pv is not None:
            mesh = self._result_to_pyvista_mesh(pv, result)
            if mesh is not None:
                for var in (result.variables or []):
                    if var in mesh.cell_data:
                        field_data[var] = np.asarray(mesh.cell_data[var], dtype=np.float64)
                    elif var in mesh.point_data:
                        field_data[var] = np.asarray(mesh.point_data[var], dtype=np.float64)

        for var in (result.variables or []):
            if var in field_data and len(field_data[var]) > 0:
                arr = field_data[var]
                statistics[var] = {
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "mean": float(np.mean(arr)),
                    "std": float(np.std(arr)),
                    "count": int(arr.size),
                }
            else:
                # Fallback: use stored min/max values
                min_v = (result.min_values or {}).get(var, 0.0)
                max_v = (result.max_values or {}).get(var, 0.0)
                statistics[var] = {
                    "min": float(min_v),
                    "max": float(max_v),
                    "mean": float((min_v + max_v) / 2),
                    "std": 0.0,
                    "count": 0,
                }

        return {
            "result_id": str(result_id),
            "variables": result.variables,
            "statistics": statistics,
        }

    async def get_field_histogram(
        self,
        result_id: UUID,
        field_name: str,
        bins: int = 50,
    ) -> Dict[str, Any]:
        """Get histogram of field values using numpy."""
        result = await self.get_result(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        if field_name not in (result.variables or []):
            raise ValueError(f"Field {field_name} not found in result")

        # Try to get actual field data from pyvista mesh
        field_values = None
        pv = _import_pyvista()
        if pv is not None:
            mesh = self._result_to_pyvista_mesh(pv, result)
            if mesh is not None:
                if field_name in mesh.cell_data:
                    field_values = np.asarray(mesh.cell_data[field_name], dtype=np.float64)
                elif field_name in mesh.point_data:
                    field_values = np.asarray(mesh.point_data[field_name], dtype=np.float64)

        if field_values is None or len(field_values) == 0:
            # Fallback: synthesize from stored min/max
            min_v = (result.min_values or {}).get(field_name, 0.0)
            max_v = (result.max_values or {}).get(field_name, 0.0)
            field_values = np.linspace(min_v, max_v, 100)

        hist, bin_edges = np.histogram(field_values, bins=bins)

        return {
            "result_id": str(result_id),
            "field_name": field_name,
            "bins": bin_edges.tolist(),
            "counts": hist.tolist(),
        }

    async def extract_surface(
        self,
        result_id: UUID,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract surface mesh from volume result using pyvista."""
        result = await self.get_result(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        surface_id = str(uuid.uuid4())
        export_dir = self.results_dir / "surfaces" / surface_id
        export_dir.mkdir(parents=True, exist_ok=True)
        file_path = export_dir / "surface.vtk"

        pv = _import_pyvista()
        if pv is None:
            return {
                "surface_id": surface_id,
                "result_id": str(result_id),
                "region": region,
                "file_path": str(file_path),
                "bounds": [0, 1, 0, 1, 0, 1],
                "area": 0.0,
                "status": ResultStatus.FAILED,
                "error": "pyvista not available",
            }

        mesh = self._result_to_pyvista_mesh(pv, result)
        if mesh is None:
            return {
                "surface_id": surface_id,
                "result_id": str(result_id),
                "region": region,
                "file_path": str(file_path),
                "bounds": [0, 1, 0, 1, 0, 1],
                "area": 0.0,
                "status": ResultStatus.FAILED,
                "error": "Could not load mesh from result",
            }

        try:
            surface = mesh.extract_surface()
            if region and "region" in surface.cell_data:
                surface = surface.threshold(value=[0.5, 1.5], scalars="region")
            surface.save(str(file_path))
            bounds = list(surface.bounds)
            area = float(surface.area) if hasattr(surface, "area") else 0.0
            status = ResultStatus.COMPLETED
            error = None
        except Exception as e:
            logger.error(f"Surface extraction failed: {e}")
            bounds = [0, 1, 0, 1, 0, 1]
            area = 0.0
            status = ResultStatus.FAILED
            error = str(e)

        return {
            "surface_id": surface_id,
            "result_id": str(result_id),
            "region": region,
            "file_path": str(file_path),
            "bounds": bounds,
            "area": area,
            "status": status,
            "error": error,
        }

    async def get_paraview_state(
        self,
        simulation_id: UUID,
        result_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """Generate ParaView state file (.pvsm) for simulation."""
        state_id = str(uuid.uuid4())
        export_dir = self.results_dir / "paraview" / state_id
        export_dir.mkdir(parents=True, exist_ok=True)
        file_path = export_dir / "state.pvsm"

        # Gather result file paths
        results = await self._get_simulation_results(simulation_id)
        if result_ids:
            result_set = set(result_ids)
            results = [r for r in results if r.id in result_set] or results

        # Generate a minimal but valid ParaView state XML
        readers_xml = ""
        for idx, r in enumerate(results):
            readers_xml += f"""
    <Proxy group="sources" type="LegacyVTKFileReader" id="{idx + 1}" servers="1">
      <Property name="FileName" id="{idx + 1}.FileName" number_of_elements="1">
        <Element index="0" value="{r.file_path or ''}"/>
      </Property>
      <Property name="ActiveScalars" id="{idx + 1}.ActiveScalars" number_of_elements="1">
        <Element index="0" value="{(r.variables or [''])[0] if r.variables else ''}"/>
      </Property>
    </Proxy>"""

        pvsm_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ParaView state generated="{datetime.utcnow().isoformat()}">
  <ServerManagerState version="5.11.0">
    <Connection id="0" />
{readers_xml}
  </ServerManagerState>
  <View id="0" type="RenderView" servers="21">
    <Property name="ViewSize" id="0.ViewSize" number_of_elements="2">
      <Element index="0" value="1920"/>
      <Element index="1" value="1080"/>
    </Property>
  </View>
</ParaView>"""

        file_path.write_text(pvsm_content, encoding="utf-8")
        file_size = file_path.stat().st_size if file_path.exists() else 0

        return {
            "state_id": state_id,
            "simulation_id": str(simulation_id),
            "file_path": str(file_path),
            "file_size": file_size,
            "result_ids": [str(r.id) for r in results],
        }

    async def list_visualizations(
        self,
        result_id: Optional[UUID] = None,
        simulation_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """List generated visualizations by scanning results directory."""
        visualizations: List[Dict[str, Any]] = []

        # Scan known visualization subdirectories
        subdirs = ["visualizations", "animations", "surfaces", "reports", "paraview"]
        for subdir in subdirs:
            dir_path = self.results_dir / subdir
            if not dir_path.exists():
                continue
            for item in dir_path.iterdir():
                if not item.is_dir():
                    continue
                # Find the main file in the directory
                files = list(item.iterdir())
                main_file = None
                for f in files:
                    if f.suffix in [".png", ".vtk", ".mp4", ".html", ".pdf", ".pvsm", ".txt"]:
                        main_file = f
                        break
                if main_file is None and files:
                    main_file = files[0]

                file_size = main_file.stat().st_size if main_file and main_file.exists() else 0
                stat = item.stat()
                visualizations.append({
                    "visualization_id": item.name,
                    "type": subdir.rstrip("s") if subdir.endswith("s") else subdir,
                    "file_path": str(main_file) if main_file else str(item),
                    "file_size": file_size,
                    "created_at": datetime.utcfromtimestamp(stat.st_ctime).isoformat(),
                    "result_id": str(result_id) if result_id else None,
                    "simulation_id": str(simulation_id) if simulation_id else None,
                })

        # Filter by simulation_id if provided (match by directory name prefix or metadata)
        if simulation_id is not None:
            sim_str = str(simulation_id)
            visualizations = [v for v in visualizations if sim_str in v.get("file_path", "")]

        return visualizations

    async def delete_visualization(self, visualization_id: str) -> bool:
        """Delete a generated visualization by removing its directory/files."""
        # Search all known subdirectories for the visualization_id
        subdirs = ["visualizations", "animations", "surfaces", "reports", "paraview"]
        for subdir in subdirs:
            dir_path = self.results_dir / subdir / visualization_id
            if dir_path.exists() and dir_path.is_dir():
                try:
                    import shutil
                    shutil.rmtree(str(dir_path))
                    return True
                except Exception as e:
                    logger.error(f"Failed to delete visualization {visualization_id}: {e}")
                    return False

        # Also check if it's a direct file path
        for subdir in subdirs:
            parent = self.results_dir / subdir
            if parent.exists():
                for item in parent.iterdir():
                    if item.name.startswith(visualization_id):
                        try:
                            if item.is_dir():
                                import shutil
                                shutil.rmtree(str(item))
                            else:
                                item.unlink()
                            return True
                        except Exception as e:
                            logger.error(f"Failed to delete {item}: {e}")
                            return False

        logger.warning(f"Visualization {visualization_id} not found")
        return False