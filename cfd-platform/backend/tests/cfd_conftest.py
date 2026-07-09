"""
Pytest configuration for CFD integration tests.
This conftest is specifically for CFD pipeline tests and doesn't require the full app.
"""

import pytest
import asyncio
from typing import Generator
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_freecad_client():
    """Mock FreeCAD client for testing."""
    client = MagicMock()
    client.import_step = AsyncMock(return_value={
        "success": True,
        "file_path": "/tmp/test_model.step",
        "num_faces": 100,
        "num_edges": 200,
        "volume": 1.5,
        "surface_area": 10.0
    })
    client.repair_geometry = AsyncMock(return_value={
        "success": True,
        "fixed_faces": 5,
        "fixed_edges": 10,
        "removed_duplicates": 2
    })
    client.get_geometry_info = AsyncMock(return_value={
        "num_faces": 100,
        "num_edges": 200,
        "num_solids": 1,
        "volume": 1.5,
        "surface_area": 10.0,
        "bounding_box": {
            "x_min": 0, "x_max": 1,
            "y_min": 0, "y_max": 1,
            "z_min": 0, "z_max": 1.5
        }
    })
    return client


@pytest.fixture
def mock_gmsh_client():
    """Mock Gmsh client for testing."""
    client = MagicMock()
    client.generate_mesh = AsyncMock(return_value={
        "success": True,
        "mesh_file": "/tmp/test_mesh.msh",
        "num_nodes": 5000,
        "num_elements": 10000,
        "mesh_quality": 0.95
    })
    client.convert_mesh_format = AsyncMock(return_value={
        "success": True,
        "output_file": "/tmp/test_mesh.vtu",
        "format": "vtu"
    })
    client.create_boundary_layer_mesh = AsyncMock(return_value={
        "success": True,
        "mesh_file": "/tmp/test_mesh_bl.msh",
        "num_layers": 10
    })
    return client


@pytest.fixture
def mock_openfoam_client():
    """Mock OpenFOAM client for testing."""
    client = MagicMock()
    client.create_case = AsyncMock(return_value={
        "success": True,
        "case_dir": "/tmp/test_case",
        "case_name": "test_case"
    })
    client.run_simulation = AsyncMock(return_value={
        "success": True,
        "case_dir": "/tmp/test_case",
        "elapsed_time": 100.0,
        "time_steps_completed": 100,
        "final_time": 1.0,
        "residuals": {
            "Ux": 1e-5,
            "Uy": 1e-5,
            "Uz": 1e-5,
            "p": 1e-6
        }
    })
    return client


@pytest.fixture
def mock_vtk_client():
    """Mock VTK client for testing."""
    client = MagicMock()
    client.convert_openfoam_to_vtk = AsyncMock(return_value={
        "success": True,
        "vtk_file": "/tmp/test_results.vtu",
        "num_points": 5000,
        "num_cells": 10000
    })
    client.extract_field_data = AsyncMock(return_value={
        "success": True,
        "field_name": "velocity",
        "min_value": 0.0,
        "max_value": 10.0,
        "average_value": 5.0
    })
    client.generate_image = AsyncMock(return_value={
        "success": True,
        "image_file": "/tmp/test_image.png",
        "resolution": [1920, 1080]
    })
    client.create_slice = AsyncMock(return_value={
        "success": True,
        "slice_file": "/tmp/test_slice.vtp",
        "slice_type": "plane",
        "position": [0.5, 0.5, 0.5]
    })
    return client