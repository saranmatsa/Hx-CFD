"""
Neural Network Surrogate Model
Multi-layer perceptron for non-linear approximation.
"""

import time
from typing import Dict, Tuple, Optional, Any
import numpy as np
import numpy.typing as npt

from .base import SurrogateModel, SurrogateConfig, SurrogateResult, SurrogateType


class NeuralNetworkSurrogate(SurrogateModel):
    """
    Neural Network (MLP) surrogate model.
    
    Uses a multi-layer perceptron to approximate complex, non-linear
    response surfaces. Particularly useful for high-dimensional,
    highly non-linear problems.
    
    Advantages:
    - Can approximate any continuous function (universal approximator)
    - Handles high-dimensional inputs well
    - Learns hierarchical feature representations
    - Scales to large datasets
    
    Disadvantages:
    - Requires careful hyperparameter tuning
    - Can be slow to train
    - May overfit without proper regularization
    - Less interpretable than polynomial methods
    - Requires more data than local methods
    """
    
    def __init__(self, config: Optional[SurrogateConfig] = None):
        if config is None:
            config = SurrogateConfig(model_type=SurrogateType.NEURAL_NETWORK)
        super().__init__(config)
        self._model: Optional[Any] = None
        self._use_pytorch = False
        self._pytorch_model: Optional[Any] = None
    
    def _get_backend(self) -> str:
        """Determine which backend to use."""
        try:
            import torch
            self._use_pytorch = True
            return "pytorch"
        except ImportError:
            pass
        
        try:
            from sklearn.neural_network import MLPRegressor
            return "sklearn"
        except ImportError:
            raise ImportError(
                "NeuralNetworkSurrogate requires either PyTorch or scikit-learn. "
                "Install with: pip install torch  OR  pip install scikit-learn"
            )
    
    def _build_sklearn_model(self):
        """Build scikit-learn MLPRegressor."""
        from sklearn.neural_network import MLPRegressor
        
        hidden_layer_sizes = self.config.nn_hidden_layers
        if hidden_layer_sizes is None:
            hidden_layer_sizes = (64, 32)
        
        activation = self.config.nn_activation.lower()
        if activation == "relu":
            activation = "relu"
        elif activation == "tanh":
            activation = "tanh"
        else:
            activation = "relu"
        
        return MLPRegressor(
            hidden_layer_sizes=hidden_layer_sizes,
            activation=activation,
            solver="adam",
            alpha=self.config.nn_regularization,
            batch_size="auto",
            learning_rate="adaptive",
            learning_rate_init=self.config.nn_learning_rate,
            max_iter=self.config.max_iterations,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=20,
            random_state=self.config.random_state,
            verbose=False
        )
    
    def _build_pytorch_model(self, n_inputs: int, n_outputs: int):
        """Build PyTorch MLP model."""
        import torch
        import torch.nn as nn
        
        hidden_layers = self.config.nn_hidden_layers
        if hidden_layers is None:
            hidden_layers = (64, 32)
        
        activation = self.config.nn_activation.lower()
        if activation == "relu":
            act_fn = nn.ReLU
        elif activation == "tanh":
            act_fn = nn.Tanh
        else:
            act_fn = nn.ReLU
        
        layers = []
        prev_size = n_inputs
        
        for size in hidden_layers:
            layers.append(nn.Linear(prev_size, size))
            layers.append(act_fn())
            prev_size = size
        
        layers.append(nn.Linear(prev_size, n_outputs))
        
        class MLP(nn.Module):
            def __init__(self, layers):
                super().__init__()
                self.network = nn.Sequential(*layers)
            
            def forward(self, x):
                return self.network(x)
        
        return MLP(layers)
    
    def _train_pytorch(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ):
        """Train PyTorch model."""
        import torch
        from torch.utils.data import DataLoader, TensorDataset
        
        n_inputs = X.shape[1]
        n_outputs = y.shape[1] if y.ndim > 1 else 1
        
        self._pytorch_model = self._build_pytorch_model(n_inputs, n_outputs)
        
        # Prepare data
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)
        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=64, shuffle=True)
        
        # Validation data
        if X_val is not None and y_val is not None:
            X_val_tensor = torch.FloatTensor(X_val)
            y_val_tensor = torch.FloatTensor(y_val)
            val_dataset = TensorDataset(X_val_tensor, y_val_tensor)
            val_loader = DataLoader(val_dataset, batch_size=64)
        else:
            val_loader = None
        
        # Optimizer
        optimizer = torch.optim.Adam(
            self._pytorch_model.parameters(),
            lr=self.config.nn_learning_rate,
            weight_decay=self.config.nn_regularization
        )
        criterion = torch.nn.MSELoss()
        
        # Training loop
        best_val_loss = float('inf')
        patience = 20
        patience_counter = 0
        
        for epoch in range(self.config.max_iterations):
            self._pytorch_model.train()
            train_loss = 0.0
            
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                outputs = self._pytorch_model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            # Validation
            if val_loader is not None:
                self._pytorch_model.eval()
                val_loss = 0.0
                with torch.no_grad():
                    for batch_X, batch_y in val_loader:
                        outputs = self._pytorch_model(batch_X)
                        val_loss += criterion(outputs, batch_y).item()
                
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        break
        
        self._use_pytorch = True
    
    def fit(
        self,
        X: npt.NDArray,
        y: npt.NDArray,
        **kwargs
    ) -> SurrogateResult:
        """
        Train the neural network surrogate model.
        
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
            
            # Choose backend
            backend = self._get_backend()
            
            if backend == "sklearn":
                self._model = self._build_sklearn_model()
                self._model.fit(X_normalized, y_normalized)
                training_score = self._model.score(X_normalized, y_normalized)
            else:
                # Split for validation
                n_val = max(int(n_samples * 0.1), 10)
                indices = np.random.permutation(n_samples)
                train_idx = indices[n_val:]
                val_idx = indices[:n_val]
                
                self._train_pytorch(
                    X_normalized[train_idx],
                    y_normalized[train_idx],
                    X_normalized[val_idx],
                    y_normalized[val_idx]
                )
                
                # Compute training score
                self._pytorch_model.eval()
                with torch.no_grad():
                    X_tensor = torch.FloatTensor(X_normalized)
                    predictions = self._pytorch_model(X_tensor).numpy()
                
                ss_res = np.sum((y_normalized - predictions) ** 2)
                ss_tot = np.sum((y_normalized - np.mean(y_normalized)) ** 2)
                training_score = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            
            self._is_trained = True
            training_time = time.time() - start_time
            
            # Compute validation score using cross-validation
            cv_score = self._compute_cv_score(X_normalized, y_normalized)
            
            return SurrogateResult(
                success=True,
                model_type=SurrogateType.NEURAL_NETWORK,
                training_score=training_score,
                loo_cross_validation_score=cv_score,
                n_training_points=n_samples,
                n_features=n_features,
                n_outputs=n_outputs,
                training_time_seconds=training_time
            )
            
        except Exception as e:
            return SurrogateResult(
                success=False,
                model_type=SurrogateType.NEURAL_NETWORK,
                error_message=str(e)
            )
    
    def _compute_cv_score(self, X: np.ndarray, y: np.ndarray) -> float:
        """Compute cross-validation score."""
        from sklearn.model_selection import cross_val_predict
        from sklearn.metrics import r2_score
        
        try:
            import torch
            # For PyTorch, use a simple train/test split
            n = len(X)
            split = int(0.8 * n)
            indices = np.random.permutation(n)
            
            X_train, X_test = X[indices[:split]], X[indices[split:]]
            y_train, y_test = y[indices[:split]], y[indices[split:]]
            
            self._train_pytorch(X_train, y_train)
            
            self._pytorch_model.eval()
            with torch.no_grad():
                X_test_tensor = torch.FloatTensor(X_test)
                predictions = self._pytorch_model(X_test_tensor).numpy()
            
            return r2_score(y_test, predictions)
            
        except ImportError:
            # Use sklearn cross-validation
            model = self._build_sklearn_model()
            predictions = cross_val_predict(model, X, y, cv=5)
            return r2_score(y, predictions)
    
    def predict(
        self,
        X: npt.NDArray,
        return_variance: bool = False,
        **kwargs
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Make predictions using the neural network surrogate model.
        
        Args:
            X: Input points (n_samples, n_features)
            return_variance: Whether to return MC dropout variance
            
        Returns:
            Tuple of (predictions, variance)
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
        
        if self._use_pytorch:
            import torch
            
            self._pytorch_model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X_normalized)
                predictions = self._pytorch_model(X_tensor).numpy()
            
            variance = None
            if return_variance:
                # MC Dropout for uncertainty estimation
                self._pytorch_model.train()
                n_samples = 50
                mc_predictions = []
                
                for _ in range(n_samples):
                    with torch.no_grad():
                        pred = self._pytorch_model(X_tensor).numpy()
                        mc_predictions.append(pred)
                
                mc_predictions = np.stack(mc_predictions)
                predictions = np.mean(mc_predictions, axis=0)
                variance = np.var(mc_predictions, axis=0)
                
                self._pytorch_model.eval()
        else:
            predictions = self._model.predict(X_normalized)
            variance = None
        
        # Denormalize outputs
        if self.config.normalize_outputs:
            predictions = self._denormalize_outputs(predictions)
            if variance is not None:
                # Scale variance appropriately
                variance = variance * (self._output_scaler.scale_ ** 2)
        
        return predictions, variance
    
    def predict_derivatives(
        self,
        X: npt.NDArray,
        method: str = "finite_diff",
        **kwargs
    ) -> Dict[str, np.ndarray]:
        """
        Compute prediction derivatives.
        
        Args:
            X: Input points (n_samples, n_features)
            method: "finite_diff" or "automatic_diff"
            
        Returns:
            Dictionary with derivatives for each feature
        """
        if not self._is_trained:
            raise RuntimeError("Model must be trained before prediction")
        
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        derivatives = {}
        eps = 1e-6
        
        for feat_idx in range(X.shape[1]):
            X_plus = X.copy()
            X_plus[:, feat_idx] += eps
            pred_plus, _ = self.predict(X_plus)
            
            X_minus = X.copy()
            X_minus[:, feat_idx] -= eps
            pred_minus, _ = self.predict(X_minus)
            
            derivatives[f"feature_{feat_idx}"] = (pred_plus - pred_minus) / (2 * eps)
        
        return derivatives
    
    def get_feature_importance(self) -> np.ndarray:
        """
        Compute feature importance using connection weights.
        
        Returns:
            Array of importance scores for each feature
        """
        if not self._is_trained:
            raise RuntimeError("Model must be trained first")
        
        if self._use_pytorch:
            # Use gradient-based importance
            import torch
            
            X_tensor = torch.FloatTensor(self._X_train[:100])
            X_tensor.requires_grad = True
            
            self._pytorch_model.eval()
            output = self._pytorch_model(X_tensor)
            
            # Gradient of output w.r.t. input
            gradients = torch.autograd.grad(
                outputs=output.mean(),
                inputs=X_tensor,
                retain_graph=True
            )[0]
            
            importance = gradients.abs().mean(dim=0).detach().numpy()
        else:
            # Use connection weights method (Olden et al.)
            weights = self._model.coefs_
            activations = self._model.hidden_layer_sizes
            
            # Compute importance as sum of weight products
            importance = np.zeros(self._n_features)
            for i in range(len(weights) - 1):
                # Absolute value of weights
                w = np.abs(weights[i])
                w_next = np.abs(weights[i + 1])
                
                # Connection weight contribution
                contribution = np.dot(w, w_next.mean(axis=1))
                importance += contribution
            
            importance = importance / len(weights)
        
        # Normalize
        if importance.sum() > 0:
            importance = importance / importance.sum()
        
        return importance
    
    def save(self, path: str):
        """Save the trained model."""
        if not self._is_trained:
            raise RuntimeError("Model must be trained before saving")
        
        if self._use_pytorch:
            import torch
            torch.save({
                "model_state": self._pytorch_model.state_dict(),
                "config": self.config,
                "n_features": self._n_features,
                "n_outputs": self._n_outputs,
                "input_scaler": self._input_scaler,
                "output_scaler": self._output_scaler
            }, path)
        else:
            import joblib
            joblib.dump({
                "model": self._model,
                "config": self.config,
                "n_features": self._n_features,
                "n_outputs": self._n_outputs,
                "input_scaler": self._input_scaler,
                "output_scaler": self._output_scaler
            }, path)
    
    @classmethod
    def load(cls, path: str) -> "NeuralNetworkSurrogate":
        """Load a trained model."""
        try:
            import torch
            checkpoint = torch.load(path)
            
            instance = cls(config=checkpoint["config"])
            instance._n_features = checkpoint["n_features"]
            instance._n_outputs = checkpoint["n_outputs"]
            instance._input_scaler = checkpoint["input_scaler"]
            instance._output_scaler = checkpoint["output_scaler"]
            instance._use_pytorch = True
            
            instance._pytorch_model = instance._build_pytorch_model(
                instance._n_features, instance._n_outputs
            )
            instance._pytorch_model.load_state_dict(checkpoint["model_state"])
            instance._is_trained = True
            
            return instance
            
        except ImportError:
            import joblib
            data = joblib.load(path)
            
            instance = cls(config=data["config"])
            instance._model = data["model"]
            instance._n_features = data["n_features"]
            instance._n_outputs = data["n_outputs"]
            instance._input_scaler = data["input_scaler"]
            instance._output_scaler = data["output_scaler"]
            instance._is_trained = True
            
            return instance