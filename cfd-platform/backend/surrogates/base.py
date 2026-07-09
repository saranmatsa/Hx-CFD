"""
Base Surrogate Model Classes
Defines the interface for all surrogate model implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
import numpy.typing as npt


class SurrogateType(Enum):
    """Types of surrogate models."""
    RBF = "rbf"  # Radial Basis Function
    GAUSSIAN_PROCESS = "gaussian_process"  # Kriging/GP
    POLYNOMIAL_CHAOS = "polynomial_chaos"  # Polynomial Chaos Expansion
    NEURAL_NETWORK = "neural_network"  # Multi-layer Perceptron
    KRIGING = "kriging"  # Alias for Gaussian Process
    PCE = "pce"  # Alias for Polynomial Chaos


@dataclass
class SurrogateConfig:
    """Configuration for surrogate model training."""
    model_type: SurrogateType = SurrogateType.GAUSSIAN_PROCESS
    normalize_inputs: bool = True
    normalize_outputs: bool = True
    center_outputs: bool = True
    variance_threshold: float = 1e-10
    n_restarts_optimizer: int = 5
    random_state: Optional[int] = None
    
    # RBF-specific config
    rbf_function: str = "multiquadric"  # multiquadric, cubic, thin_plate, gaussian
    
    # GP-specific config
    gp_kernel: str = "rbf"  # rbf, matern, constant
    gp_length_scale: Optional[float] = None
    gp_alpha: float = 1e-10  # Regularization
    gp_n_restarts: int = 5
    
    # PCE-specific config
    pce_order: int = 3
    pce_method: str = "least_squares"  # least_squares, ols, lasso
    pce_sparse: bool = False
    
    # Neural network config
    nn_hidden_layers: List[int] = field(default_factory=lambda: [64, 32])
    nn_activation: str = "relu"
    nn_learning_rate: float = 0.001
    nn_max_iter: int = 1000
    nn_tolerance: float = 1e-6
    nn_early_stopping: bool = True
    nn_validation_fraction: float = 0.1
    
    # Training options
    cross_validation_folds: int = 5
    compute_derivatives: bool = False


@dataclass
class SurrogateResult:
    """Result of surrogate model training or prediction."""
    success: bool
    model_type: SurrogateType
    predictions: Optional[np.ndarray] = None
    mean_predictions: Optional[np.ndarray] = None
    std_predictions: Optional[np.ndarray] = None
    derivatives: Optional[Dict[str, np.ndarray]] = None
    error_message: Optional[str] = None
    
    # Training metrics
    training_score: Optional[float] = None
    cross_validation_score: Optional[float] = None
    loo_cross_validation_score: Optional[float] = None
    
    # Model info
    n_training_points: Optional[int] = None
    n_features: Optional[int] = None
    n_outputs: Optional[int] = None
    
    # Computational metrics
    training_time_seconds: Optional[float] = None
    prediction_time_seconds: Optional[float] = None


class SurrogateModel(ABC):
    """
    Abstract base class for surrogate models.
    
    Surrogate models provide fast approximations of expensive CFD simulations
    by learning the input-output relationship from training data.
    """
    
    def __init__(self, config: SurrogateConfig):
        """
        Initialize the surrogate model.
        
        Args:
            config: Configuration for the surrogate model
        """
        self.config = config
        self._is_trained = False
        self._input_scaler: Optional[Any] = None
        self._output_scaler: Optional[Any] = None
        self._X_train: Optional[np.ndarray] = None
        self._y_train: Optional[np.ndarray] = None
        self._n_features: int = 0
        self._n_outputs: int = 0
    
    @property
    def is_trained(self) -> bool:
        """Check if the model has been trained."""
        return self._is_trained
    
    @property
    def n_features(self) -> int:
        """Number of input features."""
        return self._n_features
    
    @property
    def n_outputs(self) -> int:
        """Number of output dimensions."""
        return self._n_outputs
    
    @abstractmethod
    def fit(
        self,
        X: npt.NDArray,
        y: npt.NDArray,
        **kwargs
    ) -> SurrogateResult:
        """
        Train the surrogate model.
        
        Args:
            X: Training inputs (n_samples, n_features)
            y: Training outputs (n_samples, n_outputs)
            
        Returns:
            SurrogateResult with training metrics
        """
        pass
    
    @abstractmethod
    def predict(
        self,
        X: npt.NDArray,
        return_variance: bool = False,
        **kwargs
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Make predictions using the surrogate model.
        
        Args:
            X: Input points (n_samples, n_features)
            return_variance: Whether to return prediction variance
            
        Returns:
            Tuple of (predictions, variance) where variance is None if return_variance=False
        """
        pass
    
    @abstractmethod
    def predict_derivatives(
        self,
        X: npt.NDArray,
        **kwargs
    ) -> Dict[str, np.ndarray]:
        """
        Compute prediction derivatives with respect to inputs.
        
        Args:
            X: Input points (n_samples, n_features)
            
        Returns:
            Dictionary mapping feature names to derivative arrays
        """
        pass
    
    @abstractmethod
    def compute_leave_one_out_error(self) -> float:
        """
        Compute leave-one-out cross-validation error.
        
        Returns:
            LOO-CV error (RMSE for regression)
        """
        pass
    
    def save(self, filepath: str) -> None:
        """
        Save the trained model to a file.
        
        Args:
            filepath: Path to save the model
        """
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)
    
    @classmethod
    def load(cls, filepath: str) -> "SurrogateModel":
        """
        Load a trained model from a file.
        
        Args:
            filepath: Path to the saved model
            
        Returns:
            Loaded surrogate model
        """
        import pickle
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    
    def _normalize_inputs(self, X: np.ndarray) -> np.ndarray:
        """Normalize input data."""
        if self._input_scaler is None:
            from sklearn.preprocessing import StandardScaler
            self._input_scaler = StandardScaler()
            return self._input_scaler.fit_transform(X)
        return self._input_scaler.transform(X)
    
    def _normalize_outputs(self, y: np.ndarray) -> np.ndarray:
        """Normalize output data."""
        if self._output_scaler is None:
            from sklearn.preprocessing import StandardScaler
            self._output_scaler = StandardScaler()
            return self._output_scaler.fit_transform(y)
        return self._output_scaler.transform(y)
    
    def _denormalize_outputs(self, y_normalized: np.ndarray) -> np.ndarray:
        """Denormalize output data."""
        if self._output_scaler is None:
            return y_normalized
        return self._output_scaler.inverse_transform(y_normalized)
    
    def _validate_training_data(
        self,
        X: npt.NDArray,
        y: npt.NDArray
    ) -> Tuple[int, int, int]:
        """
        Validate and prepare training data.
        
        Args:
            X: Input data
            y: Output data
            
        Returns:
            Tuple of (n_samples, n_features, n_outputs)
        """
        X = np.asarray(X)
        y = np.asarray(y)
        
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if y.ndim == 1:
            y = y.reshape(-1, 1)
        
        n_samples = X.shape[0]
        n_features = X.shape[1]
        n_outputs = y.shape[1] if y.ndim > 1 else 1
        
        if n_samples == 0:
            raise ValueError("Training data is empty")
        if n_samples != y.shape[0]:
            raise ValueError(
                f"X and y have different number of samples: "
                f"{n_samples} vs {y.shape[0]}"
            )
        
        self._n_features = n_features
        self._n_outputs = n_outputs
        self._X_train = X
        self._y_train = y
        
        return n_samples, n_features, n_outputs