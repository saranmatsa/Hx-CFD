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
        """Create optimizer instance based on study configuration."""
        # This would integrate with optimization libraries like Optuna, Nevergrad, etc.
        # For now, return a mock optimizer
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
        # This would integrate with the simulation service
        # For now, return mock results
        return {
            "objectives": {"drag": np.random.random(), "lift": np.random.random()},
            "constraints": {"max_pressure": np.random.random() * 1000},
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
        """Train surrogate model."""
        # This would integrate with scikit-learn, GPyTorch, etc.
        # For now, return mock results
        return {
            "model": None,
            "metrics": {
                "training_score": 0.95,
                "validation_score": 0.92,
                "feature_importance": {f"param_{i}": 1.0 / X.shape[1] for i in range(X.shape[1])},
            },
            "cv_scores": [0.9, 0.91, 0.93, 0.92, 0.94] if cross_validation else None,
            "training_time": 1.5,
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
        
        # Load model and predict
        # This would load the actual model and make predictions
        # For now, return mock predictions
        n_objectives = len(model.metrics.get("feature_importance", {}))
        
        predictions = {f"objective_{i}": np.random.random() for i in range(max(1, n_objectives))}
        
        result = {"predictions": predictions}
        if return_std:
            result["std_dev"] = {k: 0.01 for k in predictions}
        
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
        """Compute sensitivity indices."""
        # This would use SALib
        # For now, return mock results
        n_params = len(param_names)
        return {
            "S1": {param_names[i]: np.random.random() for i in range(n_params)},
            "ST": {param_names[i]: np.random.random() for i in range(n_params)},
            "S2": {f"{param_names[i]}_{param_names[j]}": np.random.random() 
                   for i in range(n_params) for j in range(i+1, n_params)},
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
        """Calculate hypervolume indicator."""
        # This would use a proper hypervolume calculation
        return np.random.random() * 100 if pareto_points else None
    
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
        """Generate DOE samples."""
        # This would use pyDOE, SALib, or similar
        # For now, return random samples
        param_names = list(param_space.keys())
        samples = []
        
        for _ in range(n_samples):
            sample = {}
            for param in param_names:
                p_info = param_space[param]
                if p_info.get("type") == "float":
                    sample[param] = np.random.uniform(p_info["low"], p_info["high"])
                elif p_info.get("type") == "int":
                    sample[param] = np.random.randint(p_info["low"], p_info["high"] + 1)
                elif p_info.get("type") == "categorical":
                    sample[param] = np.random.choice(p_info["choices"])
            samples.append(sample)
        
        return samples


class MockOptimizer:
    """Mock optimizer for testing."""
    
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