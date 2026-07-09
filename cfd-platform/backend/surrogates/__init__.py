"""
Surrogate Model Module
Provides fast approximations of expensive CFD simulations using machine learning.

Surrogate Models Available:
- RBFSurrogate: Radial Basis Function network for smooth interpolation
- GaussianProcessSurrogate: Kriging with uncertainty quantification
- PolynomialChaosSurrogate: Global polynomial representation for UQ
- NeuralNetworkSurrogate: MLP for highly non-linear response surfaces

Usage:
    from backend.surrogates import (
        SurrogateModel,
        SurrogateConfig,
        SurrogateType,
        RBFNetworkSurrogate,
        GaussianProcessSurrogate,
        PolynomialChaosSurrogate,
        NeuralNetworkSurrogate,
    )
"""

from .base import SurrogateModel, SurrogateConfig, SurrogateType
from .rbf import RBFSurrogate
from .gaussian_process import GaussianProcessSurrogate
from .polynomial_chaos import PolynomialChaosSurrogate
from .neural_network import NeuralNetworkSurrogate

__all__ = [
    # Base classes
    "SurrogateModel",
    "SurrogateConfig",
    "SurrogateType",
    # Implementations
    "RBFSurrogate",
    "GaussianProcessSurrogate",
    "PolynomialChaosSurrogate",
    "NeuralNetworkSurrogate",
]