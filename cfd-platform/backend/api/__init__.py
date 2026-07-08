"""
API module - FastAPI routers and endpoints
"""

from . import projects
from . import meshes
from . import simulations
from . import visualization
from . import optimization
from . import pipeline_routes
from .v1.router import router as api_v1_router

__all__ = [
    "projects",
    "meshes",
    "simulations",
    "visualization",
    "optimization",
    "pipeline_routes",
    "api_v1_router",
]