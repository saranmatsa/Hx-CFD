"""
API v1 router for CFD Backend.

Aggregates all API route modules.
"""

from fastapi import APIRouter

from cfd_backend.api.v1 import projects, simulations, meshes, solvers, post, optimization, users, auth

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(simulations.router, prefix="/simulations", tags=["Simulations"])
api_router.include_router(meshes.router, prefix="/meshes", tags=["Meshes"])
api_router.include_router(solvers.router, prefix="/solvers", tags=["Solvers"])
api_router.include_router(post.router, prefix="/post", tags=["Post-Processing"])
api_router.include_router(optimization.router, prefix="/optimization", tags=["Optimization"])