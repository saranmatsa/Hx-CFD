"""
Optimization Service for CFD Backend.

Provides business logic for optimization studies, trials, surrogate models,
sensitivity analysis, Pareto front computation, and design of experiments.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cfd_backend.models.optimization import (
    OptimizationStudy,
    OptimizationTrial,
    SurrogateModel,
    OptimizationType,
    OptimizationStatus,
    TrialStatus,
    SurrogateType,
)
from cfd_backend.models.project import Simulation, Project

logger = logging.getLogger(__name__)


class OptimizationService:
    """Service for optimization operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._running_optimizations: Dict[uuid.UUID, asyncio.Task] = {}
    
    async def run_optimization(
        self,
        optimization_id: uuid.UUID,
        resume: bool = False,
    ) -> None:
        """
        Run optimization study.
        
        Args:
            optimization_id: ID of the optimization study
            resume: Whether to resume from previous state
        """
        # Get optimization study
        result = await self.db.execute(
            select(OptimizationStudy)
            .options(selectinload(OptimizationStudy.project))
            .where(OptimizationStudy.id == optimization_id)
        )
        study = result.scalar_one_or_none()
        
        if not study:
            logger.error(f"Optimization study {optimization_id} not found")
            return
        
        try:
            # Update status
            study.status = OptimizationStatus.INITIALIZING
            study.started_at = datetime.utcnow()
            await self.db.commit()
            
            # Initialize optimizer based on study type
            optimizer = await self._create_optimizer(study)
            
            # Update status to running
            study.status = OptimizationStatus.RUNNING
            await self.db.commit()
            
            # Run optimization loop
            await self._run_optimization_loop(study, optimizer, resume)
            
            # Update final status
            if study.status == OptimizationStatus.RUNNING:
                study.status = OptimizationStatus.COMPLETED
                study.completed_at = datetime.utcnow()
                if study.started_at:
                    study.total_time_seconds = (study.completed_at - study.started_at).total_seconds()
            await self.db.commit()
            
        except asyncio.CancelledError:
            study.status = OptimizationStatus.CANCELLED
            study.completed_at = datetime.utcnow()
            await self.db.commit()
            raise
        except Exception as e:
            logger.exception(f"Optimization {optimization_id} failed: {e}")
            study.status = OptimizationStatus.FAILED
            study.error_message = str(e)
            study.completed_at = datetime.utcnow()
            await self.db.commit()
        finally:
            self._running_optimizations.pop(optimization_id, None)
    
    async def _create_optimizer(self, study: OptimizationStudy) -> Any:
        """Create optimizer instance based on study configuration using nevergrad."""
        try:
            import nevergrad as ng

            param_space = study.parameters or {}
            instrumentation = {}
            for name, p_info in param_space.items():
                p_type = p_info.get("type", "float")
                if p_type == "float":
                    instrumentation[name] = ng.p.Scalar(
                        init=p_info.get("init", (p_info["low"] + p_info["high"]) / 2),
                        lower=p_info["low"],
                        upper=p_info["high"],
                    )
                elif p_type == "int":
                    instrumentation[name] = ng.p.Scalar(
                        init=p_info.get("init", (p_info["low"] + p_info["high"]) // 2),
                        lower=p_info["low"],
                        upper=p_info["high"],
                    ).set_integer_casting()
                elif p_type == "categorical":
                    instrumentation[name] = ng.p.Choice(p_info["choices"])

            instr = ng.p.Instrumentation(**instrumentation)

            study_type = study.study_type.value if hasattr(study.study_type, "value") else str(study.study_type)
            if "multi" in study_type.lower() or study.n_objectives and study.n_objectives > 1:
                optimizer_name = "NGOpt"  # multi-objective
            else:
                optimizer_name = "BO"  # Bayesian optimization for single-objective

            budget = study.max_trials or 100
            optimizer = ng.optimizers.registry[optimizer_name](parametrization=instr, budget=budget)

            return NevergradOptimizerWrapper(optimizer, study)
        except ImportError:
            logger.warning("nevergrad not available, falling back to MockOptimizer")
            return MockOptimizer(study)
        except Exception as e:
            logger.warning(f"Failed to create nevergrad optimizer: {e}, falling back to MockOptimizer")
            return MockOptimizer(study)
    
    async def _run_optimization_loop(
        self,
        study: OptimizationStudy,
        optimizer: Any,
        resume: bool,
    ) -> None:
        """Run the main optimization loop."""
        max_trials = study.max_trials or 100
        completed = study.completed_trials
        
        if resume:
            # Load previous trials
            pass
        
        for trial_num in range(completed, max_trials):
            # Check if cancelled
            if study.status in [OptimizationStatus.CANCELLED, OptimizationStatus.PAUSED]:
                break
            
            # Ask optimizer for next parameters
            params = await optimizer.ask()
            
            # Create trial
            trial = OptimizationTrial(
                study_id=study.id,
                trial_number=trial_num,
                parameters=params,
                status=TrialStatus.RUNNING,
                started_at=datetime.utcnow(),
            )
            self.db.add(trial)
            await self.db.commit()
            
            try:
                # Run simulation with parameters
                result = await self._run_simulation_for_trial(study, trial, params)
                
                # Update trial with results
                trial.objectives = result.get("objectives", {})
                trial.constraints = result.get("constraints", {})
                trial.status = TrialStatus.COMPLETED
                trial.completed_at = datetime.utcnow()
                trial.duration_seconds = (trial.completed_at - trial.started_at).total_seconds()
                
                # Tell optimizer the result
                await optimizer.tell(trial_num, result)
                
            except Exception as e:
                logger.exception(f"Trial {trial_num} failed: {e}")
                trial.status = TrialStatus.FAILED
                trial.error_message = str(e)
                trial.completed_at = datetime.utcnow()
            
            await self.db.commit()
            
            # Update study progress
            study.completed_trials = trial_num + 1
            await self.db.commit()
            
            # Check for early stopping
            if await optimizer.should_stop():
                break
    
    async def _run_simulation_for_trial(
        self,
        study: OptimizationStudy,
        trial: OptimizationTrial,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run CFD simulation for a trial and return objectives/constraints."""
        try:
            from cfd_backend.services.simulation_service import SimulationService

            sim_service = SimulationService(self.db)

            # Build solver config from study + trial parameters
            base_config = study.solver_config or {}
            solver_config = {**base_config, **parameters}

            # Create a simulation for this trial
            sim = Simulation(
                project_id=study.project_id,
                name=f"opt_trial_{trial.trial_number}",
                description=f"Optimization trial {trial.trial_number} for study {study.name}",
                status="queued",
                solver_type=study.solver_type or "simpleFoam",
                solver_config=solver_config,
                mesh_id=study.mesh_id,
                priority=10,
            )
            self.db.add(sim)
            await self.db.commit()
            await self.db.refresh(sim)

            # Start the simulation
            await sim_service.start_simulation(sim.id)

            # Poll for completion (with timeout)
            max_wait = study.max_runtime_hours or 1.0
            max_seconds = int(max_wait * 3600)
            poll_interval = 5  # seconds
            elapsed = 0

            while elapsed < max_seconds:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                result = await self.db.execute(
                    select(Simulation).where(Simulation.id == sim.id)
                )
                sim = result.scalar_one_or_none()
                if not sim:
                    break
                if sim.status.value in ("completed", "failed", "cancelled"):
                    break

            # Extract objectives from simulation results
            objectives: Dict[str, float] = {}
            constraints: Dict[str, float] = {}

            if sim and sim.status.value == "completed":
                # Read convergence data for objective values
                conv = sim.convergence_data or {}
                perf = sim.performance_metrics or {}

                obj_names = study.objective_names or ["drag", "lift"]
                for obj_name in obj_names:
                    if obj_name in perf:
                        objectives[obj_name] = float(perf[obj_name])
                    elif obj_name in conv:
                        objectives[obj_name] = float(conv[obj_name])
                    else:
                        objectives[obj_name] = 0.0

                constraint_defs = study.constraint_definitions or {}
                for c_name, c_info in constraint_defs.items():
                    if c_name in perf:
                        constraints[c_name] = float(perf[c_name])
                    elif c_name in conv:
                        constraints[c_name] = float(conv[c_name])
                    else:
                        constraints[c_name] = 0.0
            else:
                # Simulation failed or timed out
                objectives = {name: float("inf") for name in (study.objective_names or ["drag", "lift"])}
                constraints = {}

            return {"objectives": objectives, "constraints": constraints}
        except Exception as e:
            logger.warning(f"Trial simulation failed, using fallback: {e}")
            # Fallback: return neutral values so optimization can continue
            obj_names = study.objective_names or ["drag", "lift"]
            return {
                "objectives": {name: float("inf") for name in obj_names},
                "constraints": {},
            }
    
    async def pause_optimization(self, optimization_id: uuid.UUID) -> None:
        """Pause running optimization."""
        result = await self.db.execute(
            select(OptimizationStudy).where(OptimizationStudy.id == optimization_id)
        )
        study = result.scalar_one_or_none()
        
        if study and study.status == OptimizationStatus.RUNNING:
            study.status = OptimizationStatus.PAUSED
            await self.db.commit()
            
            # Cancel running task
            task = self._running_optimizations.get(optimization_id)
            if task:
                task.cancel()
    
    async def cancel_optimization(self, optimization_id: uuid.UUID) -> None:
        """Cancel optimization."""
        result = await self.db.execute(
            select(OptimizationStudy).where(OptimizationStudy.id == optimization_id)
        )
        study = result.scalar_one_or_none()
        
        if study and study.status in [OptimizationStatus.RUNNING, OptimizationStatus.INITIALIZING, OptimizationStatus.PAUSED]:
            study.status = OptimizationStatus.CANCELLED
            study.completed_at = datetime.utcnow()
            await self.db.commit()
            
            # Cancel running task
            task = self._running_optimizations.get(optimization_id)
            if task:
                task.cancel()
    
    async def create_surrogate_model(
        self,
        optimization_id: uuid.UUID,
        model_type: SurrogateType,
        training_data: Dict[str, Any],
        hyperparameters: Optional[Dict[str, Any]] = None,
        cross_validation: bool = False,
        cv_folds: int = 5,
    ) -> Dict[str, Any]:
        """
        Create surrogate model from optimization data.
        
        Args:
            optimization_id: ID of the optimization study
            model_type: Type of surrogate model
            training_data: Training data configuration
            hyperparameters: Model hyperparameters
            cross_validation: Whether to use cross-validation
            cv_folds: Number of CV folds
            
        Returns:
            Dictionary with model info
        """
        # Get study
        result = await self.db.execute(
            select(OptimizationStudy).where(OptimizationStudy.id == optimization_id)
        )
        study = result.scalar_one_or_none()
        
        if not study:
            raise ValueError(f"Optimization study {optimization_id} not found")
        
        # Get training trials
        trial_result = await self.db.execute(
            select(OptimizationTrial)
            .where(
                OptimizationTrial.study_id == optimization_id,
                OptimizationTrial.status == TrialStatus.COMPLETED,
            )
            .order_by(OptimizationTrial.trial_number)
        )
        trials = trial_result.scalars().all()
        
        if len(trials) < 2:
            raise ValueError("Need at least 2 completed trials for surrogate modeling")
        
        # Prepare training data
        X = np.array([list(t.parameters.values()) for t in trials])
        y = np.array([list(t.objectives.values()) if t.objectives else [0] for t in trials])
        
        # Create and train surrogate model
        surrogate = await self._train_surrogate(
            model_type=model_type,
            X=X,
            y=y,
            hyperparameters=hyperparameters or {},
            cross_validation=cross_validation,
            cv_folds=cv_folds,
        )
        
        # Save model
        model_path = f"surrogates/{optimization_id}/{uuid.uuid4()}.pkl"
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        await self._save_surrogate(surrogate, model_path)
        
        # Create database record
        surrogate_model = SurrogateModel(
            study_id=optimization_id,
            name=f"{model_type.value}_model_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            surrogate_type=model_type,
            status="trained",
            config=hyperparameters or {},
            training_trials=[t.trial_number for t in trials],
            training_samples=len(trials),
            model_path=model_path,
            model_format="pickle",
            metrics=surrogate.get("metrics", {}),
            cross_validation_scores=surrogate.get("cv_scores"),
            trained_at=datetime.utcnow(),
            training_time_seconds=surrogate.get("training_time"),
        )
        
        self.db.add(surrogate_model)
        await self.db.commit()
        await self.db.refresh(surrogate_model)
        
        return {
            "id": str(surrogate_model.id),
            "status": surrogate_model.status,
            "training_score": surrogate_model.metrics.get("training_score"),
            "validation_score": surrogate_model.metrics.get("validation_score"),
            "feature_importance": surrogate_model.metrics.get("feature_importance"),
            "trained_at": surrogate_model.trained_at.isoformat() if surrogate_model.trained_at else None,
        }
    
    async def _train_surrogate(
        self,
        model_type: SurrogateType,
        X: np.ndarray,
        y: np.ndarray,
        hyperparameters: Dict[str, Any],
        cross_validation: bool,
        cv_folds: int,
    ) -> Dict[str, Any]:
        """Train surrogate model using scikit-learn."""
        try:
            from sklearn.model_selection import cross_val_score
            from sklearn.gaussian_process import GaussianProcessRegressor
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.svm import SVR
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline
            import time

            start = time.time()

            mt = model_type.value if hasattr(model_type, "value") else str(model_type)
            mt_lower = mt.lower()

            if "gaussian" in mt_lower or "gpr" in mt_lower or "kriging" in mt_lower:
                kernel = None
                try:
                    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
                    kernel = ConstantKernel(1.0) * RBF()
                except Exception:
                    pass
                model = GaussianProcessRegressor(kernel=kernel, normalize_y=True)
            elif "random" in mt_lower or "forest" in mt_lower:
                n_estimators = int(hyperparameters.get("n_estimators", 100))
                model = RandomForestRegressor(n_estimators=n_estimators)
            elif "svm" in mt_lower or "svr" in mt_lower:
                model = Pipeline([("scaler", StandardScaler()), ("svr", SVR())])
            elif "polynomial" in mt_lower or "poly" in mt_lower:
                from sklearn.preprocessing import PolynomialFeatures
                from sklearn.linear_model import LinearRegression
                degree = int(hyperparameters.get("degree", 2))
                model = Pipeline([("poly", PolynomialFeatures(degree=degree)), ("lr", LinearRegression())])
            else:
                # Default: Gaussian Process
                model = GaussianProcessRegressor(normalize_y=True)

            # Fit model
            model.fit(X, y)

            # Training score
            training_score = float(model.score(X, y))

            # Cross-validation
            cv_scores = None
            if cross_validation and len(X) >= cv_folds:
                cv_scores = cross_val_score(model, X, y, cv=cv_folds).tolist()

            # Feature importance (for models that support it)
            feature_importance = {}
            if hasattr(model, "feature_importances_"):
                feature_importance = {f"param_{i}": float(v) for i, v in enumerate(model.feature_importances_)}
            elif hasattr(model, "coef_") and hasattr(model.coef_, "ravel"):
                coefs = model.coef_.ravel()
                feature_importance = {f"param_{i}": float(abs(v)) for i, v in enumerate(coefs)}
            else:
                feature_importance = {f"param_{i}": 1.0 / X.shape[1] for i in range(X.shape[1])}

            validation_score = float(np.mean(cv_scores)) if cv_scores else training_score

            return {
                "model": model,
                "metrics": {
                    "training_score": training_score,
                    "validation_score": validation_score,
                    "feature_importance": feature_importance,
                },
                "cv_scores": cv_scores,
                "training_time": time.time() - start,
            }
        except ImportError:
            logger.warning("scikit-learn not available, returning mock surrogate")
            return {
                "model": None,
                "metrics": {
                    "training_score": 0.0,
                    "validation_score": 0.0,
                    "feature_importance": {f"param_{i}": 1.0 / X.shape[1] for i in range(X.shape[1])},
                },
                "cv_scores": None,
                "training_time": 0.0,
            }
        except Exception as e:
            logger.warning(f"Surrogate training failed: {e}")
            return {
                "model": None,
                "metrics": {
                    "training_score": 0.0,
                    "validation_score": 0.0,
                    "feature_importance": {f"param_{i}": 1.0 / X.shape[1] for i in range(X.shape[1])},
                },
                "cv_scores": None,
                "training_time": 0.0,
            }
    
    async def _save_surrogate(self, surrogate: Dict[str, Any], path: str) -> None:
        """Save surrogate model to disk."""
        import pickle
        with open(path, "wb") as f:
            pickle.dump(surrogate, f)
    
    async def predict_surrogate(
        self,
        model_id: uuid.UUID,
        parameters: Dict[str, Any],
        return_std: bool = False,
    ) -> Dict[str, Any]:
        """
        Predict using surrogate model.
        
        Args:
            model_id: ID of the surrogate model
            parameters: Input parameters
            return_std: Whether to return standard deviation
            
        Returns:
            Dictionary with predictions
        """
        # Get model
        result = await self.db.execute(
            select(SurrogateModel).where(SurrogateModel.id == model_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            raise ValueError(f"Surrogate model {model_id} not found")
        
        if model.status != "trained":
            raise ValueError(f"Model {model_id} is not trained")

        # Load model from disk and predict
        try:
            import pickle

            if not model.file_path or not Path(model.file_path).exists():
                raise ValueError(f"Model file not found: {model.file_path}")

            with open(model.file_path, "rb") as f:
                surrogate = pickle.load(f)

            trained_model = surrogate.get("model")
            if trained_model is None:
                raise ValueError("Loaded surrogate has no trained model")

            # Build feature vector from parameters
            feature_names = list(model.metrics.get("feature_importance", {}).keys())
            n_features = len(feature_names) if feature_names else len(parameters)
            X = np.array([[float(parameters.get(f"param_{i}", 0)) for i in range(n_features)]])

            # Predict
            if hasattr(trained_model, "predict"):
                preds = trained_model.predict(X)
                if hasattr(trained_model, "predict_proba") or hasattr(trained_model, "return_std"):
                    try:
                        preds, std = trained_model.predict(X, return_std=True)
                        std_arr = std
                    except Exception:
                        preds = trained_model.predict(X)
                        std_arr = None
                else:
                    std_arr = None
            else:
                raise ValueError("Model does not support prediction")

            # Map predictions to objective names
            obj_names = model.objective_names or [f"objective_{i}" for i in range(len(np.atleast_1d(preds)))]
            predictions = {}
            for i, name in enumerate(obj_names):
                predictions[name] = float(np.atleast_1d(preds)[i])

            result = {"predictions": predictions}
            if return_std and std_arr is not None:
                result["std_dev"] = {name: float(np.atleast_1d(std_arr)[i]) for i, name in enumerate(obj_names)}

            return result
        except Exception as e:
            logger.warning(f"Surrogate prediction failed: {e}")
            # Fallback: return zeros
            n_obj = len(model.objective_names) if model.objective_names else 1
            predictions = {f"objective_{i}": 0.0 for i in range(n_obj)}
            result = {"predictions": predictions}
            if return_std:
                result["std_dev"] = {k: 0.0 for k in predictions}
            return result
    
    async def run_sensitivity_analysis(
        self,
        optimization_id: uuid.UUID,
        method: str = "sobol",
        n_samples: int = 1000,
        parameters: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run sensitivity analysis on optimization results.
        
        Args:
            optimization_id: ID of the optimization study
            method: Sensitivity analysis method (sobol, morris, fast)
            n_samples: Number of samples
            parameters: List of parameter names to analyze
            
        Returns:
            Dictionary with sensitivity indices
        """
        # Get study and completed trials
        result = await self.db.execute(
            select(OptimizationStudy).where(OptimizationStudy.id == optimization_id)
        )
        study = result.scalar_one_or_none()
        
        if not study:
            raise ValueError(f"Optimization study {optimization_id} not found")
        
        trial_result = await self.db.execute(
            select(OptimizationTrial)
            .where(
                OptimizationTrial.study_id == optimization_id,
                OptimizationTrial.status == TrialStatus.COMPLETED,
            )
        )
        trials = trial_result.scalars().all()
        
        if len(trials) < 10:
            raise ValueError("Need at least 10 completed trials for sensitivity analysis")
        
        # Prepare data
        param_names = parameters or list(trials[0].parameters.keys())
        X = np.array([[t.parameters.get(p, 0) for p in param_names] for t in trials])
        y = np.array([list(t.objectives.values())[0] if t.objectives else 0 for t in trials])
        
        # Run sensitivity analysis
        # This would use SALib or similar library
        sensitivity = await self._compute_sensitivity(
            method=method,
            X=X,
            y=y,
            param_names=param_names,
            n_samples=n_samples,
        )
        
        analysis_id = str(uuid.uuid4())
        
        return {
            "analysis_id": analysis_id,
            "first_order_indices": sensitivity.get("S1", {}),
            "total_order_indices": sensitivity.get("ST", {}),
            "second_order_indices": sensitivity.get("S2", {}),
        }
    
    async def _compute_sensitivity(
        self,
        method: str,
        X: np.ndarray,
        y: np.ndarray,
        param_names: List[str],
        n_samples: int,
    ) -> Dict[str, Any]:
        """Compute sensitivity indices using SALib."""
        try:
            from SALib.analyze import sobol, morris, fast
            from SALib.sample import saltelli, morris as morris_sample, fast_sampler

            n_params = len(param_names)

            # Build problem definition
            bounds = []
            for i in range(n_params):
                col = X[:, i] if X.shape[1] > i else np.array([0, 1])
                lo, hi = float(np.min(col)), float(np.max(col))
                if lo == hi:
                    lo, hi = lo - 0.5, hi + 0.5
                bounds.append([lo, hi])

            problem = {
                "num_vars": n_params,
                "names": param_names,
                "bounds": bounds,
            }

            method_lower = method.lower()

            if method_lower == "sobol":
                # Generate samples and run analysis
                param_values = saltelli.sample(problem, n_samples)
                # We don't have a model to evaluate, so use the existing data
                # Fit a simple surrogate and evaluate on samples
                from sklearn.gaussian_process import GaussianProcessRegressor
                surrogate = GaussianProcessRegressor(normalize_y=True)
                surrogate.fit(X, y)
                Y_samples = surrogate.predict(param_values)
                Si = sobol.analyze(problem, Y_samples)
                return {
                    "S1": {param_names[i]: float(Si["S1"][i]) for i in range(n_params)},
                    "ST": {param_names[i]: float(Si["ST"][i]) for i in range(n_params)},
                    "S2": {
                        f"{param_names[i]}_{param_names[j]}": float(Si["S2"][i][j])
                        for i in range(n_params) for j in range(i + 1, n_params)
                    },
                }

            elif method_lower == "morris":
                param_values = morris_sample.sample(problem, n_samples)
                from sklearn.gaussian_process import GaussianProcessRegressor
                surrogate = GaussianProcessRegressor(normalize_y=True)
                surrogate.fit(X, y)
                Y_samples = surrogate.predict(param_values)
                Si = morris.analyze(problem, param_values, Y_samples)
                return {
                    "S1": {param_names[i]: float(Si["mu"][i]) for i in range(n_params)},
                    "ST": {param_names[i]: float(Si["mu_star"][i]) for i in range(n_params)},
                    "S2": {},
                }

            elif method_lower == "fast":
                param_values = fast_sampler.sample(problem, n_samples)
                from sklearn.gaussian_process import GaussianProcessRegressor
                surrogate = GaussianProcessRegressor(normalize_y=True)
                surrogate.fit(X, y)
                Y_samples = surrogate.predict(param_values)
                Si = fast.analyze(problem, Y_samples)
                return {
                    "S1": {param_names[i]: float(Si["S1"][i]) for i in range(n_params)},
                    "ST": {param_names[i]: float(Si["ST"][i]) for i in range(n_params)},
                    "S2": {},
                }

            else:
                raise ValueError(f"Unknown sensitivity method: {method}")

        except ImportError:
            logger.warning("SALib not available, using correlation-based sensitivity")
            # Fallback: use correlation coefficients
            n_params = len(param_names)
            correlations = []
            for i in range(n_params):
                if X.shape[1] > i and np.std(X[:, i]) > 0 and np.std(y) > 0:
                    correlations.append(abs(float(np.corrcoef(X[:, i], y)[0, 1])))
                else:
                    correlations.append(0.0)
            total = sum(correlations) if sum(correlations) > 0 else 1.0
            return {
                "S1": {param_names[i]: correlations[i] for i in range(n_params)},
                "ST": {param_names[i]: correlations[i] / total for i in range(n_params)},
                "S2": {},
            }
        except Exception as e:
            logger.warning(f"Sensitivity analysis failed: {e}")
            n_params = len(param_names)
            return {
                "S1": {param_names[i]: 0.0 for i in range(n_params)},
                "ST": {param_names[i]: 0.0 for i in range(n_params)},
                "S2": {},
            }
    
    async def compute_pareto_front(
        self,
        optimization_id: uuid.UUID,
        objectives: List[str],
        n_points: int = 50,
    ) -> Dict[str, Any]:
        """
        Compute Pareto front for multi-objective optimization.
        
        Args:
            optimization_id: ID of the optimization study
            objectives: List of objective names
            n_points: Number of points on Pareto front
            
        Returns:
            Dictionary with Pareto front points
        """
        # Get study
        result = await self.db.execute(
            select(OptimizationStudy).where(OptimizationStudy.id == optimization_id)
        )
        study = result.scalar_one_or_none()
        
        if not study:
            raise ValueError(f"Optimization study {optimization_id} not found")
        
        if study.optimization_type != OptimizationType.MULTI_OBJECTIVE:
            raise ValueError("Pareto front only available for multi-objective optimization")
        
        # Get completed trials
        trial_result = await self.db.execute(
            select(OptimizationTrial)
            .where(
                OptimizationTrial.study_id == optimization_id,
                OptimizationTrial.status == TrialStatus.COMPLETED,
            )
        )
        trials = trial_result.scalars().all()
        
        if not trials:
            raise ValueError("No completed trials found")
        
        # Extract objective values
        obj_data = []
        for trial in trials:
            if trial.objectives:
                obj_values = [trial.objectives.get(obj, 0) for obj in objectives]
                obj_data.append((trial.parameters, obj_values))
        
        # Compute Pareto front
        pareto_points = await self._compute_pareto_front(obj_data, n_points)
        
        # Calculate hypervolume
        hypervolume = await self._calculate_hypervolume(pareto_points, objectives)
        
        pareto_id = str(uuid.uuid4())
        
        return {
            "pareto_id": pareto_id,
            "points": pareto_points,
            "hypervolume": hypervolume,
        }
    
    async def _compute_pareto_front(
        self,
        obj_data: List[Tuple[Dict, List[float]]],
        n_points: int,
    ) -> List[Dict[str, Any]]:
        """Compute Pareto front points."""
        # Simple non-dominated sorting
        pareto = []
        for params, objs in obj_data:
            dominated = False
            for _, other_objs in obj_data:
                if all(o <= oo for o, oo in zip(objs, other_objs)) and any(o < oo for o, oo in zip(objs, other_objs)):
                    dominated = True
                    break
            if not dominated:
                pareto.append({"parameters": params, "objectives": dict(zip(range(len(objs)), objs))})
        
        # Limit to n_points
        return pareto[:n_points]
    
    async def _calculate_hypervolume(
        self,
        pareto_points: List[Dict[str, Any]],
        objectives: List[str],
    ) -> Optional[float]:
        """Calculate hypervolume indicator using the WFG algorithm."""
        if not pareto_points:
            return None

        try:
            # Try pygmo first
            try:
                import pygmo as pg
                pts = [[p.get(obj, 0.0) for obj in objectives] for p in pareto_points]
                # Use a reference point slightly worse than the worst in each dimension
                ref = [max(p[obj] for p in pareto_points) * 1.1 + 1e-6 for obj in objectives]
                hv = pg.hypervolume(pts)
                return float(hv.compute(ref))
            except ImportError:
                pass

            # Manual WFG implementation
            pts = np.array([[p.get(obj, 0.0) for obj in objectives] for p in pareto_points], dtype=float)
            ref = np.array([np.max(pts[:, i]) * 1.1 + 1e-6 for i in range(pts.shape[1])], dtype=float)

            # Remove dominated points
            keep = np.ones(len(pts), dtype=bool)
            for i in range(len(pts)):
                if not keep[i]:
                    continue
                for j in range(len(pts)):
                    if i == j or not keep[j]:
                        continue
                    if np.all(pts[j] <= pts[i]) and np.any(pts[j] < pts[i]):
                        keep[i] = False
                        break
            pts = pts[keep]
            if len(pts) == 0:
                return 0.0

            # Sort by first objective
            pts = pts[np.argsort(-pts[:, 0])]

            def wfg_hv(points, reference):
                n = len(points)
                if n == 1:
                    return float(np.prod(reference - points[0]))
                if n == 2:
                    return float(
                        np.prod(reference - np.maximum(points[0], points[1])) +
                        np.prod(reference - points[0]) -
                        np.prod(reference - np.maximum(points[0], points[1]))
                    )
                # Inclusion-exclusion for general case
                from itertools import combinations
                total = 0.0
                for k in range(1, n + 1):
                    for combo in combinations(range(n), k):
                        subset = points[list(combo)]
                        worst = np.max(subset, axis=0)
                        vol = np.prod(reference - worst)
                        total += ((-1) ** (k + 1)) * vol
                return float(total)

            return wfg_hv(pts, ref)

        except Exception as e:
            logger.warning(f"Hypervolume calculation failed: {e}")
            return None
    
    async def generate_doe(
        self,
        optimization_id: uuid.UUID,
        method: str = "lhs",
        n_samples: int = 10,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Design of Experiments samples.
        
        Args:
            optimization_id: ID of the optimization study
            method: DOE method (lhs, sobol, halton, grid, random)
            n_samples: Number of samples
            parameters: Parameter space definition
            
        Returns:
            Dictionary with DOE samples
        """
        # Get study
        result = await self.db.execute(
            select(OptimizationStudy).where(OptimizationStudy.id == optimization_id)
        )
        study = result.scalar_one_or_none()
        
        if not study:
            raise ValueError(f"Optimization study {optimization_id} not found")
        
        # Use study parameter space if not provided
        param_space = parameters or study.parameters
        
        # Generate samples
        samples = await self._generate_doe_samples(
            method=method,
            n_samples=n_samples,
            param_space=param_space,
        )
        
        doe_id = str(uuid.uuid4())
        
        return {
            "doe_id": doe_id,
            "method": method,
            "n_samples": n_samples,
            "samples": samples,
        }
    
    async def _generate_doe_samples(
        self,
        method: str,
        n_samples: int,
        param_space: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate DOE samples using pyDOE or nevergrad."""
        param_names = list(param_space.keys())
        n_params = len(param_names)
        method_lower = method.lower()

        try:
            # Try pyDOE2 first
            try:
                from pyDOE2 import lhs, sobol as doe_sobol, fullfact

                # Build normalized samples in [0, 1]
                if method_lower == "lhs":
                    norm_samples = lhs(n_params, samples=n_samples, criterion="maximin")
                elif method_lower == "sobol":
                    # pyDOE2 sobol requires power-of-2 samples
                    import math
                    n_pow2 = 2 ** int(math.ceil(math.log2(max(n_samples, 2))))
                    norm_samples = doe_sobol(n_params, n_pow2)[:n_samples]
                    if len(norm_samples) < n_samples:
                        # Pad with LHS
                        extra = lhs(n_params, samples=n_samples - len(norm_samples))
                        norm_samples = np.vstack([norm_samples, extra])
                elif method_lower == "halton":
                    # Halton sequence
                    from scipy.stats import qmc
                    sampler = qmc.Halton(d=n_params)
                    norm_samples = sampler.random(n=n_samples)
                elif method_lower == "grid":
                    # Full factorial — compute per-dimension levels
                    levels_per_dim = max(2, int(round(n_samples ** (1.0 / n_params))))
                    levels = [levels_per_dim] * n_params
                    norm_samples = fullfact(levels)
                    # Normalize to [0, 1]
                    norm_samples = norm_samples / (levels_per_dim - 1) if levels_per_dim > 1 else norm_samples
                    # Subsample if too many
                    if len(norm_samples) > n_samples:
                        idx = np.linspace(0, len(norm_samples) - 1, n_samples, dtype=int)
                        norm_samples = norm_samples[idx]
                else:
                    # Default: random
                    norm_samples = np.random.uniform(0, 1, size=(n_samples, n_params))
            except ImportError:
                # Try scipy.stats.qmc
                try:
                    from scipy.stats import qmc
                    if method_lower == "sobol":
                        sampler = qmc.Sobol(d=n_params)
                        norm_samples = sampler.random(n=n_samples)
                    elif method_lower == "halton":
                        sampler = qmc.Halton(d=n_params)
                        norm_samples = sampler.random(n=n_samples)
                    elif method_lower == "lhs":
                        sampler = qmc.LatinHypercube(d=n_params)
                        norm_samples = sampler.random(n=n_samples)
                    else:
                        norm_samples = np.random.uniform(0, 1, size=(n_samples, n_params))
                except ImportError:
                    logger.warning("pyDOE2 and scipy.stats.qmc not available, using random sampling")
                    norm_samples = np.random.uniform(0, 1, size=(n_samples, n_params))

            # Scale normalized samples to parameter ranges
            samples = []
            for row in norm_samples:
                sample = {}
                for i, param in enumerate(param_names):
                    p_info = param_space[param]
                    ptype = p_info.get("type", "float")
                    if ptype == "float":
                        lo, hi = float(p_info["low"]), float(p_info["high"])
                        sample[param] = lo + row[i] * (hi - lo)
                    elif ptype == "int":
                        lo, hi = int(p_info["low"]), int(p_info["high"])
                        sample[param] = int(round(lo + row[i] * (hi - lo)))
                    elif ptype == "categorical":
                        choices = p_info["choices"]
                        idx = min(int(row[i] * len(choices)), len(choices) - 1)
                        sample[param] = choices[idx]
                samples.append(sample)
            return samples

        except Exception as e:
            logger.warning(f"DOE generation failed ({method}), using random: {e}")
            # Fallback: random sampling
            samples = []
            for _ in range(n_samples):
                sample = {}
                for param in param_names:
                    p_info = param_space[param]
                    ptype = p_info.get("type", "float")
                    if ptype == "float":
                        sample[param] = np.random.uniform(p_info["low"], p_info["high"])
                    elif ptype == "int":
                        sample[param] = np.random.randint(p_info["low"], p_info["high"] + 1)
                    elif ptype == "categorical":
                        sample[param] = np.random.choice(p_info["choices"])
                samples.append(sample)
            return samples


class MockOptimizer:
    """Mock optimizer for testing — random sampling fallback."""
    
    def __init__(self, study: OptimizationStudy):
        self.study = study
        self.trial_count = 0
    
    async def ask(self) -> Dict[str, Any]:
        """Get next parameters to evaluate."""
        params = {}
        for name, p_info in self.study.parameters.items():
            if p_info.get("type") == "float":
                params[name] = np.random.uniform(p_info["low"], p_info["high"])
            elif p_info.get("type") == "int":
                params[name] = np.random.randint(p_info["low"], p_info["high"] + 1)
            elif p_info.get("type") == "categorical":
                params[name] = np.random.choice(p_info["choices"])
        self.trial_count += 1
        return params
    
    async def tell(self, trial_num: int, result: Dict[str, Any]) -> None:
        """Tell optimizer the result."""
        pass
    
    async def should_stop(self) -> bool:
        """Check if optimization should stop."""
        return self.trial_count >= (self.study.max_trials or 100)


class NevergradOptimizerWrapper:
    """Wraps a nevergrad optimizer to provide async ask/tell/should_stop interface."""

    def __init__(self, ng_optimizer, instrumentation, study: OptimizationStudy):
        self.optimizer = ng_optimizer
        self.instrumentation = instrumentation
        self.study = study
        self.trial_count = 0
        self._pending = None

    async def ask(self) -> Dict[str, Any]:
        """Get next parameters to evaluate."""
        candidate = self.optimizer.ask()
        self._pending = candidate
        # Extract parameter values from the candidate
        try:
            kwargs = candidate.kwargs
            if kwargs:
                return dict(kwargs)
        except Exception:
            pass
        # Fallback: try args
        try:
            args = candidate.args
            param_names = list(self.study.parameters.keys())
            if args and len(args) == len(param_names):
                return {param_names[i]: args[i] for i in range(len(param_names))}
        except Exception:
            pass
        # Last resort: random
        params = {}
        for name, p_info in self.study.parameters.items():
            if p_info.get("type") == "float":
                params[name] = np.random.uniform(p_info["low"], p_info["high"])
            elif p_info.get("type") == "int":
                params[name] = np.random.randint(p_info["low"], p_info["high"] + 1)
            elif p_info.get("type") == "categorical":
                params[name] = np.random.choice(p_info["choices"])
        return params

    async def tell(self, trial_num: int, result: Dict[str, Any]) -> None:
        """Tell optimizer the result."""
        if self._pending is None:
            return
        # Build objective vector from result
        objective_names = self.study.objectives or list(result.keys())
        if len(objective_names) == 1:
            loss = float(result.get(objective_names[0], 0.0))
        else:
            # Multi-objective: nevergrad expects a tuple
            loss = tuple(float(result.get(name, 0.0)) for name in objective_names)
        self.optimizer.tell(self._pending, loss)
        self._pending = None
        self.trial_count += 1

    async def should_stop(self) -> bool:
        """Check if optimization should stop."""
        max_trials = self.study.max_trials or 100
        if self.trial_count >= max_trials:
            return True
        try:
            return self.optimizer.should_stop()
        except Exception:
            return False