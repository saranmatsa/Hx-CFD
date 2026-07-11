"""
Mesh models for CFD Backend.

Defines mesh-related enums and models.
"""

import enum


class MeshFormat(str, enum.Enum):
    """Mesh file format enumeration."""
    GMSH = "gmsh"
    OPENFOAM = "openfoam"
    CGNS = "cgns"
    VTK = "vtk"
    STL = "stl"
    OBJ = "obj"
    PLY = "ply"
    MED = "med"
    UNV = "unv"
    NASTRAN = "nastran"
    ABAQUS = "abaqus"
    ANSYS = "ansys"
    FLUENT = "fluent"
    STARCD = "starcd"
    NEUTRAL = "neutral"
    EXODUS = "exodus"
    XDMF = "xdmf"
    HDF5 = "hdf5"


class MeshQualityMetric(str, enum.Enum):
    """Mesh quality metric enumeration."""
    ORTHOGONALITY = "orthogonality"
    ASPECT_RATIO = "aspect_ratio"
    SKEWNESS = "skewness"
    JACOBIAN = "jacobian"
    VOLUME_RATIO = "volume_ratio"
    FACE_ANGLE = "face_angle"
    EDGE_RATIO = "edge_ratio"
    WARPAGE = "warpage"
    TAPER = "taper"
    VOLUME = "volume"


class MeshGenerationMethod(str, enum.Enum):
    """Mesh generation method enumeration."""
    GMSH = "gmsh"
    BLOCKMESH = "blockMesh"
    SHELLMESH = "shellMesh"
    SNAPPYHEXMESH = "snappyHexMesh"
    CARTESIAN = "cartesian"
    TETRAHEDRAL = "tetrahedral"
    HEXAHEDRAL = "hexahedral"
    POLYHEDRAL = "polyhedral"
    CUSTOM = "custom"


# Re-export from project.py for convenience
from cfd_backend.models.project import (
    Mesh,
    MeshType,
    MeshStatus,
)