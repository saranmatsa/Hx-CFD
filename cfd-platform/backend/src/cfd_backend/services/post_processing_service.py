"""Post-processing service for simulation results and visualization."""

import uuid
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.models.simulation import Simulation
from cfd_backend.models.simulation_result import SimulationResult, ResultType, ResultStatus
from cfd_backend.models.project import Project

logger = logging.getLogger(__name__)


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
        """Export results to VTK format."""
        file_path = export_dir / "results.vtk"
        # Placeholder - would use pyvista or vtk to write actual VTK files
        with open(file_path, "w") as f:
            f.write("# vtk DataFile Version 3.0\n")
            f.write("CFD Simulation Results\n")
            f.write("ASCII\n")
            f.write("DATASET UNSTRUCTURED_GRID\n")
            f.write("POINTS 0 float\n")
            f.write("CELLS 0 0\n")
            f.write("CELL_TYPES 0\n")
        return file_path

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
        """Export results to HDF5 format."""
        file_path = export_dir / "results.h5"
        # Placeholder - would use h5py to write actual HDF5
        with open(file_path, "w") as f:
            f.write("HDF5 placeholder")
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
        """Generate visualization for a result."""
        result = await self.get_result(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        visualization_id = str(uuid.uuid4())

        # Placeholder - would use pyvista/paraview to generate actual visualization
        return {
            "visualization_id": visualization_id,
            "result_id": str(result_id),
            "visualization_type": visualization_type,
            "field_name": field_name,
            "parameters": parameters or {},
            "image_data": None,  # Base64 encoded image
            "vtk_data": None,    # Base64 encoded VTK data
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
        """Create probe at specified points."""
        probe_id = str(uuid.uuid4())

        # Placeholder - would use pyvista/OpenFOAM to probe fields
        data = {}
        for field in fields:
            data[field] = []
            for _ in time_steps or [0.0]:
                data[field].append([[0.0] * len(points)])

        return {
            "probe_id": probe_id,
            "simulation_id": str(simulation_id),
            "points": points,
            "fields": fields,
            "time_steps": time_steps or [0.0],
            "data": data,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def create_cut_plane(
        self,
        simulation_id: UUID,
        origin: List[float],
        normal: List[float],
        fields: List[str],
        time_step: Optional[float] = None,
        resolution: List[int] = [100, 100],
    ) -> Dict[str, Any]:
        """Create cut plane through simulation data."""
        cut_plane_id = str(uuid.uuid4())

        # Placeholder - would use pyvista to create cut plane
        return {
            "cut_plane_id": cut_plane_id,
            "simulation_id": str(simulation_id),
            "origin": origin,
            "normal": normal,
            "fields": fields,
            "time_step": time_step,
            "resolution": resolution,
            "data": {},
            "bounds": [0, 1, 0, 1, 0, 1],
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
        """Create streamlines from vector field."""
        streamline_id = str(uuid.uuid4())

        # Placeholder - would use pyvista to generate streamlines
        streamlines = []
        for i in range(seed_resolution):
            streamlines.append({
                "points": [[0, 0, 0], [1, 1, 1]],
                "values": [0.0, 1.0],
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
        """Create animation from time-series data."""
        animation_id = str(uuid.uuid4())
        export_dir = self.results_dir / "animations" / animation_id
        export_dir.mkdir(parents=True, exist_ok=True)

        # Placeholder - would use pyvista/ffmpeg to create animation
        file_path = export_dir / f"animation.{format}"

        return {
            "animation_id": animation_id,
            "file_path": str(file_path),
            "status": ResultStatus.PENDING,
        }

    async def compare_simulations(
        self,
        simulation_ids: List[UUID],
        field_name: str,
        time_step: Optional[float] = None,
        comparison_type: str = "difference",
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare multiple simulation results."""
        comparison_id = str(uuid.uuid4())

        # Placeholder - would load and compare simulation data
        return {
            "comparison_id": comparison_id,
            "data": {},
            "statistics": {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "std": 0.0,
            },
        }

    async def generate_report(
        self,
        simulation_id: UUID,
        template: str = "standard",
        sections: Optional[List[str]] = None,
        include_images: bool = True,
        include_tables: bool = True,
        format: str = "pdf",
    ) -> Dict[str, Any]:
        """Generate simulation report."""
        report_id = str(uuid.uuid4())
        export_dir = self.results_dir / "reports" / report_id
        export_dir.mkdir(parents=True, exist_ok=True)

        # Placeholder - would use jinja2/weasyprint to generate report
        file_path = export_dir / f"report.{format}"

        return {
            "report_id": report_id,
            "file_path": str(file_path),
            "file_size": 0,
            "status": ResultStatus.PENDING,
        }

    async def get_result_statistics(self, result_id: UUID) -> Dict[str, Any]:
        """Get statistical summary of result data."""
        result = await self.get_result(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        # Placeholder - would compute actual statistics from data
        return {
            "result_id": str(result_id),
            "variables": result.variables,
            "statistics": {
                var: {
                    "min": 0.0,
                    "max": 0.0,
                    "mean": 0.0,
                    "std": 0.0,
                    "count": 0,
                }
                for var in result.variables
            },
        }

    async def get_field_histogram(
        self,
        result_id: UUID,
        field_name: str,
        bins: int = 50,
    ) -> Dict[str, Any]:
        """Get histogram of field values."""
        result = await self.get_result(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        if field_name not in result.variables:
            raise ValueError(f"Field {field_name} not found in result")

        # Placeholder - would compute actual histogram from data
        import numpy as np
        hist, bin_edges = np.histogram([], bins=bins)

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
        """Extract surface mesh from volume result."""
        result = await self.get_result(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        surface_id = str(uuid.uuid4())
        export_dir = self.results_dir / "surfaces" / surface_id
        export_dir.mkdir(parents=True, exist_ok=True)

        # Placeholder - would use pyvista to extract surface
        file_path = export_dir / "surface.vtk"

        return {
            "surface_id": surface_id,
            "result_id": str(result_id),
            "region": region,
            "file_path": str(file_path),
            "bounds": [0, 1, 0, 1, 0, 1],
            "area": 0.0,
        }

    async def get_paraview_state(
        self,
        simulation_id: UUID,
        result_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """Generate ParaView state file for simulation."""
        state_id = str(uuid.uuid4())
        export_dir = self.results_dir / "paraview" / state_id
        export_dir.mkdir(parents=True, exist_ok=True)

        # Placeholder - would generate actual .pvsm state file
        file_path = export_dir / "state.pvsm"

        return {
            "state_id": state_id,
            "simulation_id": str(simulation_id),
            "file_path": str(file_path),
            "result_ids": [str(r) for r in result_ids] if result_ids else [],
        }

    async def list_visualizations(
        self,
        result_id: Optional[UUID] = None,
        simulation_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """List generated visualizations."""
        # Placeholder - would query visualization database/table
        return []

    async def delete_visualization(self, visualization_id: str) -> bool:
        """Delete a generated visualization."""
        # Placeholder - would delete visualization files and database record
        return True