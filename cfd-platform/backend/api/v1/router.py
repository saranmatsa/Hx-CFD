"""
v1 API router - aggregates all v1 endpoints.
"""

from fastapi import APIRouter

from .endpoints import meshes, simulations, optimizations, websocket, dependencies

router = APIRouter(prefix="/v1")

router.include_router(meshes.router)
router.include_router(simulations.router)
router.include_router(optimizations.router)
router.include_router(websocket.router)
router.include_router(dependencies.router)