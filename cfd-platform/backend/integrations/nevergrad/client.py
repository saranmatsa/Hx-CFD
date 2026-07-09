"""
Nevergrad Client Module
Provides optimization capabilities using Facebook's Nevergrad library.

Nevergrad is used for:
- Single-objective optimization
- Multi-objective optimization
- Constraint handling
- Parameter tuning
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Union
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class OptimizerType(Enum):
    """Available optimizer types from Nevergrad."""
    # Single-objective optimizers
    NG_SPSA = "SPSA"
    NG_CMA = "CMA"
    NG_TBPSA = "TBPSA"
    NG_ONE_PLUS_ONE = "OnePlusOne"
    NG_TWO_PLUS_ONE = "TwoPlusOne"
    NG_RECURSIVE = "Recursive"
    NG_PURE_RANDOM = "PureRandom"
    NG_RANDOM_RESTRICTED_PANDAS = "RandomRestrictedPandas"
    NG_GR_SHADOW = "GR_SHADOW"
    NG_NG_OPT = "NGOpt"
    NG_CMA_PARETO = "CMAForScaledObjective"
    
    # Multi-objective optimizers
    NG_NSGA2 = "NSGA2"
    NG_BO_2A = "BO2A"
    NG_AGG_BOUNDED = "AggBounded"
    
    # Portfolio optimizers
    NG_PORTFOLIO = "Portfolio"
    NG_CMA_PORTFOLIO = "CMAPortfolio"


@dataclass
class OptimizationConfig:
    """Configuration for optimization run."""
    optimizer: OptimizerType = OptimizerType.NG_CMA
    budget: int = 1000
    num_workers: int = 1
    batch_mode: bool = False
    verbosity: int = 0
    seed: Optional[int] = None
    
    # Parameter bounds
    param_bounds: Optional[Dict[str, tuple]] = None
    param_defaults: Optional[Dict[str, float]] = None
    
    # Constraints
    constraints: Optional[List[Dict[str, Any]]] = None
    
    # Multi-objective settings
    multi_objective: bool = False
    num_objectives: int = 1


@dataclass
class OptimizationResult:
    """Result of optimization run."""
    success: bool
    best_parameters: Optional[Dict[str, float]] = None
    best_objective: Optional[float] = None
    all_objectives: Optional[List[float]] = None
    all_parameters: Optional[List[Dict[str, float]]] = None
    optimizer_name: Optional[str] = None
    num_evaluations: int = 0
    elapsed_time: float = 0.0
    error_message: Optional[str] = None
    convergence_history: Optional[List[float]] = None
    pareto_front: Optional[List[Dict[str, float]]] = None


class NevergradClient:
    """
    Client for Nevergrad optimization operations.
    
    Nevergrad provides gradient-free optimization algorithms that can be used
    for:
    - Hyperparameter tuning
    - Design optimization
    - Configuration optimization
    - Reinforcement learning optimization
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialize Nevergrad client.
        
        Args:
            config: Optimization configuration. Uses defaults if not provided.
        """
        self.config = config or OptimizationConfig()
        self._verify_nevergrad()
    
    def _verify_nevergrad(self) -> None:
        """Verify Nevergrad is installed."""
        try:
            import nevergrad as ng
            self._ng = ng
            logger.info(f"Nevergrad version: {ng.__version__}")
        except ImportError:
            logger.warning("Nevergrad not installed, optimization will not be available")
            self._ng = None
    
    def optimize(
        self,
        objective_func: Callable[[Dict[str, float]], float],
        parameter_names: List[str],
        config: Optional[OptimizationConfig] = None,
        callbacks: Optional[List[Callable]] = None
    ) -> OptimizationResult:
        """
        Run optimization using Nevergrad.
        
        Args:
            objective_func: Objective function to minimize.
                          Takes a dict of parameter_name -> value and returns a scalar.
            parameter_names: List of parameter names to optimize.
            config: Override configuration for this run.
            callbacks: Optional list of callbacks called after each evaluation.
            
        Returns:
            OptimizationResult with best parameters and objective value.
        """
        if self._ng is None:
            return OptimizationResult(
                success=False,
                error_message="Nevergrad not installed"
            )
        
        cfg = config or self.config
        
        try:
            import nevergrad as ng
            import time
            
            start_time = time.time()
            
            # Create instrumentation (parameter space)
            instrum = self._create_instrumentation(parameter_names, cfg)
            
            # Create optimizer
            optimizer = self._create_optimizer(instrum, cfg)
            
            # Track convergence
            convergence_history = []
            
            # Run optimization
            if cfg.batch_mode:
                # Batch mode: evaluate multiple candidates at once
                recommendation = self._optimize_batch(
                    optimizer, objective_func, cfg, callbacks, convergence_history
                )
            else:
                # Sequential mode: evaluate one candidate at a time
                recommendation = self._optimize_sequential(
                    optimizer, objective_func, cfg, callbacks, convergence_history
                )
            
            elapsed = time.time() - start_time
            
            # Extract results
            best_params = self._extract_parameters(recommendation, parameter_names)
            
            # Evaluate best parameters to get objective value
            best_objective = objective_func(best_params)
            
            return OptimizationResult(
                success=True,
                best_parameters=best_params,
                best_objective=best_objective,
                all_objectives=convergence_history,
                optimizer_name=cfg.optimizer.value,
                num_evaluations=len(convergence_history),
                elapsed_time=elapsed,
                convergence_history=convergence_history
            )
            
        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            return OptimizationResult(
                success=False,
                error_message=str(e)
            )
    
    def optimize_multi_objective(
        self,
        objective_funcs: List[Callable[[Dict[str, float]], float]],
        parameter_names: List[str],
        config: Optional[OptimizationConfig] = None
    ) -> OptimizationResult:
        """
        Run multi-objective optimization using Nevergrad.
        
        Args:
            objective_funcs: List of objective functions to minimize.
            parameter_names: List of parameter names to optimize.
            config: Override configuration for this run.
            
        Returns:
            OptimizationResult with Pareto front.
        """
        if self._ng is None:
            return OptimizationResult(
                success=False,
                error_message="Nevergrad not installed"
            )
        
        cfg = config or self.config
        cfg.multi_objective = True
        cfg.num_objectives = len(objective_funcs)
        
        try:
            import nevergrad as ng
            import time
            
            start_time = time.time()
            
            # Create multi-objective instrumentation
            instrum = self._create_instrumentation(parameter_names, cfg)
            
            # Create multi-objective optimizer
            optimizer = self._create_optimizer(instrum, cfg)
            
            # Run optimization
            optimizer.minimize(
                lambda params: [f(params) for f in objective_funcs],
                batch_mode=cfg.batch_mode
            )
            
            # Get Pareto front
            pareto = optimizer.pareto_front()
            pareto_front = []
            
            for candidate in pareto:
                params = self._extract_parameters(candidate, parameter_names)
                objectives = [f(candidate) for f in objective_funcs]
                params["_objectives"] = objectives
                pareto_front.append(params)
            
            elapsed = time.time() - start_time
            
            return OptimizationResult(
                success=True,
                pareto_front=pareto_front,
                optimizer_name=cfg.optimizer.value,
                num_evaluations=cfg.budget,
                elapsed_time=elapsed
            )
            
        except Exception as e:
            logger.error(f"Multi-objective optimization failed: {str(e)}")
            return OptimizationResult(
                success=False,
                error_message=str(e)
            )
    
    def _create_instrumentation(
        self,
        parameter_names: List[str],
        config: OptimizationConfig
    ):
        """Create Nevergrad instrumentation for parameters."""
        import nevergrad as ng
        
        instruments = []
        
        for name in parameter_names:
            if config.param_bounds and name in config.param_bounds:
                # Bounded parameter
                low, high = config.param_bounds[name]
                instruments.append(ng.p.Scalar(lower=low, upper=high).set_name(name))
            elif config.param_defaults and name in config.param_defaults:
                # Parameter with default
                default = config.param_defaults[name]
                instruments.append(ng.p.Scalar(lower=default * 0.5, upper=default * 1.5).set_name(name))
            else:
                # Unbounded parameter
                instruments.append(ng.p.Scalar(lower=-10, upper=10).set_name(name))
        
        return ng.p.Instrumentation(*instruments)
    
    def _create_optimizer(
        self,
        instrum,
        config: OptimizationConfig
    ):
        """Create Nevergrad optimizer."""
        import nevergrad as ng
        
        optimizer_name = config.optimizer.value
        
        try:
            # Try to get optimizer from ng.optimizers
            if hasattr(ng.optimizers, optimizer_name):
                optimizer_cls = getattr(ng.optimizers, optimizer_name)
            else:
                # Fallback to ng.get_optimizer
                optimizer_cls = ng.get_optimizer_class(optimizer_name)
            
            return optimizer_cls(
                parametrization=instrum,
                budget=config.budget,
                num_workers=config.num_workers
            )
        except Exception as e:
            logger.warning(f"Failed to create optimizer {optimizer_name}: {e}, using CMA")
            return ng.optimizers.CMA(
                parametrization=instrum,
                budget=config.budget,
                num_workers=config.num_workers
            )
    
    def _optimize_sequential(
        self,
        optimizer,
        objective_func: Callable,
        config: OptimizationConfig,
        callbacks: Optional[List[Callable]],
        convergence_history: List[float]
    ) -> Any:
        """Run optimization in sequential mode."""
        import nevergrad as ng
        
        for i in range(config.budget):
            # Ask for candidate
            candidate = optimizer.ask()
            
            # Evaluate
            if isinstance(candidate, ng.p.Array):
                # Convert Array to dict
                params = candidate.value
                param_dict = dict(enumerate(params))
            else:
                param_dict = candidate.value if hasattr(candidate, 'value') else candidate
            
            # Handle parameterized case
            if hasattr(candidate, 'args') and hasattr(candidate, 'kwargs'):
                # This is a parameterized candidate
                try:
                    # Get the data from the parameterized object
                    data = candidate.args[0] if candidate.args else candidate.kwargs
                    if hasattr(data, '__iter__') and not isinstance(data, dict):
                        param_dict = dict(enumerate(data))
                    else:
                        param_dict = data if isinstance(data, dict) else {0: data}
                except:
                    param_dict = {0: candidate}
            else:
                param_dict = candidate if isinstance(candidate, dict) else {0: candidate}
            
            # Evaluate objective
            try:
                objective_value = objective_func(param_dict)
            except Exception as e:
                logger.warning(f"Objective evaluation failed: {e}")
                objective_value = float('inf')
            
            # Tell result to optimizer
            optimizer.tell(candidate, objective_value)
            
            # Track convergence
            convergence_history.append(objective_value)
            
            # Call callbacks
            if callbacks:
                for callback in callbacks:
                    try:
                        callback(i, param_dict, objective_value)
                    except Exception as e:
                        logger.warning(f"Callback failed: {e}")
            
            if config.verbosity > 0 and i % 100 == 0:
                logger.info(f"Iteration {i}: objective = {objective_value:.6f}")
        
        return optimizer.recommend()
    
    def _optimize_batch(
        self,
        optimizer,
        objective_func: Callable,
        config: OptimizationConfig,
        callbacks: Optional[List[Callable]],
        convergence_history: List[float]
    ) -> Any:
        """Run optimization in batch mode."""
        import nevergrad as ng
        
        batch_size = config.num_workers
        
        for batch_start in range(0, config.budget, batch_size):
            batch_end = min(batch_start + batch_size, config.budget)
            batch_size_actual = batch_end - batch_start
            
            # Ask for batch of candidates
            candidates = [optimizer.ask() for _ in range(batch_size_actual)]
            
            # Evaluate batch
            for candidate in candidates:
                if isinstance(candidate, ng.p.Array):
                    params = candidate.value
                    param_dict = dict(enumerate(params))
                else:
                    param_dict = candidate.value if hasattr(candidate, 'value') else candidate
                
                try:
                    objective_value = objective_func(param_dict)
                except Exception as e:
                    logger.warning(f"Objective evaluation failed: {e}")
                    objective_value = float('inf')
                
                optimizer.tell(candidate, objective_value)
                convergence_history.append(objective_value)
        
        return optimizer.recommend()
    
    def _extract_parameters(
        self,
        recommendation: Any,
        parameter_names: List[str]
    ) -> Dict[str, float]:
        """Extract parameter dictionary from recommendation."""
        if hasattr(recommendation, 'value'):
            value = recommendation.value
            if isinstance(value, tuple):
                args, kwargs = value
                # args is typically (data,) for parameterized
                if hasattr(args, '__iter__') and not isinstance(args, dict):
                    return dict(zip(parameter_names, args))
                elif isinstance(args, dict):
                    return args
                else:
                    return dict(zip(parameter_names, args)) if args else kwargs
            elif isinstance(value, dict):
                return value
            else:
                # Single parameter
                return {parameter_names[0]: float(value)} if parameter_names else {}
        elif isinstance(recommendation, dict):
            return recommendation
        else:
            return {parameter_names[0]: float(recommendation)} if parameter_names else {}
    
    def list_optimizers(self) -> List[str]:
        """List available optimizer names."""
        if self._ng is None:
            return []
        
        optimizers = [opt.value for opt in OptimizerType]
        return optimizers
    
    def get_optimizer_info(self, optimizer_name: str) -> Dict[str, Any]:
        """Get information about an optimizer."""
        info = {
            "name": optimizer_name,
            "type": "single-objective",
            "description": ""
        }
        
        if optimizer_name in ["NSGA2", "BO2A", "AggBounded"]:
            info["type"] = "multi-objective"
            info["description"] = "Multi-objective optimizer for Pareto optimization"
        elif optimizer_name in ["Portfolio", "CMAPortfolio"]:
            info["type"] = "portfolio"
            info["description"] = "Portfolio of optimizers"
        else:
            info["description"] = "Single-objective gradient-free optimizer"
        
        return info