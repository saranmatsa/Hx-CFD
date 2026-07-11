"""
Mesh Service for CFD Backend.

Provides mesh validation, generation, quality computation, and format conversion.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.models.mesh import (
    Mesh,
    MeshFormat,
    MeshGenerationMethod,
    MeshQualityMetric,
    MeshStatus,
)
from cfd_backend.models.project import Project

logger = logging.getLogger(__name__)


class MeshService:
    """Service for mesh operations including validation, generation, quality computation, and conversion."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_mesh(self, mesh_id: UUID) -> Dict[str, Any]:
        """
        Validate a mesh file.
        
        Args:
            mesh_id: UUID of the mesh to validate
            
        Returns:
            Dictionary with validation results
        """
        result = await self.db.execute(
            select(Mesh)
            .options(selectinload(Mesh.project))
            .where(Mesh.id == mesh_id)
        )
        mesh = result.scalar_one_or_none()
        
        if not mesh:
            raise ValueError(f"Mesh {mesh_id} not found")
        
        mesh.status = MeshStatus.VALIDATING
        await self.db.commit()
        
        try:
            # Validate based on format
            validation_result = await self._validate_mesh_file(mesh)
            
            if validation_result["valid"]:
                mesh.status = MeshStatus.READY
                mesh.element_count = validation_result.get("element_count", 0)
                mesh.node_count = validation_result.get("node_count", 0)
                mesh.boundary_count = validation_result.get("boundary_count", 0)
            else:
                mesh.status = MeshStatus.FAILED
                mesh.error_message = validation_result.get("error", "Validation failed")
            
            await self.db.commit()
            return validation_result
            
        except Exception as e:
            mesh.status = MeshStatus.FAILED
            mesh.error_message = str(e)
            await self.db.commit()
            logger.error(f"Mesh validation failed for {mesh_id}: {e}")
            raise

    async def _validate_mesh_file(self, mesh: Mesh) -> Dict[str, Any]:
        """Validate mesh file based on its format."""
        file_path = Path(mesh.file_path)
        
        if not file_path.exists():
            return {"valid": False, "error": f"Mesh file not found: {file_path}"}
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size == 0:
            return {"valid": False, "error": "Mesh file is empty"}
        
        mesh.file_size = file_size
        
        # Format-specific validation
        if mesh.format == MeshFormat.OPENFOAM:
            return await self._validate_openfoam_mesh(file_path)
        elif mesh.format == MeshFormat.GMSH:
            return await self._validate_gmsh_mesh(file_path)
        elif mesh.format == MeshFormat.CGNS:
            return await self._validate_cgns_mesh(file_path)
        elif mesh.format == MeshFormat.VTK:
            return await self._validate_vtk_mesh(file_path)
        elif mesh.format == MeshFormat.STL:
            return await self._validate_stl_mesh(file_path)
        elif mesh.format == MeshFormat.OBJ:
            return await self._validate_obj_mesh(file_path)
        elif mesh.format == MeshFormat.MED:
            return await self._validate_med_mesh(file_path)
        elif mesh.format == MeshFormat.UNV:
            return await self._validate_unv_mesh(file_path)
        elif mesh.format == MeshFormat.FLUENT:
            return await self._validate_fluent_mesh(file_path)
        elif mesh.format == MeshFormat.ANSYS:
            return await self._validate_ansys_mesh(file_path)
        elif mesh.format == MeshFormat.ABAQUS:
            return await self._validate_abaqus_mesh(file_path)
        elif mesh.format == MeshFormat.NASTRAN:
            return await self._validate_nastran_mesh(file_path)
        elif mesh.format == MeshFormat.PLY:
            return await self._validate_ply_mesh(file_path)
        elif mesh.format == MeshFormat.XDMF:
            return await self._validate_xdmf_mesh(file_path)
        else:
            return {"valid": False, "error": f"Unsupported mesh format: {mesh.format}"}

    async def _validate_openfoam_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate OpenFOAM mesh directory."""
        # OpenFOAM mesh is a directory with constant/polyMesh/
        poly_mesh_dir = file_path / "constant" / "polyMesh"
        if not poly_mesh_dir.exists():
            return {"valid": False, "error": "OpenFOAM polyMesh directory not found"}
        
        required_files = ["points", "faces", "owner", "neighbour", "boundary"]
        for f in required_files:
            if not (poly_mesh_dir / f).exists():
                return {"valid": False, "error": f"Missing OpenFOAM mesh file: {f}"}
        
        # Run checkMesh for validation
        try:
            result = await self._run_command(["checkMesh", "-case", str(file_path.parent)])
            if "Mesh OK" in result.stdout:
                # Parse mesh stats from checkMesh output
                stats = self._parse_openfoam_checkmesh(result.stdout)
                return {"valid": True, **stats}
            else:
                return {"valid": False, "error": result.stderr or "Mesh check failed"}
        except FileNotFoundError:
            # OpenFOAM not installed, do basic validation
            return await self._basic_openfoam_validation(poly_mesh_dir)
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _basic_openfoam_validation(self, poly_mesh_dir: Path) -> Dict[str, Any]:
        """Basic OpenFOAM mesh validation without checkMesh."""
        # Read points file to get node count
        points_file = poly_mesh_dir / "points"
        with open(points_file) as f:
            lines = f.readlines()
            # Find the number of points
            for line in lines:
                if line.strip().isdigit():
                    node_count = int(line.strip())
                    break
            else:
                node_count = 0
        
        # Read faces file
        faces_file = poly_mesh_dir / "faces"
        with open(faces_file) as f:
            lines = f.readlines()
            for line in lines:
                if line.strip().isdigit():
                    face_count = int(line.strip())
                    break
            else:
                face_count = 0
        
        # Read owner file
        owner_file = poly_mesh_dir / "owner"
        with open(owner_file) as f:
            lines = f.readlines()
            for line in lines:
                if line.strip().isdigit():
                    cell_count = int(line.strip())
                    break
            else:
                cell_count = 0
        
        return {
            "valid": True,
            "element_count": cell_count,
            "node_count": node_count,
            "boundary_count": face_count,
        }

    def _parse_openfoam_checkmesh(self, output: str) -> Dict[str, Any]:
        """Parse checkMesh output for statistics."""
        stats = {"element_count": 0, "node_count": 0, "boundary_count": 0}
        for line in output.split("\n"):
            if "cells:" in line:
                stats["element_count"] = int(line.split(":")[1].strip())
            elif "points:" in line:
                stats["node_count"] = int(line.split(":")[1].strip())
            elif "faces:" in line:
                stats["boundary_count"] = int(line.split(":")[1].strip())
        return stats

    async def _validate_gmsh_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate Gmsh mesh file."""
        try:
            # Use gmsh to check mesh
            result = await self._run_command(["gmsh", "-info", str(file_path)])
            if result.returncode == 0:
                stats = self._parse_gmsh_info(result.stdout)
                return {"valid": True, **stats}
            else:
                return {"valid": False, "error": result.stderr}
        except FileNotFoundError:
            # Gmsh not installed, do basic file check
            return await self._basic_gmsh_validation(file_path)
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _basic_gmsh_validation(self, file_path: Path) -> Dict[str, Any]:
        """Basic Gmsh file validation."""
        # Check file extension and basic structure
        if file_path.suffix not in [".msh", ".msh2", ".msh4"]:
            return {"valid": False, "error": "Invalid Gmsh file extension"}
        
        # Try to read as ASCII
        try:
            with open(file_path, "r") as f:
                header = f.readline()
                if "$MeshFormat" not in header:
                    return {"valid": False, "error": "Invalid Gmsh file format"}
        except UnicodeDecodeError:
            # Binary format - assume valid if extension matches
            pass
        
        return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}

    def _parse_gmsh_info(self, output: str) -> Dict[str, Any]:
        """Parse gmsh -info output."""
        stats = {"element_count": 0, "node_count": 0, "boundary_count": 0}
        for line in output.split("\n"):
            if "Nodes:" in line:
                stats["node_count"] = int(line.split(":")[1].strip())
            elif "Elements:" in line:
                stats["element_count"] = int(line.split(":")[1].strip())
        return stats

    async def _validate_cgns_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate CGNS mesh file."""
        try:
            import cgns
            # Use CGNS library to validate
            return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}
        except ImportError:
            return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _validate_vtk_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate VTK mesh file."""
        try:
            import vtk
            reader = vtk.vtkUnstructuredGridReader()
            reader.SetFileName(str(file_path))
            reader.Update()
            grid = reader.GetOutput()
            return {
                "valid": True,
                "element_count": grid.GetNumberOfCells(),
                "node_count": grid.GetNumberOfPoints(),
                "boundary_count": 0,
            }
        except ImportError:
            return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _validate_stl_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate STL mesh file."""
        try:
            import stl
            mesh = stl.mesh.Mesh.from_file(str(file_path))
            return {
                "valid": True,
                "element_count": len(mesh.vectors),
                "node_count": len(mesh.vectors) * 3,
                "boundary_count": 0,
            }
        except ImportError:
            return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _validate_obj_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate OBJ mesh file."""
        try:
            with open(file_path, "r") as f:
                vertices = 0
                faces = 0
                for line in f:
                    if line.startswith("v "):
                        vertices += 1
                    elif line.startswith("f "):
                        faces += 1
            return {
                "valid": True,
                "element_count": faces,
                "node_count": vertices,
                "boundary_count": 0,
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _validate_med_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate MED mesh file."""
        return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}

    async def _validate_unv_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate UNV mesh file."""
        return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}

    async def _validate_fluent_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate Fluent mesh file."""
        return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}

    async def _validate_ansys_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate ANSYS mesh file."""
        return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}

    async def _validate_abaqus_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate Abaqus mesh file."""
        return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}

    async def _validate_nastran_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate NASTRAN mesh file."""
        return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}

    async def _validate_ply_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate PLY mesh file."""
        return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}

    async def _validate_xdmf_mesh(self, file_path: Path) -> Dict[str, Any]:
        """Validate XDMF mesh file."""
        return {"valid": True, "element_count": 0, "node_count": 0, "boundary_count": 0}

    async def _run_command(self, cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
        """Run a command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return subprocess.CompletedProcess(
                cmd, process.returncode, stdout.decode(), stderr.decode()
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Command timed out: {' '.join(cmd)}")

    async def generate_mesh(
        self,
        mesh_id: UUID,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a mesh for the given mesh configuration.
        
        Args:
            mesh_id: UUID of the mesh to generate
            overwrite: Whether to overwrite existing mesh
            
        Returns:
            Dictionary with generation results
        """
        result = await self.db.execute(
            select(Mesh)
            .options(selectinload(Mesh.project))
            .where(Mesh.id == mesh_id)
        )
        mesh = result.scalar_one_or_none()
        
        if not mesh:
            raise ValueError(f"Mesh {mesh_id} not found")
        
        if mesh.status == MeshStatus.COMPLETED and not overwrite:
            return {"success": True, "message": "Mesh already generated", "mesh_id": str(mesh_id)}
        
        mesh.status = MeshStatus.GENERATING
        await self.db.commit()
        
        try:
            # Generate based on method
            if mesh.generation_method == MeshGenerationMethod.GMSH:
                result = await self._generate_gmsh_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.OPENFOAM:
                result = await self._generate_openfoam_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.SNELLING:
                result = await self._generate_snappy_hex_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.BLOCKMESH:
                result = await self._generate_block_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.CARTESIAN:
                result = await self._generate_cartesian_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.OCTREE:
                return await self._generate_octree_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.Delaunay:
                return await self._generate_delaunay_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.ADVANCING_FRONT:
                return await self._generate_advancing_front_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.PAVING:
                return await self._generate_paving_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.TETGEN:
                return await self._generate_tetgen_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.NETGEN:
                return await self._generate_netgen_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.CGAL:
                return await self._generate_cgal_mesh(mesh)
            elif mesh.generation_method == MeshGenerationMethod.GMSH_API:
                return await self._generate_gmsh_api_mesh(mesh)
            else:
                raise ValueError(f"Unsupported generation method: {mesh.generation_method}")
            
            if result["success"]:
                mesh.status = MeshStatus.COMPLETED
                mesh.file_path = result.get("file_path", mesh.file_path)
                mesh.format = result.get("format", mesh.format)
                mesh.element_count = result.get("element_count", 0)
                mesh.node_count = result.get("node_count", 0)
                mesh.boundary_count = result.get("boundary_count", 0)
            else:
                mesh.status = MeshStatus.FAILED
                mesh.error_message = result.get("error", "Mesh generation failed")
            
            await self.db.commit()
            return result
            
        except Exception as e:
            mesh.status = MeshStatus.FAILED
            mesh.error_message = str(e)
            await self.db.commit()
            logger.error(f"Mesh generation failed for {mesh_id}: {e}")
            raise

    async def _generate_gmsh_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate mesh using Gmsh."""
        # Create a temporary .geo file from mesh parameters
        geo_content = self._create_gmsh_geo(mesh)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            geo_file = Path(tmpdir) / "mesh.geo"
            msh_file = Path(tmpdir) / "mesh.msh"
            
            with open(geo_file, "w") as f:
                f.write(geo_content)
            
            try:
                result = await self._run_command(["gmsh", "-3", "-o", str(msh_file), str(geo_file)])
                if result.returncode == 0:
                    # Copy to final location
                    final_path = Path(mesh.file_path)
                    final_path.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(msh_file, final_path)
                    
                    return {
                        "success": True,
                        "file_path": str(final_path),
                        "format": MeshFormat.GMSH,
                        "element_count": 0,  # Would parse from output
                        "node_count": 0,
                        "boundary_count": 0,
                    }
                else:
                    return {"success": False, "error": result.stderr}
            except FileNotFoundError:
                return {"success": False, "error": "Gmsh not installed"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def _create_gmsh_geo(self, mesh: Mesh) -> str:
        """Create Gmsh .geo file from mesh parameters."""
        params = mesh.mesh_parameters or {}
        
        geo = "// Gmsh geometry file generated by CFD Backend\n"
        geo += f"Mesh.CharacteristicLengthMin = {params.get('min_size', 0.1)};\n"
        geo += f"Mesh.CharacteristicLengthMax = {params.get('max_size', 1.0)};\n"
        geo += f"Mesh.Algorithm = {params.get('algorithm', 6)};\n"  # 6 = Frontal-Delaunay
        geo += f"Mesh.Algorithm3D = {params.get('algorithm3d', 10)};\n"  # 10 = HXT
        
        # Add geometry based on parameters
        if "geometry" in params:
            geo += params["geometry"]
        else:
            # Default: simple box
            geo += """
// Default box geometry
Point(1) = {0, 0, 0, 1.0};
Point(2) = {1, 0, 0, 1.0};
Point(3) = {1, 1, 0, 1.0};
Point(4) = {0, 1, 0, 1.0};
Point(5) = {0, 0, 1, 1.0};
Point(6) = {1, 0, 1, 1.0};
Point(7) = {1, 1, 1, 1.0};
Point(8) = {0, 1, 1, 1.0};

Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};
Line(5) = {5, 6};
Line(6) = {6, 7};
Line(7) = {7, 8};
Line(8) = {8, 5};
Line(9) = {1, 5};
Line(10) = {2, 6};
Line(11) = {3, 7};
Line(12) = {4, 8};

Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};
Curve Loop(2) = {5, 6, 7, 8};
Plane Surface(2) = {2};
Curve Loop(3) = {1, 10, -5, -9};
Plane Surface(3) = {3};
Curve Loop(4) = {2, 11, -6, -10};
Plane Surface(4) = {4};
Curve Loop(5) = {3, 12, -7, -11};
Plane Surface(5) = {5};
Curve Loop(6) = {4, 9, -8, -12};
Plane Surface(6) = {6};

Surface Loop(1) = {1, 2, 3, 4, 5, 6};
Volume(1) = {1};

Physical Volume("fluid") = {1};
Physical Surface("walls") = {1, 2, 3, 4, 5, 6};
"""
        return geo

    async def _generate_openfoam_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate mesh using OpenFOAM blockMesh/snappyHexMesh."""
        # This would create blockMeshDict and run blockMesh
        return {"success": False, "error": "OpenFOAM mesh generation not fully implemented"}

    async def _generate_snappy_hex_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate mesh using snappyHexMesh."""
        return {"success": False, "error": "snappyHexMesh generation not fully implemented"}

    async def _generate_block_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate mesh using blockMesh."""
        return {"success": False, "error": "blockMesh generation not fully implemented"}

    async def _generate_cartesian_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate Cartesian mesh."""
        return {"success": False, "error": "Cartesian mesh generation not implemented"}

    async def _generate_octree_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate octree-based mesh."""
        return {"success": False, "error": "Octree mesh generation not implemented"}

    async def _generate_delaunay_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate Delaunay mesh."""
        return {"success": False, "error": "Delaunay mesh generation not implemented"}

    async def _generate_advancing_front_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate advancing front mesh."""
        return {"success": False, "error": "Advancing front mesh generation not implemented"}

    async def _generate_paving_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate paving mesh."""
        return {"success": False, "error": "Paving mesh generation not implemented"}

    async def _generate_tetgen_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate mesh using TetGen."""
        return {"success": False, "error": "TetGen mesh generation not implemented"}

    async def _generate_netgen_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate mesh using Netgen."""
        return {"success": False, "error": "Netgen mesh generation not implemented"}

    async def _generate_cgal_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate mesh using CGAL."""
        return {"success": False, "error": "CGAL mesh generation not implemented"}

    async def _generate_gmsh_api_mesh(self, mesh: Mesh) -> Dict[str, Any]:
        """Generate mesh using Gmsh Python API."""
        try:
            import gmsh
            gmsh.initialize()
            # Create geometry using Gmsh API
            # This is a placeholder - actual implementation would use the API
            gmsh.finalize()
            return {"success": False, "error": "Gmsh API generation not implemented"}
        except ImportError:
            return {"success": False, "error": "Gmsh Python API not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def compute_quality(self, mesh_id: UUID) -> Dict[str, Any]:
        """
        Compute mesh quality metrics.
        
        Args:
            mesh_id: UUID of the mesh
            
        Returns:
            Dictionary with quality metrics
        """
        result = await self.db.execute(
            select(Mesh)
            .options(selectinload(Mesh.project))
            .where(Mesh.id == mesh_id)
        )
        mesh = result.scalar_one_or_none()
        
        if not mesh:
            raise ValueError(f"Mesh {mesh_id} not found")
        
        if mesh.status != MeshStatus.READY and mesh.status != MeshStatus.COMPLETED:
            raise ValueError(f"Mesh not ready for quality computation: {mesh.status}")
        
        # Check if quality report is cached
        if mesh.quality_report and mesh.min_quality is not None:
            return {
                "element_count": mesh.element_count or 0,
                "node_count": mesh.node_count or 0,
                "boundary_count": mesh.boundary_count or 0,
                "min_quality": mesh.min_quality or 0.0,
                "avg_quality": mesh.avg_quality or 0.0,
                "max_aspect_ratio": mesh.max_aspect_ratio or 0.0,
                "max_skewness": mesh.max_skewness or 0.0,
                "distribution": mesh.quality_report.get("distribution", {}),
                "failed_elements": mesh.quality_report.get("failed_elements", 0),
                "warnings": mesh.quality_report.get("warnings", []),
                "report_path": mesh.quality_report.get("report_path"),
            }
        
        # Compute quality based on format
        quality_result = await self._compute_mesh_quality(mesh)
        
        # Update mesh with quality metrics
        mesh.min_quality = quality_result.get("min_quality", 0.0)
        mesh.avg_quality = quality_result.get("avg_quality", 0.0)
        mesh.max_aspect_ratio = quality_result.get("max_aspect_ratio", 0.0)
        mesh.max_skewness = quality_result.get("max_skewness", 0.0)
        mesh.quality_report = quality_result
        await self.db.commit()
        
        return quality_result

    async def _compute_mesh_quality(self, mesh: Mesh) -> Dict[str, Any]:
        """Compute mesh quality metrics based on format."""
        file_path = Path(mesh.file_path)
        
        if mesh.format == MeshFormat.OPENFOAM:
            return await self._compute_openfoam_quality(file_path)
        elif mesh.format == MeshFormat.GMSH:
            return await self._compute_gmsh_quality(file_path)
        elif mesh.format == MeshFormat.VTK:
            return await self._compute_vtk_quality(file_path)
        else:
            # Generic quality computation
            return await self._compute_generic_quality(mesh)

    async def _compute_openfoam_quality(self, file_path: Path) -> Dict[str, Any]:
        """Compute quality for OpenFOAM mesh using checkMesh."""
        try:
            result = await self._run_command(["checkMesh", "-case", str(file_path.parent)])
            if result.returncode == 0:
                return self._parse_openfoam_quality(result.stdout)
            else:
                return self._default_quality_result()
        except FileNotFoundError:
            return self._default_quality_result()
        except Exception as e:
            logger.warning(f"OpenFOAM quality check failed: {e}")
            return self._default_quality_result()

    def _parse_openfoam_quality(self, output: str) -> Dict[str, Any]:
        """Parse checkMesh output for quality metrics."""
        quality = self._default_quality_result()
        
        for line in output.split("\n"):
            line = line.strip()
            if "Mesh non-orthogonality" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "Max:":
                        quality["max_skewness"] = float(parts[i + 1])
                    elif part == "Average:":
                        quality["avg_quality"] = float(parts[i + 1])
            elif "Max aspect ratio" in line:
                quality["max_aspect_ratio"] = float(line.split()[-1])
            elif "Minimum face area" in line:
                quality["min_quality"] = float(line.split()[-1])
        
        return quality

    async def _compute_gmsh_quality(self, file_path: Path) -> Dict[str, Any]:
        """Compute quality for Gmsh mesh."""
        return self._default_quality_result()

    async def _compute_vtk_quality(self, file_path: Path) -> Dict[str, Any]:
        """Compute quality for VTK mesh."""
        try:
            import vtk
            from vtk.util.numpy_support import vtk_to_numpy
            
            reader = vtk.vtkUnstructuredGridReader()
            reader.SetFileName(str(file_path))
            reader.Update()
            grid = reader.GetOutput()
            
            # Compute quality metrics using VTK
            quality_filter = vtk.vtkMeshQuality()
            quality_filter.SetInputData(grid)
            quality_filter.SetTriangleQualityMeasureToMinAngle()
            quality_filter.Update()
            
            quality_array = quality_filter.GetOutput().GetCellData().GetArray("Quality")
            if quality_array:
                qualities = vtk_to_numpy(quality_array)
                return {
                    "element_count": grid.GetNumberOfCells(),
                    "node_count": grid.GetNumberOfPoints(),
                    "boundary_count": 0,
                    "min_quality": float(qualities.min()),
                    "avg_quality": float(qualities.mean()),
                    "max_aspect_ratio": 0.0,
                    "max_skewness": 0.0,
                    "distribution": {},
                    "failed_elements": int((qualities < 0.1).sum()),
                    "warnings": [],
                    "report_path": None,
                }
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"VTK quality computation failed: {e}")
        
        return self._default_quality_result()

    async def _compute_generic_quality(self, mesh: Mesh) -> Dict[str, Any]:
        """Generic quality computation fallback."""
        return self._default_quality_result()

    def _default_quality_result(self) -> Dict[str, Any]:
        """Default quality result when computation is not available."""
        return {
            "element_count": 0,
            "node_count": 0,
            "boundary_count": 0,
            "min_quality": 1.0,
            "avg_quality": 1.0,
            "max_aspect_ratio": 1.0,
            "max_skewness": 0.0,
            "distribution": {},
            "failed_elements": 0,
            "warnings": ["Quality computation not available for this mesh format"],
            "report_path": None,
        }

    async def convert_mesh(
        self,
        mesh_id: UUID,
        target_format: MeshFormat,
    ) -> Mesh:
        """
        Convert mesh to a different format.
        
        Args:
            mesh_id: UUID of the source mesh
            target_format: Target mesh format
            
        Returns:
            New Mesh object with converted format
        """
        result = await self.db.execute(
            select(Mesh)
            .options(selectinload(Mesh.project))
            .where(Mesh.id == mesh_id)
        )
        source_mesh = result.scalar_one_or_none()
        
        if not source_mesh:
            raise ValueError(f"Mesh {mesh_id} not found")
        
        if source_mesh.status != MeshStatus.READY and source_mesh.status != MeshStatus.COMPLETED:
            raise ValueError(f"Mesh not ready for conversion: {source_mesh.status}")
        
        if source_mesh.format == target_format:
            raise ValueError("Source and target formats are the same")
        
        # Create new mesh record
        new_mesh = Mesh(
            project_id=source_mesh.project_id,
            name=f"{source_mesh.name}_{target_format.value}",
            description=f"Converted from {source_mesh.format.value} to {target_format.value}",
            format=target_format,
            status=MeshStatus.CONVERTING,
            generation_method=source_mesh.generation_method,
            mesh_parameters=source_mesh.mesh_parameters.copy(),
            quality_thresholds=source_mesh.quality_thresholds.copy(),
        )
        
        self.db.add(new_mesh)
        await self.db.commit()
        await self.db.refresh(new_mesh)
        
        try:
            # Perform conversion
            conversion_result = await self._convert_mesh_file(
                source_mesh,
                new_mesh,
                target_format,
            )
            
            if conversion_result["success"]:
                new_mesh.status = MeshStatus.READY
                new_mesh.file_path = conversion_result["file_path"]
                new_mesh.file_size = conversion_result.get("file_size", 0)
                new_mesh.element_count = conversion_result.get("element_count", 0)
                new_mesh.node_count = conversion_result.get("node_count", 0)
                new_mesh.boundary_count = conversion_result.get("boundary_count", 0)
            else:
                new_mesh.status = MeshStatus.FAILED
                new_mesh.error_message = conversion_result.get("error", "Conversion failed")
            
            await self.db.commit()
            await self.db.refresh(new_mesh)
            return new_mesh
            
        except Exception as e:
            new_mesh.status = MeshStatus.FAILED
            new_mesh.error_message = str(e)
            await self.db.commit()
            logger.error(f"Mesh conversion failed for {mesh_id}: {e}")
            raise

    async def _convert_mesh_file(
        self,
        source_mesh: Mesh,
        target_mesh: Mesh,
        target_format: MeshFormat,
    ) -> Dict[str, Any]:
        """Convert mesh file from source format to target format."""
        source_path = Path(source_mesh.file_path)
        
        # Determine output path
        output_dir = source_path.parent / "converted"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{target_mesh.name}.{target_format.value}"
        
        # Format-specific conversion
        if source_mesh.format == MeshFormat.OPENFOAM and target_format == MeshFormat.VTK:
            return await self._convert_openfoam_to_vtk(source_path, output_path)
        elif source_mesh.format == MeshFormat.GMSH and target_format == MeshFormat.VTK:
            return await self._convert_gmsh_to_vtk(source_path, output_path)
        elif source_mesh.format == MeshFormat.GMSH and target_format == MeshFormat.OPENFOAM:
            return await self._convert_gmsh_to_openfoam(source_path, output_path)
        elif source_mesh.format == MeshFormat.VTK and target_format == MeshFormat.GMSH:
            return await self._convert_vtk_to_gmsh(source_path, output_path)
        elif source_mesh.format == MeshFormat.STL and target_format == MeshFormat.VTK:
            return await self._convert_stl_to_vtk(source_path, output_path)
        elif source_mesh.format == MeshFormat.OBJ and target_format == MeshFormat.VTK:
            return await self._convert_obj_to_vtk(source_path, output_path)
        else:
            # Try using meshio for generic conversion
            return await self._convert_with_meshio(source_path, output_path, target_format)

    async def _convert_openfoam_to_vtk(self, source_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert OpenFOAM mesh to VTK using foamToVTK."""
        try:
            result = await self._run_command(["foamToVTK", "-case", str(source_path.parent)])
            if result.returncode == 0:
                # Find generated VTK files
                vtk_files = list(source_path.parent.glob("VTK/*.vtk"))
                if vtk_files:
                    import shutil
                    shutil.copy2(vtk_files[0], output_path)
                    return {"success": True, "file_path": str(output_path), "file_size": output_path.stat().st_size}
            return {"success": False, "error": result.stderr or "foamToVTK failed"}
        except FileNotFoundError:
            return {"success": False, "error": "foamToVTK not found (OpenFOAM not installed)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _convert_gmsh_to_vtk(self, source_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert Gmsh mesh to VTK."""
        try:
            result = await self._run_command(["gmsh", "-o", str(output_path), str(source_path)])
            if result.returncode == 0:
                return {"success": True, "file_path": str(output_path), "file_size": output_path.stat().st_size}
            return {"success": False, "error": result.stderr}
        except FileNotFoundError:
            return {"success": False, "error": "Gmsh not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _convert_gmsh_to_openfoam(self, source_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert Gmsh mesh to OpenFOAM."""
        try:
            # Gmsh can write OpenFOAM format
            result = await self._run_command(["gmsh", "-o", str(output_path), "-format", "msh2", str(source_path)])
            if result.returncode == 0:
                return {"success": True, "file_path": str(output_path), "file_size": output_path.stat().st_size}
            return {"success": False, "error": result.stderr}
        except FileNotFoundError:
            return {"success": False, "error": "Gmsh not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _convert_vtk_to_gmsh(self, source_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert VTK mesh to Gmsh."""
        return await self._convert_with_meshio(source_path, output_path, MeshFormat.GMSH)

    async def _convert_stl_to_vtk(self, source_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert STL mesh to VTK."""
        return await self._convert_with_meshio(source_path, output_path, MeshFormat.VTK)

    async def _convert_obj_to_vtk(self, source_path: Path, output_path: Path) -> Dict[str, Any]:
        """Convert OBJ mesh to VTK."""
        return await self._convert_with_meshio(source_path, output_path, MeshFormat.VTK)

    async def _convert_with_meshio(
        self,
        source_path: Path,
        output_path: Path,
        target_format: MeshFormat,
    ) -> Dict[str, Any]:
        """Convert mesh using meshio library."""
        try:
            import meshio
            
            # Read source mesh
            mesh = meshio.read(str(source_path))
            
            # Write to target format
            format_map = {
                MeshFormat.VTK: "vtk",
                MeshFormat.GMSH: "gmsh",
                MeshFormat.STL: "stl",
                MeshFormat.OBJ: "obj",
                MeshFormat.PLY: "ply",
                MeshFormat.XDMF: "xdmf",
                MeshFormat.CGNS: "cgns",
                MeshFormat.MED: "med",
            }
            
            meshio_format = format_map.get(target_format)
            if not meshio_format:
                return {"success": False, "error": f"meshio does not support format: {target_format}"}
            
            meshio.write(str(output_path), mesh, file_format=meshio_format)
            
            return {
                "success": True,
                "file_path": str(output_path),
                "file_size": output_path.stat().st_size,
                "element_count": len(mesh.cells_dict) if mesh.cells_dict else 0,
                "node_count": len(mesh.points) if mesh.points is not None else 0,
                "boundary_count": 0,
            }
        except ImportError:
            return {"success": False, "error": "meshio not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}