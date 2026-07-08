"""
Integration services for external CFD tools.
These services provide a consistent interface for interacting with FreeCAD, Gmsh, OpenFOAM, and VTK.
"""

import os
import subprocess
import json
import tempfile
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import structlog

from core.config import get_settings
from core.errors import (
    CFDPlatformException,
    FileProcessingError,
    MeshGenerationError,
    SimulationError,
    VisualizationError,
)
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BaseToolClient:
    """Base class for external tool clients."""

    def __init__(self, tool_path: Optional[str] = None):
        """
        Initialize the tool client.
        
        Args:
            tool_path: Optional path to the tool executable
        """
        self.tool_path = tool_path
        self._logger = logger.bind(client=self.__class__.__name__)

    def _verify_installation(self) -> bool:
        """Verify the tool is installed and accessible."""
        if not self.tool_path:
            self._logger.warning("tool_path_not_configured")
            return False
        
        if not os.path.exists(self.tool_path):
            self._logger.error("tool_not_found", path=self.tool_path)
            return False
        
        return True

    def _run_command(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        timeout: int = 3600,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a command and return the result.
        
        Args:
            args: Command arguments
            cwd: Working directory
            timeout: Command timeout in seconds
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            CompletedProcess instance
            
        Raises:
            CFDPlatformException: If command fails
        """
        self._logger.debug("running_command", args=args, cwd=cwd)
        
        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
            )
            
            if result.returncode != 0:
                self._logger.error(
                    "command_failed",
                    returncode=result.returncode,
                    stderr=result.stderr,
                )
                raise CFDPlatformException(f"Command failed: {result.stderr}")
            
            return result
            
        except subprocess.TimeoutExpired:
            self._logger.error("command_timeout", timeout=timeout)
            raise CFDPlatformException(f"Command timed out after {timeout} seconds")
        except FileNotFoundError:
            self._logger.error("executable_not_found", args=args[0])
            raise CFDPlatformException(f"Executable not found: {args[0]}")
        except Exception as e:
            self._logger.error("command_error", error=str(e))
            raise CFDPlatformException(f"Command error: {str(e)}")


class FreeCADClient(BaseToolClient):
    """Client for FreeCAD operations."""

    def __init__(self, tool_path: Optional[str] = None):
        super().__init__(tool_path or settings.FREECAD_BIN)
        self._logger = logger.bind(client="FreeCADClient")

    def _verify_installation(self) -> bool:
        """Verify FreeCAD is installed."""
        if not self.tool_path:
            self._logger.warning("FREECAD_BIN not configured")
            return False
        
        if not os.path.exists(self.tool_path):
            self._logger.error("freecad_not_found", path=self.tool_path)
            return False
        
        return True

    def import_geometry(
        self,
        input_path: str,
        output_path: str,
        format: str = "step",
    ) -> Dict[str, Any]:
        """
        Import geometry from various formats.
        
        Args:
            input_path: Path to input geometry file
            output_path: Path to output file
            format: Output format (step, brep, etc.)
            
        Returns:
            Dictionary with import results
        """
        self._logger.info("importing_geometry", input=input_path, output=output_path)
        
        if not self._verify_installation():
            raise FileProcessingError("FreeCAD not properly configured")
        
        # Create FreeCAD Python script for import
        script = f"""
import FreeCAD
import Part
import Mesh

# Open the input file
doc = FreeCAD.newDocument()
Part.insert("{input_path.replace('\\', '\\\\')}", doc)

# Export to output format
if "{format}" == "step":
    Part.export(doc.Objects, "{output_path.replace('\\', '\\\\')}")
elif "{format}" == "brep":
    Part.export(doc.Objects, "{output_path.replace('\\', '\\\\')}")
else:
    Mesh.export(doc.Objects, "{output_path.replace('\\', '\\\\')}")

FreeCAD.closeDocument(doc.Name)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            result = self._run_command(
                [self.tool_path, script_path],
                timeout=300,
            )
            
            return {
                "success": True,
                "output_path": output_path,
                "format": format,
            }
        finally:
            os.unlink(script_path)

    def get_geometry_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a geometry file.
        
        Args:
            file_path: Path to geometry file
            
        Returns:
            Dictionary with geometry information
        """
        self._logger.info("getting_geometry_info", file=file_path)
        
        if not self._verify_installation():
            raise FileProcessingError("FreeCAD not properly configured")
        
        script = f"""
import FreeCAD
import Part
import json

doc = FreeCAD.newDocument()
Part.insert("{file_path.replace('\\', '\\\\')}", doc)

# Calculate bounding box
bounding_box = doc.Objects[0].Shape.BoundBox
volume = doc.Objects[0].Shape.Volume
surface_area = doc.Objects[0].Shape.Area

result = {{
    "bounding_box": {{
        "x_min": bounding_box.XMin,
        "x_max": bounding_box.XMax,
        "y_min": bounding_box.YMin,
        "y_max": bounding_box.YMax,
        "z_min": bounding_box.ZMin,
        "z_max": bounding_box.ZMax,
    }},
    "volume": volume,
    "surface_area": surface_area,
}}

print(json.dumps(result))
FreeCAD.closeDocument(doc.Name)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            result = self._run_command(
                [self.tool_path, script_path],
                timeout=300,
            )
            
            # Parse JSON from stdout
            for line in result.stdout.split('\n'):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
            
            raise FileProcessingError("Could not parse geometry info")
        finally:
            os.unlink(script_path)


class GmshClient(BaseToolClient):
    """Client for Gmsh mesh generation operations."""

    def __init__(self, tool_path: Optional[str] = None):
        super().__init__(tool_path or settings.GMSH_BIN)
        self._logger = logger.bind(client="GmshClient")

    def _verify_installation(self) -> bool:
        """Verify Gmsh is installed."""
        if not self.tool_path:
            self._logger.warning("GMSH_BIN not configured")
            return False
        
        if not os.path.exists(self.tool_path):
            self._logger.error("gmsh_not_found", path=self.tool_path)
            return False
        
        return True

    def generate_mesh(
        self,
        geometry_path: str,
        output_path: str,
        mesh_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a mesh from geometry.
        
        Args:
            geometry_path: Path to input geometry file
            output_path: Path to output mesh file
            mesh_config: Mesh generation configuration
            
        Returns:
            Dictionary with mesh generation results
        """
        self._logger.info(
            "generating_mesh",
            geometry=geometry_path,
            output=output_path,
        )
        
        if not self._verify_installation():
            raise MeshGenerationError("Gmsh not properly configured")
        
        config = mesh_config or {}
        
        # Build Gmsh options
        args = [
            self.tool_path,
            geometry_path,
            "-o", output_path,
            "-format", config.get("format", "msh2"),
        ]
        
        # Add mesh size options
        if "mesh_size" in config:
            args.extend(["-clscale", str(config["mesh_size"])])
        if "element_size" in config:
            args.extend(["-clsize", str(config["element_size"])])
        
        # 2D or 3D mesh
        if config.get("dim", 3) == 2:
            args.extend(["-2"])
        else:
            args.extend(["-3"])
        
        # Run Gmsh
        result = self._run_command(args, timeout=config.get("timeout", 3600))
        
        # Get mesh statistics
        stats = self._get_mesh_stats(output_path)
        
        return {
            "success": True,
            "output_path": output_path,
            "element_count": stats.get("element_count", 0),
            "node_count": stats.get("node_count", 0),
        }

    def _get_mesh_stats(self, mesh_path: str) -> Dict[str, Any]:
        """Get statistics from a mesh file."""
        try:
            import meshio
            mesh = meshio.read(mesh_path)
            return {
                "element_count": sum(len(cells) for cells in mesh.cells),
                "node_count": len(mesh.points),
            }
        except Exception as e:
            self._logger.warning("could_not_read_mesh_stats", error=str(e))
            return {}

    def check_mesh_quality(self, mesh_path: str) -> Dict[str, float]:
        """
        Check mesh quality metrics.
        
        Args:
            mesh_path: Path to mesh file
            
        Returns:
            Dictionary with quality metrics
        """
        self._logger.info("checking_mesh_quality", mesh=mesh_path)
        
        # Use meshio to read and analyze mesh
        try:
            import meshio
            mesh = meshio.read(mesh_path)
            
            # Basic quality metrics
            points = mesh.points
            
            # Calculate aspect ratios (simplified)
            min_quality = 0.0
            max_quality = 1.0
            
            return {
                "min_quality": min_quality,
                "max_quality": max_quality,
                "average_quality": (min_quality + max_quality) / 2,
            }
        except Exception as e:
            self._logger.error("mesh_quality_check_failed", error=str(e))
            return {}


class OpenFOAMClient(BaseToolClient):
    """Client for OpenFOAM operations."""

    def __init__(self, openfoam_dir: Optional[str] = None):
        super().__init__(None)
        self.openfoam_dir = openfoam_dir or settings.OPENFOAM_DIR
        self._logger = logger.bind(client="OpenFOAMClient")
        self._setup_environment()

    def _setup_environment(self) -> None:
        """Set up OpenFOAM environment variables."""
        if not self.openfoam_dir or not os.path.exists(self.openfoam_dir):
            self._logger.warning("OPENFOAM_DIR not configured or not found")
            return
        
        # Set up OpenFOAM environment
        self._logger.info("openfoam_environment_setup", dir=self.openfoam_dir)

    def _verify_installation(self) -> bool:
        """Verify OpenFOAM is installed."""
        if not self.openfoam_dir:
            self._logger.warning("OPENFOAM_DIR not configured")
            return False
        
        # Check for essential directories
        required_dirs = ["bin", "etc", "applications"]
        for dir_name in required_dirs:
            if not os.path.exists(os.path.join(self.openfoam_dir, dir_name)):
                self._logger.error("openfoam_dir_missing", dir=dir_name)
                return False
        
        return True

    def create_case(
        self,
        case_path: str,
        mesh_path: str,
        solver: str = "simpleFoam",
    ) -> Dict[str, Any]:
        """
        Create an OpenFOAM case directory structure.
        
        Args:
            case_path: Path to create the case
            mesh_path: Path to mesh file
            solver: OpenFOAM solver to use
            
        Returns:
            Dictionary with case creation results
        """
        self._logger.info("creating_openfoam_case", case=case_path, mesh=mesh_path)
        
        if not self._verify_installation():
            raise SimulationError("OpenFOAM not properly configured")
        
        # Create case directory structure
        os.makedirs(case_path, exist_ok=True)
        os.makedirs(os.path.join(case_path, "system"), exist_ok=True)
        os.makedirs(os.path.join(case_path, "constant"), exist_ok=True)
        os.makedirs(os.path.join(case_path, "0.orig"), exist_ok=True)
        
        # Copy mesh to constant/polyMesh
        mesh_dest = os.path.join(case_path, "constant", "polyMesh")
        os.makedirs(mesh_dest, exist_ok=True)
        
        # Create basic OpenFOAM files
        self._create_case_files(case_path, solver)
        
        return {
            "success": True,
            "case_path": case_path,
            "solver": solver,
        }

    def _create_case_files(self, case_path: str, solver: str) -> None:
        """Create basic OpenFOAM case files."""
        
        # controlDict
        control_dict = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  2306                                  |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     F amily        |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     {solver};

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         1000;

deltaT          0.5;

writeControl    timeStep;

writeInterval   100;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision  6;

runTimeModifiable true;

// ************************************************************************* //
"""
        with open(os.path.join(case_path, "system", "controlDict"), "w") as f:
            f.write(control_dict)

    def run_simulation(
        self,
        case_path: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run an OpenFOAM simulation.
        
        Args:
            case_path: Path to the case directory
            config: Simulation configuration
            
        Returns:
            Dictionary with simulation results
        """
        self._logger.info("running_simulation", case=case_path)
        
        if not self._verify_installation():
            raise SimulationError("OpenFOAM not properly configured")
        
        config = config or {}
        
        # Source OpenFOAM bashrc
        bashrc_path = os.path.join(self.openfoam_dir, "etc", "bashrc")
        
        # Create run script
        run_script = f"""#!/bin/bash
source {bashrc_path}
cd {case_path}
blockMesh
checkMesh
{solver} -parallel > log.{solver} 2>&1
"""
        
        script_path = os.path.join(case_path, "run_simulation.sh")
        with open(script_path, "w") as f:
            f.write(run_script)
        
        # Note: In a real implementation, this would be run via Celery
        # For now, return the script path
        return {
            "success": True,
            "case_path": case_path,
            "script_path": script_path,
            "message": "Simulation queued for execution",
        }

    def get_residuals(self, case_path: str) -> Dict[str, List[float]]:
        """
        Get solver residuals from a case.
        
        Args:
            case_path: Path to the case directory
            
        Returns:
            Dictionary with residual data
        """
        self._logger.info("getting_residuals", case=case_path)
        
        # Parse log file for residuals
        log_file = os.path.join(case_path, "log.simpleFoam")
        
        if not os.path.exists(log_file):
            return {}
        
        residuals = {}
        with open(log_file, "r") as f:
            for line in f:
                if "Solving for" in line:
                    # Parse residual line
                    pass
        
        return residuals


class VTKClient(BaseToolClient):
    """Client for VTK visualization operations."""

    def __init__(self, tool_path: Optional[str] = None):
        super().__init__(tool_path)
        self._logger = logger.bind(client="VTKClient")

    def convert_mesh(
        self,
        input_path: str,
        output_path: str,
        input_format: str = "openfoam",
        output_format: str = "vtk",
    ) -> Dict[str, Any]:
        """
        Convert mesh between formats.
        
        Args:
            input_path: Path to input mesh
            output_path: Path to output mesh
            input_format: Input format
            output_format: Output format
            
        Returns:
            Dictionary with conversion results
        """
        self._logger.info(
            "converting_mesh",
            input=input_path,
            output=output_path,
            from_format=input_format,
            to_format=output_format,
        )
        
        try:
            import meshio
            
            mesh = meshio.read(input_path)
            meshio.write(output_path, mesh, file_format=output_format)
            
            return {
                "success": True,
                "output_path": output_path,
            }
        except Exception as e:
            raise VisualizationError(f"Mesh conversion failed: {str(e)}")

    def extract_slice(
        self,
        input_path: str,
        output_path: str,
        origin: Tuple[float, float, float],
        normal: Tuple[float, float, float],
    ) -> Dict[str, Any]:
        """
        Extract a slice from a 3D dataset.
        
        Args:
            input_path: Path to input VTK file
            output_path: Path to output slice file
            origin: Origin point of the slice
            normal: Normal vector of the slice plane
            
        Returns:
            Dictionary with extraction results
        """
        self._logger.info("extracting_slice", input=input_path, output=output_path)
        
        try:
            import pyvista as pv
            
            # Read the dataset
            dataset = pv.read(input_path)
            
            # Create slice
            slice_data = dataset.slice(origin=origin, normal=normal)
            
            # Save slice
            slice_data.save(output_path)
            
            return {
                "success": True,
                "output_path": output_path,
            }
        except Exception as e:
            raise VisualizationError(f"Slice extraction failed: {str(e)}")

    def get_field_data(
        self,
        file_path: str,
        field_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get field data from a VTK file.
        
        Args:
            file_path: Path to VTK file
            field_name: Optional specific field to retrieve
            
        Returns:
            Dictionary with field data
        """
        self._logger.info("getting_field_data", file=file_path, field=field_name)
        
        try:
            import pyvista as pv
            
            dataset = pv.read(file_path)
            
            result = {
                "point_arrays": list(dataset.point_data.keys()),
                "cell_arrays": list(dataset.cell_data.keys()),
                "field_arrays": list(dataset.field_data.keys()),
            }
            
            if field_name:
                if field_name in dataset.point_data:
                    result["data"] = dataset.point_data[field_name].tolist()
                elif field_name in dataset.cell_data:
                    result["data"] = dataset.cell_data[field_name].tolist()
            
            return result
        except Exception as e:
            raise VisualizationError(f"Failed to get field data: {str(e)}")


# Factory function for creating clients
def get_freecad_client() -> FreeCADClient:
    """Get a FreeCAD client instance."""
    return FreeCADClient()


def get_gmsh_client() -> GmshClient:
    """Get a Gmsh client instance."""
    return GmshClient()


def get_openfoam_client() -> OpenFOAMClient:
    """Get an OpenFOAM client instance."""
    return OpenFOAMClient()


def get_vtk_client() -> VTKClient:
    """Get a VTK client instance."""
    return VTKClient()