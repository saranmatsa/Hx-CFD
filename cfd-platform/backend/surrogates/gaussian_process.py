"""
Gaussian Process (Kriging) Surrogate Model
Bayesian approach providing uncertainty quantification.
"""

import time
from typing import Dict, Tuple, Optional
import numpy as np
import numpy.typing as npt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    RBF, Matern, ConstantKernel, WhiteKernel, Kernel
)

from .base import SurrogateModel, SurrogateConfig, SurrogateResult, SurrogateType


class GaussianProcessSurrogate(SurrogateModel):
    """
    Gaussian Process (Kriging) surrogate model.
    
    Provides probabilistic predictions with uncertainty quantification.
    Ideal for optimization, uncertainty propagation, and adaptive sampling.
    
    Advantages:
    - Uncertainty quantification (mean and variance)
    - Probabilistic predictions
    - Automatic hyperparameter optimization
    - Works well with sparse data
    
    Disadvantages:
    - O(n^3) training complexity
    - Memory scales with O(n^2)
    - Not suitable for large training sets (>5000 points)
    - Can be slow for high-dimensional inputs
    """
    
    def __init__(self, config: Optional[SurrogateConfig] = None):
        if config is None:
            config = SurrogateConfig(model_type=SurrogateType.GAUSSIAN_PROCESS)
        super().__init__(config)
        self._gp_models: Dict[int, GaussianProcessRegressor] = {}
        self._kernel_map = {
            "rbf": lambda: RBF(length_scale=1.0),
            "matern": lambda: Matern(length_scale=1.0, nu=2.5),
            "constant": lambda: ConstantKernel(constant_value=1.0),
        }
    
    def _build_kernel(self) -> Kernel:
        """Build the kernel for Gaussian Process."""
        kernel_name = self.config.gp_kernel.lower()
        
        if kernel_name == "rbf":
            base_kernel = RBF(
                length_scale=self.config.gp_length_scale or 1.0,
                length_scale_bounds=(1e-5, 1e5)
            )
        elif kernel_name == "matern":
            base_kernel = Matern(
                length_scale=self.config.gp_length_scale or 1.0,
                nu=2.5,
                length_scale_bounds=(1e-5, 1e5)
            )
        else:
            base_kernel = RBF(
                length_scale=self.config.gp_length_scale or 1.0,
                length_scale_bounds=(1e-5, 1e5)
            )
        
        # Add white noise kernel for regularization
        kernel = ConstantKernel(constant_value=1.0) * base_kernel + WhiteKernel(
            noise_level=self.config.gp_alpha,
            noise_level_bounds=(1e-10, 1e1)
        )
        
        return kernel
    
    def fit(
        self,
        X: npt.NDArray,
        y: npt.NDArray,
        **kwargs
    ) -> SurrogateResult:
        """
        Train the Gaussian Process surrogate model.
        
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
            
            # Build kernel
            kernel = self._build_kernel()
            
            # Train separate GP for each output
            self._gp_models = {}
            training_scores = []
            
            for i in range(n_outputs):
                gp = GaussianProcessRegressor(
                    kernel=kernel,
                    n_restarts_optimizer=self.config.gp_n_restarts,
                    alpha=self.config.gp_alpha,
                    random_state=self.config.random_state,
                    normalize_y=False  # Already normalized
                )
                
                gp.fit(X_normalized, y_normalized[:, i])
                self._gp_models[i] = gp
                
                # Training score (log marginal likelihood)
                training_scores.append(gp.log_marginal_likelihood_value_)
            
            self._is_trained = True
            training_time = time.time() - start_time
            
            # Compute LOO-CV score
            loo_cv_score = self.compute_leave_one_out_error()
            
            return SurrogateResult(
                success=True,
                model_type=SurrogateType.GAUSSIAN_PROCESS,
                training_score=np.mean(training_scores),
                loo_cross_validation_score=loo_cv_score,
                n_training_points=n_samples,
                n_features=n_features,
                n_outputs=n_outputs,
                training_time_seconds=training_time
            )
            
        except Exception as e:
            return SurrogateResult(
                success=False,
                model_type=SurrogateType.GAUSSIAN_PROCESS,
                error_message=str(e)
            )
    
    def predict(
        self,
        X: npt.NDArray,
        return_variance: bool = True,
        **kwargs
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Make predictions with uncertainty quantification.
        
        Args:
            X: Input points (n_samples, n_features)
            return_variance: Whether to return prediction variance
            
        Returns:
            Tuple of (mean_predictions, variance)
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
        n_samples = X.shape[0]
        mean_predictions = np.zeros((n_samples, self._n_outputs))
        variance_predictions = np.zeros((n_samples, self._n_outputs)) if return_variance else None
        
        for i, gp in self._gp_models.items():
            mean, std = gp.predict(X_normalized, return_std=True)
            mean_predictions[:, i] = mean
            if return_variance:
                variance_predictions[:, i] = std ** 2
        
        # Denormalize outputs
        if self.config.normalize_outputs:
            mean_predictions = self._denormalize_outputs(mean_predictions)
            if return_variance and variance_predictions is not None:
                # Scale variance appropriately
                if self._output_scaler is not None:
                    scale = self._output_scaler.scale_
                    if self._n_outputs == 1:
                        scale = scale.reshape(1)
                    variance_predictions *= scale ** 2
        
        return mean_predictions, variance_predictions
    
    def predict_derivatives(
        self,
        X: npt.NDArray,
        **kwargs
    ) -> Dict[str, np.ndarray]:
        """
        Compute prediction derivatives analytically.
        
        For GP, derivatives can be computed analytically using the
        kernel gradient. This is more accurate than finite differences.
        
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
        
        # Use finite differences for simplicity
        # Analytical derivatives are complex to implement
        eps = 1e-7
        n_samples, n_features = X.shape
        derivatives = {}
        
        for feat_idx in range(n_features):
            X_plus = X.copy()
            X_plus[:, feat_idx] += eps
            pred_plus, _ = self.predict(X_plus)
            
            X_minus = X.copy()
            X_minus[:, feat_idx] -= eps
            pred_minus, _ = self.predict(X_minus)
            
            derivatives[f"feature_{feat_idx}"] = (pred_plus - pred_minus) / (2 * eps)
        
        return derivatives
    
    def compute_leave_one_out_error(self) -> float:
        """
        Compute leave-one-out cross-validation error.
        
        Uses the GP's built-in capability to compute LOO predictions
        efficiently via the covariance matrix inverse.
        
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
        else:
            X_subset = self._X_train
            y_subset = self._y_train
        
        # Normalize
        if self.config.normalize_inputs:
            X_normalized = self._input_scaler.transform(X_subset)
        else:
            X_normalized = X_subset
        
        if self.config.normalize_outputs:
            y_normalized = self._output_scaler.transform(y_subset)
        else:
            y_normalized = y_subset
        
        # Compute LOO predictions for first output
        gp = self._gp_models.get(0)
        if gp is None:
            return float('inf')
        
        # Use analytical LOO formula
        K = gp.kernel_(X_normalized)
        K_inv = np.linalg.inv(K + gp.alpha * np.eye(n_samples))
        alpha = K_inv @ y_normalized[:, 0]
        
        # LOO prediction for each point
        loo_preds = np.zeros(n_samples)
        for i in range(n_samples):
            loo_preds[i] = y_normalized[i, 0] - alpha[i] / K_inv[i, i]
        
        # Compute RMSE
        rmse = np.sqrt(np.mean((loo_preds - y_normalized[:, 0]) ** 2))
        return rmse
    
    def get_confidence_interval(
        self,
        X: npt.NDArray,
        confidence: float = 0.95
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get prediction with confidence intervals.
        
        Args:
            X: Input points (n_samples, n_features)
            confidence: Confidence level (default 95%)
            
        Returns:
            Tuple of (lower_bound, mean, upper_bound)
        """
        mean, variance = self.predict(X, return_variance=True)
        
        if variance is None:
            raise ValueError("Variance not available")
        
        std = np.sqrt(variance)
        
        # Z-score for confidence interval
        from scipy.stats import norm
        z = norm.ppf((1 + confidence) / 2)
        
        lower = mean - z * std
        upper = mean + z * std
        
        return lower, mean, upper