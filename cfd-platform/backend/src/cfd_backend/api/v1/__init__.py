"""Legacy API v1 router construction.

Imports are deliberately deferred.  ``cfd_backend.api.v1.workflow`` is the
desktop's private service contract and must remain startable when optional
browser/API authentication packages are absent from the engineering runtime.
"""

from fastapi import APIRouter

__all__ = ["api_router", "build_api_router"]


def build_api_router() -> APIRouter:
    """Build the full legacy public API only for callers that request it."""
    from cfd_backend.api.v1 import (
        auth,
        dependencies,
        meshes,
        optimization,
        post,
        projects,
        simulations,
        solvers,
        users,
        workflow,
    )

    api_router = APIRouter()
    api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    api_router.include_router(users.router, prefix="/users", tags=["Users"])
    api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
    api_router.include_router(simulations.router, prefix="/simulations", tags=["Simulations"])
    api_router.include_router(meshes.router, prefix="/meshes", tags=["Meshes"])
    api_router.include_router(solvers.router, prefix="/solvers", tags=["Solvers"])
    api_router.include_router(post.router, prefix="/post", tags=["Post-Processing"])
    api_router.include_router(optimization.router, prefix="/optimization", tags=["Optimization"])
    api_router.include_router(dependencies.router, prefix="/dependencies", tags=["Dependencies"])
    api_router.include_router(workflow.router, prefix="/workflow", tags=["Desktop Workflow"])
    return api_router


def __getattr__(name: str):
    if name == "api_router":
        return build_api_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
