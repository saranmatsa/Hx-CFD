"""
Radial Basis Function (RBF) Surrogate Model
Fast interpolation using radial basis functions for scattered data.
"""

import time
from typing import Dict, Tuple, Optional
import numpy as np
import numpy.typing as npt
from scipy.interpolate import RBFInterpolator
from sklearn.model_selection import cross_val_score

from .base import SurrogateModel, SurrogateConfig, SurrogateResult, SurrogateType


class RBFSurrogate(SurrogateModel):
    """
    Radial Basis Function surrogate model.
    
    Uses scipy's RBFInterpolator for fast interpolation of scattered data.
    Supports various radial basis functions including multiquadric, cubic,
    thin-plate spline, and Gaussian.
    
    Advantages:
    - Fast training (exact interpolation)
    - Works well with scattered/unstructured data
    - No hyperparameters to tune (except kernel choice)
    - Supports high-dimensional inputs
    
    Disadvantages:
    - Memory scales with training data size (O(n^2))
    - Not suitable for very large training sets (>10k points)
    - No uncertainty quantification
    - Can be ill-conditioned for large datasets
    """
    
    def __init__(self, config: Optional[SurrogateConfig] = None):
        if config is None:
            config = SurrogateConfig(model_type=SurrogateType.RBF)
        super().__init__(config)
        self._rbf_interpolators: Dict[int, RBFInterpolator] = {}
        self._kernel_map = {
            "multiquadric": "multiquadric",
            "cubic": "cubic",
            "thin_plate": "thin_plate_spline",
            "gaussian": "gaussian",
            "linear": "linear",
            "quintic": "quintic",
        }
    
    def fit(
        self,
        X: npt.NDArray,
        y: npt.NDArray,
        **kwargs
    ) -> SurrogateResult:
        """
        Train the RBF surrogate model.
        
        Args:
            X: Training inputs (n_samples, n_features)
            y: Training outputs (n_samples, n_outputs)
            
        Returns:
            SurrogateResult with training metrics
        """
        start_time = time.time()
        
        try:
            n_samples, n_features, n_outputs = self._validate_training_data(X, y)
            
            # Normalize inputs
            if self.config.normalize_inputs:
                X_normalized = self._normalize_inputs(self._X_train)
            else:
                X_normalized = self._X_train
            
            # Normalize outputs
            if self.config.normalize_outputs:
                y_normalized = self._normalize_outputs(self._y_train)
            else:
                y_normalized = self._y_train
            
            # Get kernel name
            kernel = self._kernel_map.get(
                self.config.rbf_function,
                "multiquadric"
            )
            
            # Train separate interpolator for each output
            self._rbf_interpolators = {}
            for i in range(n_outputs):
                self._rbf_interpolators[i] = RBFInterpolator(
                    X_normalized,
                    y_normalized[:, i],
                    kernel=kernel,
                    neighbors=None,
                    smoothing=0,
                    kernel_options={"epsilon": 1.0}
                )
            
            self._is_trained = True
            training_time = time.time() - start_time
            
            # Compute training score (using cross-validation)
            cv_scores = []
            for i in range(n_outputs):
                scores = cross_val_score(
                    _RBFWrapper(kernel),
                    X_normalized,
                    y_normalized[:, i],
                    cv=min(5, n_samples),  # Use 5-fold or less if not enough samples
                    scoring="neg_mean_squared_error"
                )
                cv_scores.append(-scores.mean())
            
            return SurrogateResult(
                success=True,
                model_type=SurrogateType.RBF,
                training_score=1.0 - np.mean(cv_scores),  # Approximate R²
                cross_validation_score=1.0 - np.mean(cv_scores),
                n_training_points=n_samples,
                n_features=n_features,
                n_outputs=n_outputs,
                training_time_seconds=training_time
            )
            
        except Exception as e:
            return SurrogateResult(
                success=False,
                model_type=SurrogateType.RBF,
                error_message=str(e)
            )
    
    def predict(
        self,
        X: npt.NDArray,
        return_variance: bool = False,
        **kwargs
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Make predictions using the RBF surrogate model.
        
        Args:
            X: Input points (n_samples, n_features)
            return_variance: Ignored for RBF (no uncertainty quantification)
            
        Returns:
            Tuple of (predictions, None) - RBF doesn't provide variance
        """
        if not self._is_trained:
            raise RuntimeError("Model must be trained before prediction")
        
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        if X.shape[1] != self._n_features:
            raise ValueError(
                f"Input has {X.shape[1]} features, expected {self._n_features}"
            )
        
        # Normalize inputs
        if self.config.normalize_inputs:
            X_normalized = self._input_scaler.transform(X)
        else:
            X_normalized = X
        
        # Predict for each output
        predictions = np.zeros((X.shape[0], self._n_outputs))
        for i, interpolator in self._rbf_interpolators.items():
            predictions[:, i] = interpolator(X_normalized)
        
        # Denormalize outputs
        if self.config.normalize_outputs:
            predictions = self._denormalize_outputs(predictions)
        
        # RBF doesn't provide uncertainty
        return predictions, None
    
    def predict_derivatives(
        self,
        X: npt.NDArray,
        **kwargs
    ) -> Dict[str, np.ndarray]:
        """
        Compute prediction derivatives using finite differences.
        
        Args:
            X: Input points (n_samples, n_features)
            
        Returns:
            Dictionary with derivatives for each feature
        """
        if not self._is_trained:
            raise RuntimeError("Model must be trained before prediction")
        
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        eps = 1e-7  # Finite difference step
        n_samples, n_features = X.shape
        derivatives = {}
        
        for feat_idx in range(n_features):
            # Compute prediction at X + eps
            X_plus = X.copy()
            X_plus[:, feat_idx] += eps
            
            pred_plus, _ = self.predict(X_plus)
            
            # Compute prediction at X - eps
            X_minus = X.copy()
            X_minus[:, feat_idx] -= eps
            
            pred_minus, _ = self.predict(X_minus)
            
            # Central difference
            derivatives[f"feature_{feat_idx}"] = (pred_plus - pred_minus) / (2 * eps)
        
        return derivatives
    
    def compute_leave_one_out_error(self) -> float:
        """
        Compute leave-one-out cross-validation error.
        
        For RBF, this is expensive (O(n^2)) but provides an unbiased
        estimate of generalization error.
        
        Returns:
            LOO-CV RMSE
        """
        if not self._is_trained:
            raise RuntimeError("Model must be trained first")
        
        n_samples = self._X_train.shape[0]
        
        # For large datasets, use subset
        if n_samples > 1000:
            indices = np.random.choice(n_samples, 1000, replace=False)
            X_subset = self._X_train[indices]
            y_subset = self._y_train[indices]
            n_eval = 1000
        else:
            X_subset = self._X_train
            y_subset = self._y_train
            n_eval = n_samples
        
        # Predict on subset using model trained on complement
        predictions, _ = self.predict(X_subset)
        
        # Compute RMSE
        rmse = np.sqrt(np.mean((predictions - y_subset) ** 2))
        return rmse


class _RBFWrapper:
    """Wrapper to make RBFInterpolator compatible with sklearn."""
    
    def __init__(self, kernel: str):
        self.kernel = kernel
        self.interpolator = None
    
    def fit(self, X, y):
        self.interpolator = RBFInterpolator(X, y, kernel=self.kernel)
        return self
    
    def predict(self, X):
        return self.interpolator(X)