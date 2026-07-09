"""
OpenMDAO Integration Module
Provides multidisciplinary optimization capabilities using NASA's OpenMDAO framework.
"""

from .client import OpenMDAOClient, MDAOProblem, MDAOComponent, OptimizationResult

__all__ = [
    "OpenMDAOClient",
    "MDAOProblem",
    "MDAOComponent",
    "OptimizationResult",
]