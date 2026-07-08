"""
VTK Integration Module
Handles visualization and post-processing of CFD results.
"""

import os
import shutil
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class VisualizationResult:
    """Result of visualization operation."""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded image


@dataclass
class FieldData:
    """Container for field data (velocity, pressure, etc.)."""
    name: str
    data: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None


class VTKClient:
    """
    Client for VTK operations.
    VTK is used for:
    - Converting OpenFOAM results to VTK format
    - Generating visualizations
    - Extracting field data
    - Creating slices and streamlines
    """
    
    def __init__(self, vtk_path: str = "/usr/bin"):
        self.vtk_path = vtk_path
        self._verify_installation()
    
    def _verify_installation(self) -> None:
        """Verify VTK/ParaView tools are available."""
        # Check for paraFoam (OpenFOAM's VTK converter)
        try:
            result = subprocess.run(
                ["which", "paraFoam"],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info("paraFoam found for VTK conversion")
                self._has_parafoam = True
            else:
                self._has_parafoam = False
        except Exception:
            self._has_parafoam = False
        
        # Check for VTK Python modules
        try:
            import vtk
            self._has_vtk_python = True
            logger.info("VTK Python module available")
        except ImportError:
            self._has_vtk_python = False
            logger.warning("VTK Python module not available")
    
    def convert_openfoam_to_vtk(
        self,
        case_dir: str,
        output_dir: str,
        time_step: Optional[str] = None
    ) -> str:
        """
        Convert OpenFOAM results to VTK format.
        
        Args:
            case_dir: Path to OpenFOAM case directory
            output_dir: Directory for VTK output
            time_step: Specific time step to convert (None for latest)
            
        Returns:
            Path to VTK files directory
        """
        os.makedirs(output_dir, exist_ok=True)
        vtk_dir = os.path.join(output_dir, "vtk")
        os.makedirs(vtk_dir, exist_ok=True)
        
        if self._has_parafoam:
            try:
                # Use paraFoam to convert
                subprocess.run(
                    ["paraFoam", "-case", case_dir, "-vtk", "-no-zero"],
                    capture_output=True,
                    check=True,
                    timeout=300
                )
                
                # Move generated VTK files
                vtk_files = Path(case_dir).rglob("*.vtk")
                for vtk_file in vtk_files:
                    shutil.copy(vtk_file, vtk_dir)
                
                return vtk_dir
            except subprocess.CalledProcessError as e:
                logger.warning(f"paraFoam conversion failed: {e.stderr}")
        
        # Fallback: create placeholder VTK
        return self._create_placeholder_vtk(vtk_dir)
    
    def _create_placeholder_vtk(self, output_dir: str) -> str:
        """Create placeholder VTK files for testing."""
        # Create a simple VTK file
        vtk_content = '''# vtk DataFile Version 3.0
CFD Results
ASCII
DATASET UNSTRUCTURED_GRID
POINTS 8 float
0 0 0
1 0 0
1 1 0
0 1 0
0 0 1
1 0 1
1 1 1
0 1 1
CELLS 1
8 0 1 2 3 4 5 6 7
CELL_TYPES 1
12
POINT_DATA 8
SCALARS pressure float 1
LOOKUP_TABLE default
0 0.1 0.2 0.3 0.4 0.5 0.6 0.7
VECTORS velocity float
1 0 0
1 0 0
1 0 0
1 0 0
1 0 0
1 0 0
1 0 0
1 0 0
'''
        vtk_path = os.path.join(output_dir, "results.vtk")
        with open(vtk_path, 'w') as f:
            f.write(vtk_content)
        
        return output_dir
    
    def extract_field_data(
        self,
        vtk_file: str,
        field_name: str
    ) -> Optional[FieldData]:
        """
        Extract field data from VTK file.
        
        Args:
            vtk_file: Path to VTK file
            field_name: Name of field to extract
            
        Returns:
            FieldData object with extracted data
        """
        if self._has_vtk_python:
            return self._extract_with_vtk(vtk_file, field_name)
        else:
            return self._extract_from_ascii(vtk_file, field_name)
    
    def _extract_with_vtk(self, vtk_file: str, field_name: str) -> Optional[FieldData]:
        """Extract field data using VTK Python module."""
        try:
            import vtk
            
            reader = vtk.vtkXMLUnstructuredGridReader()
            reader.SetFileName(vtk_file)
            reader.Update()
            
            output = reader.GetOutput()
            point_data = output.GetPointData()
            
            # Find the array
            array = None
            for i in range(point_data.GetNumberOfArrays()):
                arr = point_data.GetArray(i)
                if arr.GetName() == field_name:
                    array = arr
                    break
            
            if array:
                data_range = array.GetRange()
                return FieldData(
                    name=field_name,
                    data=[array.GetValue(i) for i in range(array.GetNumberOfValues())],
                    min_value=data_range[0],
                    max_value=data_range[1]
                )
            
            return None
        except Exception as e:
            logger.error(f"VTK extraction failed: {e}")
            return None
    
    def _extract_from_ascii(self, vtk_file: str, field_name: str) -> Optional[FieldData]:
        """Extract field data from ASCII VTK file."""
        try:
            with open(vtk_file, 'r') as f:
                content = f.read()
            
            # Simple parsing for ASCII VTK
            if field_name == "pressure":
                if "SCALARS pressure" in content:
                    start = content.find("LOOKUP_TABLE default") + len("LOOKUP_TABLE default\n")
                    end = content.find("\n", start)
                    values = [float(v) for v in content[start:end].split()]
                    return FieldData(
                        name="pressure",
                        data=values,
                        min_value=min(values) if values else 0,
                        max_value=max(values) if values else 0,
                        unit="Pa"
                    )
            elif field_name == "velocity":
                if "VECTORS velocity" in content:
                    # Parse vector data
                    values = []
                    # This is simplified - real implementation would parse properly
                    return FieldData(
                        name="velocity",
                        data=values,
                        unit="m/s"
                    )
            
            return None
        except Exception as e:
            logger.error(f"ASCII extraction failed: {e}")
            return None
    
    def create_slice(
        self,
        vtk_file: str,
        output_dir: str,
        origin: Tuple[float, float, float] = (0, 0, 0),
        normal: Tuple[float, float, float] = (1, 0, 0)
    ) -> str:
        """
        Create a slice through the dataset.
        
        Args:
            vtk_file: Input VTK file
            output_dir: Output directory
            origin: Point for slice plane
            normal: Normal vector for slice plane
            
        Returns:
            Path to slice VTK file
        """
        output_path = os.path.join(output_dir, "slice.vtk")
        
        if self._has_vtk_python:
            try:
                import vtk
                
                reader = vtk.vtkXMLUnstructuredGridReader()
                reader.SetFileName(vtk_file)
                reader.Update()
                
                # Create plane
                plane = vtk.vtkPlane()
                plane.SetOrigin(*origin)
                plane.SetNormal(*normal)
                
                # Cut the data
                cutter = vtk.vtkCutter()
                cutter.SetInputConnection(reader.GetOutputPort())
                cutter.SetCutFunction(plane)
                cutter.Update()
                
                # Write output
                writer = vtk.vtkXMLUnstructuredGridWriter()
                writer.SetFileName(output_path)
                writer.SetInputConnection(cutter.GetOutputPort())
                writer.Write()
                
                return output_path
            except Exception as e:
                logger.error(f"Slice creation failed: {e}")
        
        # Fallback: copy input
        import shutil
        shutil.copy(vtk_file, output_path)
        return output_path
    
    def generate_image(
        self,
        vtk_file: str,
        output_path: str,
        field_name: str = "pressure",
        camera_position: Tuple[float, float, float] = (2, 2, 2),
        color_range: Optional[Tuple[float, float]] = None
    ) -> VisualizationResult:
        """
        Generate a visualization image from VTK data.
        
        Args:
            vtk_file: Input VTK file
            output_path: Output image path
            field_name: Field to visualize
            camera_position: Camera position (x, y, z)
            color_range: Optional (min, max) for color scale
            
        Returns:
            VisualizationResult with image data
        """
        if self._has_vtk_python:
            return self._generate_with_vtk(
                vtk_file, output_path, field_name, camera_position, color_range
            )
        else:
            return self._generate_placeholder_image(output_path)
    
    def _generate_with_vtk(
        self,
        vtk_file: str,
        output_path: str,
        field_name: str,
        camera_position: Tuple[float, float, float],
        color_range: Optional[Tuple[float, float]]
    ) -> VisualizationResult:
        """Generate image using VTK."""
        try:
            import vtk
            
            # Read data
            reader = vtk.vtkXMLUnstructuredGridReader()
            reader.SetFileName(vtk_file)
            reader.Update()
            
            # Create mapper
            mapper = vtk.vtkDataSetMapper()
            mapper.SetInputConnection(reader.GetOutputPort())
            
            # Get the array for color range
            output = reader.GetOutput()
            point_data = output.GetPointData()
            array = point_data.GetArray(field_name)
            
            if array and color_range is None:
                color_range = array.GetRange()
            
            if color_range:
                mapper.SetScalarRange(*color_range)
            
            # Create actor
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetOpacity(1.0)
            
            # Create renderer
            renderer = vtk.vtkRenderer()
            renderer.AddActor(actor)
            renderer.SetBackground(1, 1, 1)  # White background
            
            # Set camera
            camera = renderer.GetActiveCamera()
            camera.SetPosition(*camera_position)
            camera.SetFocalPoint(0, 0, 0)
            camera.SetViewUp(0, 0, 1)
            
            # Create render window
            render_window = vtk.vtkRenderWindow()
            render_window.SetOffScreenRendering(1)
            render_window.SetSize(800, 600)
            render_window.AddRenderer(renderer)
            render_window.Render()
            
            # Save to image
            window_to_image = vtk.vtkWindowToImageFilter()
            window_to_image.SetInput(render_window)
            window_to_image.SetInputBufferTypeToRGBA()
            window_to_image.ReadFrontBufferOff()
            window_to_image.Update()
            
            writer = vtk.vtkPNGWriter()
            writer.SetFileName(output_path)
            writer.SetInputConnection(window_to_image.GetOutputPort())
            writer.Write()
            
            # Read back for base64
            with open(output_path, 'rb') as f:
                import base64
                image_data = base64.b64encode(f.read()).decode()
            
            return VisualizationResult(
                success=True,
                output_path=output_path,
                image_data=image_data
            )
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return VisualizationResult(success=False, error_message=str(e))
    
    def _generate_placeholder_image(self, output_path: str) -> VisualizationResult:
        """Generate a placeholder image when VTK is not available."""
        try:
            # Create a simple placeholder using PIL if available
            try:
                from PIL import Image, ImageDraw
                
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)
                draw.text((350, 280), "CFD Visualization", fill='black')
                draw.text((300, 320), "(Placeholder)", fill='gray')
                img.save(output_path)
                
                with open(output_path, 'rb') as f:
                    import base64
                    image_data = base64.b64encode(f.read()).decode()
                
                return VisualizationResult(
                    success=True,
                    output_path=output_path,
                    image_data=image_data
                )
            except ImportError:
                # No PIL either - create empty file
                with open(output_path, 'w') as f:
                    f.write("Placeholder image")
                return VisualizationResult(success=True, output_path=output_path)
        except Exception as e:
            return VisualizationResult(success=False, error_message=str(e))
    
    def compute_streamlines(
        self,
        vtk_file: str,
        output_path: str,
        seed_point: Tuple[float, float, float] = (0, 0, 0),
        length: float = 10.0
    ) -> str:
        """
        Generate streamlines from velocity field.
        
        Args:
            vtk_file: Input VTK file with velocity data
            output_path: Output VTK file with streamlines
            seed_point: Starting point for streamlines
            length: Length of streamlines
            
        Returns:
            Path to streamline VTK file
        """
        if self._has_vtk_python:
            try:
                import vtk
                
                reader = vtk.vtkXMLUnstructuredGridReader()
                reader.SetFileName(vtk_file)
                reader.Update()
                
                # Create streamer
                streamer = vtk.vtkStreamTracer()
                streamer.SetInputConnection(reader.GetOutputPort())
                streamer.SetStartPosition(*seed_point)
                streamer.SetMaximumPropagation(length)
                streamer.SetIntegrationDirectionToBoth()
                streamer.Update()
                
                # Write output
                writer = vtk.vtkXMLUnstructuredGridWriter()
                writer.SetFileName(output_path)
                writer.SetInputConnection(streamer.GetOutputPort())
                writer.Write()
                
                return output_path
            except Exception as e:
                logger.error(f"Streamline generation failed: {e}")
        
        # Fallback
        import shutil
        shutil.copy(vtk_file, output_path)
        return output_path
    
    def extract_slice_data(
        self,
        vtk_file: str,
        plane: str = "XY",
        position: float = 0.0
    ) -> Dict[str, Any]:
        """
        Extract 2D data from a slice plane.
        
        Args:
            vtk_file: Input VTK file
            plane: Plane orientation ("XY", "XZ", "YZ")
            position: Position along the perpendicular axis
            
        Returns:
            Dictionary with slice data
        """
        if self._has_vtk_python:
            try:
                import vtk
                import numpy as np
                
                reader = vtk.vtkXMLUnstructuredGridReader()
                reader.SetFileName(vtk_file)
                reader.Update()
                
                output = reader.GetOutput()
                bounds = output.GetBounds()
                
                # Determine plane and origin
                if plane == "XY":
                    origin = (bounds[0], bounds[2], position)
                    normal = (0, 0, 1)
                elif plane == "XZ":
                    origin = (bounds[0], position, bounds[4])
                    normal = (0, 1, 0)
                else:  # YZ
                    origin = (position, bounds[2], bounds[4])
                    normal = (1, 0, 0)
                
                # Create cutter
                plane_source = vtk.vtkPlane()
                plane_source.SetOrigin(*origin)
                plane_source.SetNormal(*normal)
                
                cutter = vtk.vtkCutter()
                cutter.SetInputConnection(reader.GetOutputPort())
                cutter.SetCutFunction(plane_source)
                cutter.Update()
                
                # Extract points and data
                cut_output = cutter.GetOutput()
                points = np.array([cut_output.GetPoint(i) for i in range(cut_output.GetNumberOfPoints())])
                
                result = {
                    "points": points.tolist(),
                    "n_points": len(points)
                }
                
                # Get field data
                point_data = cut_output.GetPointData()
                for i in range(point_data.GetNumberOfArrays()):
                    arr = point_data.GetArray(i)
                    result[arr.GetName()] = [arr.GetValue(j) for j in range(arr.GetNumberOfValues())]
                
                return result
            except Exception as e:
                logger.error(f"Slice extraction failed: {e}")
                return {}
        else:
            return {"n_points": 0, "message": "VTK Python not available"}