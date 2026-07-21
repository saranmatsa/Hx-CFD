"""CFD Backend API package.

The desktop starts a narrow local workflow router.  Do not import the legacy
web API graph here: importing a submodule must not require optional web-only
authentication dependencies that the local engineering runtime does not use.
"""

__all__ = ["api_router"]


def __getattr__(name: str):
    """Construct the legacy aggregate router only when it is explicitly used."""
    if name == "api_router":
        from cfd_backend.api.v1 import build_api_router

        return build_api_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
