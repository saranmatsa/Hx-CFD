"""
Nevergrad Integration Module
Provides optimization capabilities using Facebook's Nevergrad library.
"""

from .client import NevergradClient, OptimizationResult, OptimizationConfig

__all__ = [
    "NevergradClient",
    "OptimizationResult",
    "OptimizationConfig",
]