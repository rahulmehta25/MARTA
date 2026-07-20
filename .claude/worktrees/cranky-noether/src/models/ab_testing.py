"""
A/B Testing Framework for MARTA ML Models

This module implements a comprehensive A/B testing framework for comparing
ML model performance, conducting statistical tests, and managing experiments.
"""
import os
import logging
import json
import hashlib
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import asyncpg
from pydantic import BaseModel, Field
import mlflow
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from src.models.ml_experiment_tracker import get_experiment_tracker

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """Experiment status enumeration."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class TrafficSplitStrategy(Enum):
    """Traffic split strategies."""
    RANDOM = "random"
    USER_ID_HASH = "user_id_hash"
    GEOGRAPHIC = "geographic"
    TIME_BASED = "time_based"
    FEATURE_BASED = "feature_based"


@dataclass
class ExperimentConfig:
    """Configuration for A/B testing experiment."""
    experiment_id: str
    name: str
    description: str
    model_a: str  # Control model
    model_b: str  # Treatment model
    traffic_split: float = 0.5  # Fraction going to model B
    split_strategy: TrafficSplitStrategy = TrafficSplitStrategy.RANDOM
    success_metrics: List[str] = field(default_factory=lambda: ["mae", "rmse", "r2"])
    minimum_sample_size: int = 1000
    confidence_level: float = 0.95
    power: float = 0.8
    effect_size: float = 0.05  # Minimum detectable effect
    max_duration_days: int = 30
    early_stopping: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"


@dataclass
class ExperimentResult:
    """Results from A/B testing experiment."""
    timestamp: datetime
    model_name: str
    prediction: float
    actual: Optional[float]
    features: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StatisticalAnalyzer:
    """
    Statistical analysis for A/B testing results.
    
    Features:
    - Statistical significance testing
    - Power analysis
    - Effect size calculation
    - Confidence intervals
    - Multiple testing correction
    """
    
    def __init__(self, confidence_level: float = 0.95):
        """
        Initialize statistical analyzer.
        
        Args:
            confidence_level: Confidence level for statistical tests
        """
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level
        
    def t_test(self, 
               sample_a: np.ndarray, 
               sample_b: np.ndarray,
               alternative: str = 'two-sided') -> Dict[str, Any]:
        """
        Perform t-test between two samples.
        
        Args:
            sample_a: Control group samples
            sample_b: Treatment group samples  
            alternative: Alternative hypothesis ('two-sided', 'less', 'greater')
            
        Returns:
            Dictionary with test results
        """
        # Check for sufficient sample sizes
        if len(sample_a) < 30 or len(sample_b) < 30:
            logger.warning("Small sample sizes may affect test reliability")
        
        # Perform Welch's t-test (assumes unequal variances)
        statistic, p_value = stats.ttest_ind(
            sample_a, sample_b, 
            equal_var=False, 
            alternative=alternative
        )
        
        # Calculate effect size (Cohen's d)
        pooled_std = np.sqrt(((len(sample_a) - 1) * np.var(sample_a, ddof=1) + 
                             (len(sample_b) - 1) * np.var(sample_b, ddof=1)) / 
                            (len(sample_a) + len(sample_b) - 2))
        
        effect_size = (np.mean(sample_b) - np.mean(sample_a)) / pooled_std
        
        # Calculate confidence interval for the difference in means
        se_diff = np.sqrt(np.var(sample_a, ddof=1)/len(sample_a) + 
                         np.var(sample_b, ddof=1)/len(sample_b))
        
        dof = len(sample_a) + len(sample_b) - 2
        t_critical = stats.t.ppf(1 - self.alpha/2, dof)
        
        mean_diff = np.mean(sample_b) - np.mean(sample_a)
        ci_lower = mean_diff - t_critical * se_diff
        ci_upper = mean_diff + t_critical * se_diff
        
        return {
            'statistic': float(statistic),
            'p_value': float(p_value),
            'significant': p_value < self.alpha,
            'effect_size': float(effect_size),
            'mean_a': float(np.mean(sample_a)),
            'mean_b': float(np.mean(sample_b)),
            'std_a': float(np.std(sample_a, ddof=1)),
            'std_b': float(np.std(sample_b, ddof=1)),
            'n_a': len(sample_a),
            'n_b': len(sample_b),
            'mean_difference': float(mean_diff),
            'ci_lower': float(ci_lower),
            'ci_upper': float(ci_upper),
            'confidence_level': self.confidence_level
        }
    
    def mann_whitney_test(self, 
                         sample_a: np.ndarray, 
                         sample_b: np.ndarray,
                         alternative: str = 'two-sided') -> Dict[str, Any]:
        """
        Perform Mann-Whitney U test (non-parametric alternative to t-test).
        
        Args:
            sample_a: Control group samples
            sample_b: Treatment group samples
            alternative: Alternative hypothesis
            
        Returns:
            Dictionary with test results
        """
        statistic, p_value = stats.mannwhitneyu(
            sample_a, sample_b,
            alternative=alternative
        )
        
        # Calculate effect size (r = Z / sqrt(N))
        z_score = stats.norm.ppf(1 - p_value/2) if alternative == 'two-sided' else stats.norm.ppf(1 - p_value)
        effect_size = z_score / np.sqrt(len(sample_a) + len(sample_b))
        
        return {
            'statistic': float(statistic),
            'p_value': float(p_value),
            'significant': p_value < self.alpha,
            'effect_size': float(effect_size),
            'median_a': float(np.median(sample_a)),
            'median_b': float(np.median(sample_b)),
            'n_a': len(sample_a),
            'n_b': len(sample_b),
            'test_type': 'mann_whitney'
        }
    
    def bootstrap_test(self, 
                      sample_a: np.ndarray, 
                      sample_b: np.ndarray,
                      n_bootstrap: int = 10000,
                      statistic_func: callable = np.mean) -> Dict[str, Any]:
        """
        Perform bootstrap hypothesis test.
        
        Args:
            sample_a: Control group samples
            sample_b: Treatment group samples  
            n_bootstrap: Number of bootstrap samples
            statistic_func: Function to calculate statistic
            
        Returns:
            Dictionary with test results
        """
        # Observed difference
        observed_diff = statistic_func(sample_b) - statistic_func(sample_a)
        
        # Bootstrap under null hypothesis (no difference)
        combined = np.concatenate([sample_a, sample_b])
        n_a, n_b = len(sample_a), len(sample_b)
        
        bootstrap_diffs = []
        
        for _ in range(n_bootstrap):
            # Resample from combined data
            resampled = np.random.choice(combined, size=len(combined), replace=True)
            
            # Split into two groups with original sizes
            boot_a = resampled[:n_a]
            boot_b = resampled[n_a:n_a+n_b]
            
            # Calculate difference
            boot_diff = statistic_func(boot_b) - statistic_func(boot_a)
            bootstrap_diffs.append(boot_diff)
        
        bootstrap_diffs = np.array(bootstrap_diffs)
        
        # Calculate p-value (two-tailed)
        p_value = 2 * min(
            np.mean(bootstrap_diffs >= observed_diff),
            np.mean(bootstrap_diffs <= observed_diff)
        )
        
        # Confidence interval for the difference
        ci_lower = np.percentile(bootstrap_diffs, (self.alpha/2) * 100)
        ci_upper = np.percentile(bootstrap_diffs, (1 - self.alpha/2) * 100)
        
        return {
            'observed_difference': float(observed_diff),
            'p_value': float(p_value),
            'significant': p_value < self.alpha,
            'ci_lower': float(ci_lower),
            'ci_upper': float(ci_upper),
            'bootstrap_samples': n_bootstrap,
            'test_type': 'bootstrap'
        }
    
    def power_analysis(self, 
                      effect_size: float,
                      sample_size_a: int,
                      sample_size_b: int,
                      alpha: float = None) -> Dict[str, Any]:
        """
        Perform power analysis for the experiment.
        
        Args:
            effect_size: Expected effect size (Cohen's d)
            sample_size_a: Sample size for group A
            sample_size_b: Sample size for group B
            alpha: Significance level (uses instance default if None)
            
        Returns:
            Dictionary with power analysis results
        """
        alpha = alpha or self.alpha
        
        # Calculate power using approximation
        n_harmonic = 2 * sample_size_a * sample_size_b / (sample_size_a + sample_size_b)
        
        # Non-centrality parameter
        ncp = effect_size * np.sqrt(n_harmonic / 2)
        
        # Critical value
        t_critical = stats.t.ppf(1 - alpha/2, sample_size_a + sample_size_b - 2)
        
        # Power calculation
        power = 1 - stats.nct.cdf(t_critical, sample_size_a + sample_size_b - 2, ncp) + \
                stats.nct.cdf(-t_critical, sample_size_a + sample_size_b - 2, ncp)
        
        return {
            'power': float(power),
            'effect_size': effect_size,
            'sample_size_a': sample_size_a,
            'sample_size_b': sample_size_b,
            'alpha': alpha,
            'adequate_power': power >= 0.8
        }
    
    def multiple_testing_correction(self, 
                                  p_values: List[float],
                                  method: str = 'bonferroni') -> Dict[str, Any]:
        """
        Apply multiple testing correction.
        
        Args:
            p_values: List of p-values
            method: Correction method ('bonferroni', 'holm', 'fdr_bh')
            
        Returns:
            Dictionary with corrected results
        """
        p_values = np.array(p_values)
        
        if method == 'bonferroni':
            corrected_p = p_values * len(p_values)
            corrected_p = np.minimum(corrected_p, 1.0)
        elif method == 'holm':
            sorted_indices = np.argsort(p_values)
            corrected_p = np.zeros_like(p_values)
            for i, idx in enumerate(sorted_indices):
                corrected_p[idx] = p_values[idx] * (len(p_values) - i)
        elif method == 'fdr_bh':
            sorted_indices = np.argsort(p_values)
            corrected_p = np.zeros_like(p_values)
            for i, idx in enumerate(sorted_indices):
                corrected_p[idx] = p_values[idx] * len(p_values) / (i + 1)
        else:
            raise ValueError(f"Unknown correction method: {method}")
        
        corrected_p = np.minimum(corrected_p, 1.0)
        
        return {
            'original_p_values': p_values.tolist(),
            'corrected_p_values': corrected_p.tolist(),
            'method': method,
            'significant_original': (p_values < self.alpha).tolist(),
            'significant_corrected': (corrected_p < self.alpha).tolist()
        }


class TrafficSplitter:
    """
    Traffic splitting for A/B testing.
    
    Features:
    - Multiple splitting strategies
    - Consistent assignment
    - Bias prevention
    - Assignment logging
    """
    
    def __init__(self, strategy: TrafficSplitStrategy = TrafficSplitStrategy.RANDOM):
        """
        Initialize traffic splitter.
        
        Args:
            strategy: Traffic splitting strategy
        """
        self.strategy = strategy
        
    def assign_variant(self, 
                      user_id: str,
                      traffic_split: float,
                      features: Dict[str, Any] = None,
                      experiment_id: str = None) -> str:
        """
        Assign user to variant (A or B).
        
        Args:
            user_id: User identifier
            traffic_split: Fraction of traffic going to variant B
            features: User features for feature-based splitting
            experiment_id: Experiment identifier for consistent hashing
            
        Returns:
            Variant assignment ('A' or 'B')
        """
        if self.strategy == TrafficSplitStrategy.RANDOM:
            return self._random_assignment(traffic_split)
        
        elif self.strategy == TrafficSplitStrategy.USER_ID_HASH:
            return self._hash_based_assignment(user_id, traffic_split, experiment_id)
        
        elif self.strategy == TrafficSplitStrategy.FEATURE_BASED:
            return self._feature_based_assignment(features, traffic_split)
        
        elif self.strategy == TrafficSplitStrategy.TIME_BASED:
            return self._time_based_assignment(traffic_split)
        
        else:
            # Default to random
            return self._random_assignment(traffic_split)
    
    def _random_assignment(self, traffic_split: float) -> str:
        """Random assignment."""
        return 'B' if np.random.random() < traffic_split else 'A'
    
    def _hash_based_assignment(self, 
                              user_id: str, 
                              traffic_split: float,
                              experiment_id: str = None) -> str:
        """Hash-based assignment for consistency."""
        # Create deterministic hash
        hash_input = f"{user_id}_{experiment_id}" if experiment_id else user_id
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # Normalize to [0, 1]
        normalized = (hash_value % 10000) / 10000.0
        
        return 'B' if normalized < traffic_split else 'A'
    
    def _feature_based_assignment(self, 
                                 features: Dict[str, Any], 
                                 traffic_split: float) -> str:
        """Feature-based assignment."""
        if not features:
            return self._random_assignment(traffic_split)
        
        # Simple feature-based assignment (can be made more sophisticated)
        feature_sum = sum(float(v) for v in features.values() if isinstance(v, (int, float)))
        normalized = (feature_sum % 1000) / 1000.0
        
        return 'B' if normalized < traffic_split else 'A'
    
    def _time_based_assignment(self, traffic_split: float) -> str:
        """Time-based assignment."""
        # Use current minute for assignment
        current_minute = datetime.now().minute
        normalized = current_minute / 60.0
        
        return 'B' if normalized < traffic_split else 'A'


class ABTestManager:
    """
    A/B testing experiment manager.
    
    Features:
    - Experiment lifecycle management
    - Statistical analysis
    - Results visualization
    - Database integration
    - Real-time monitoring
    """
    
    def __init__(self):
        """Initialize A/B test manager."""
        self.experiments: Dict[str, ExperimentConfig] = {}
        self.experiment_results: Dict[str, List[ExperimentResult]] = {}
        self.traffic_splitter = TrafficSplitter()
        self.analyzer = StatisticalAnalyzer()
        self.experiment_tracker = get_experiment_tracker()
        
        # Database connection
        self.db_pool = None
        
        logger.info("A/B test manager initialized")
    
    async def initialize_db_connection(self):
        """Initialize database connection."""
        try:
            connection_string = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            self.db_pool = await asyncpg.create_pool(connection_string, min_size=2, max_size=10)
            logger.info("Database connection pool initialized for A/B testing")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
    
    def create_experiment(self, config: ExperimentConfig) -> str:
        """
        Create new A/B testing experiment.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Experiment ID
        """
        # Validate configuration
        if config.traffic_split < 0 or config.traffic_split > 1:
            raise ValueError("Traffic split must be between 0 and 1")
        
        if config.minimum_sample_size < 100:
            logger.warning("Very small minimum sample size may lead to unreliable results")
        
        # Store experiment
        self.experiments[config.experiment_id] = config
        self.experiment_results[config.experiment_id] = []
        
        # Log to MLflow
        with self.experiment_tracker.start_run(
            run_name=f"ab_experiment_{config.experiment_id}",
            tags={
                "experiment_type": "ab_test",
                "model_a": config.model_a,
                "model_b": config.model_b
            }
        ) as run:
            mlflow.log_param("traffic_split", config.traffic_split)
            mlflow.log_param("split_strategy", config.split_strategy.value)
            mlflow.log_param("minimum_sample_size", config.minimum_sample_size)
            mlflow.log_param("confidence_level", config.confidence_level)
            mlflow.log_param("max_duration_days", config.max_duration_days)
        
        logger.info(f"Created experiment: {config.experiment_id}")
        return config.experiment_id
    
    def assign_to_variant(self, 
                         experiment_id: str,
                         user_id: str,
                         features: Dict[str, Any] = None) -> str:
        """
        Assign user to experiment variant.
        
        Args:
            experiment_id: Experiment identifier
            user_id: User identifier
            features: User features
            
        Returns:
            Assigned variant ('A' or 'B')
        """
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self.experiments[experiment_id]
        
        # Set traffic splitter strategy
        self.traffic_splitter.strategy = experiment.split_strategy
        
        variant = self.traffic_splitter.assign_variant(
            user_id=user_id,
            traffic_split=experiment.traffic_split,
            features=features,
            experiment_id=experiment_id
        )
        
        return variant
    
    def log_result(self, 
                  experiment_id: str,
                  variant: str,
                  prediction: float,
                  actual: Optional[float] = None,
                  features: Dict[str, Any] = None,
                  user_id: Optional[str] = None,
                  session_id: Optional[str] = None,
                  metadata: Dict[str, Any] = None) -> None:
        """
        Log experiment result.
        
        Args:
            experiment_id: Experiment identifier
            variant: Assigned variant
            prediction: Model prediction
            actual: Actual value (if available)
            features: Input features
            user_id: User identifier
            session_id: Session identifier
            metadata: Additional metadata
        """
        if experiment_id not in self.experiments:
            logger.warning(f"Logging result for unknown experiment: {experiment_id}")
            return
        
        result = ExperimentResult(
            timestamp=datetime.now(),
            model_name=variant,
            prediction=prediction,
            actual=actual,
            features=features or {},
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        self.experiment_results[experiment_id].append(result)
    
    def analyze_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        Analyze experiment results.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Analysis results
        """
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self.experiments[experiment_id]
        results = self.experiment_results[experiment_id]
        
        if len(results) < experiment.minimum_sample_size:
            return {
                "status": "insufficient_data",
                "current_samples": len(results),
                "minimum_required": experiment.minimum_sample_size
            }
        
        # Separate results by variant
        variant_a_results = [r for r in results if r.model_name == 'A']
        variant_b_results = [r for r in results if r.model_name == 'B']
        
        if not variant_a_results or not variant_b_results:
            return {
                "status": "insufficient_variants",
                "variant_a_count": len(variant_a_results),
                "variant_b_count": len(variant_b_results)
            }
        
        analysis = {
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "analysis_timestamp": datetime.now().isoformat(),
            "sample_sizes": {
                "variant_a": len(variant_a_results),
                "variant_b": len(variant_b_results),
                "total": len(results)
            },
            "metrics": {}
        }
        
        # Analyze each success metric
        for metric_name in experiment.success_metrics:
            try:
                metric_analysis = self._analyze_metric(
                    variant_a_results, variant_b_results, metric_name
                )
                analysis["metrics"][metric_name] = metric_analysis
            except Exception as e:
                logger.error(f"Failed to analyze metric {metric_name}: {e}")
                analysis["metrics"][metric_name] = {"error": str(e)}
        
        # Overall recommendation
        analysis["recommendation"] = self._make_recommendation(analysis)
        
        return analysis
    
    def _analyze_metric(self, 
                       variant_a_results: List[ExperimentResult],
                       variant_b_results: List[ExperimentResult],
                       metric_name: str) -> Dict[str, Any]:
        """Analyze a specific metric."""
        # Calculate metric values for each variant
        if metric_name == "mae":
            values_a = [abs(r.prediction - r.actual) for r in variant_a_results if r.actual is not None]
            values_b = [abs(r.prediction - r.actual) for r in variant_b_results if r.actual is not None]
        elif metric_name == "rmse":
            values_a = [(r.prediction - r.actual)**2 for r in variant_a_results if r.actual is not None]
            values_b = [(r.prediction - r.actual)**2 for r in variant_b_results if r.actual is not None]
            values_a = [np.sqrt(np.mean(values_a))] * len(values_a) if values_a else []
            values_b = [np.sqrt(np.mean(values_b))] * len(values_b) if values_b else []
        elif metric_name == "r2":
            # Calculate R² for each variant
            if len(variant_a_results) > 1:
                actual_a = [r.actual for r in variant_a_results if r.actual is not None]
                pred_a = [r.prediction for r in variant_a_results if r.actual is not None]
                r2_a = r2_score(actual_a, pred_a) if len(actual_a) > 1 else 0
            else:
                r2_a = 0
            
            if len(variant_b_results) > 1:
                actual_b = [r.actual for r in variant_b_results if r.actual is not None]
                pred_b = [r.prediction for r in variant_b_results if r.actual is not None]
                r2_b = r2_score(actual_b, pred_b) if len(actual_b) > 1 else 0
            else:
                r2_b = 0
            
            values_a = [r2_a] * len(variant_a_results)
            values_b = [r2_b] * len(variant_b_results)
        else:
            # Default: use predictions directly
            values_a = [r.prediction for r in variant_a_results]
            values_b = [r.prediction for r in variant_b_results]
        
        if not values_a or not values_b:
            return {"error": "Insufficient data for metric calculation"}
        
        values_a = np.array(values_a)
        values_b = np.array(values_b)
        
        # Perform statistical tests
        t_test_result = self.analyzer.t_test(values_a, values_b)
        mw_test_result = self.analyzer.mann_whitney_test(values_a, values_b)
        bootstrap_result = self.analyzer.bootstrap_test(values_a, values_b)
        
        # Power analysis
        effect_size = abs(t_test_result['effect_size'])
        power_result = self.analyzer.power_analysis(
            effect_size=effect_size,
            sample_size_a=len(values_a),
            sample_size_b=len(values_b)
        )
        
        return {
            "metric_name": metric_name,
            "descriptive_stats": {
                "variant_a": {
                    "mean": float(np.mean(values_a)),
                    "std": float(np.std(values_a, ddof=1)),
                    "median": float(np.median(values_a)),
                    "count": len(values_a)
                },
                "variant_b": {
                    "mean": float(np.mean(values_b)),
                    "std": float(np.std(values_b, ddof=1)),
                    "median": float(np.median(values_b)),
                    "count": len(values_b)
                }
            },
            "statistical_tests": {
                "t_test": t_test_result,
                "mann_whitney": mw_test_result,
                "bootstrap": bootstrap_result
            },
            "power_analysis": power_result
        }
    
    def _make_recommendation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Make recommendation based on analysis."""
        significant_metrics = []
        non_significant_metrics = []
        
        for metric_name, metric_analysis in analysis["metrics"].items():
            if "error" in metric_analysis:
                continue
            
            t_test = metric_analysis["statistical_tests"]["t_test"]
            if t_test["significant"]:
                significant_metrics.append({
                    "metric": metric_name,
                    "p_value": t_test["p_value"],
                    "effect_size": t_test["effect_size"],
                    "improvement": t_test["mean_b"] < t_test["mean_a"]  # Assuming lower is better
                })
            else:
                non_significant_metrics.append(metric_name)
        
        # Decision logic
        if len(significant_metrics) > len(non_significant_metrics):
            if all(m["improvement"] for m in significant_metrics):
                decision = "deploy_variant_b"
                confidence = "high"
            elif any(m["improvement"] for m in significant_metrics):
                decision = "mixed_results"
                confidence = "medium"
            else:
                decision = "keep_variant_a"
                confidence = "high"
        else:
            decision = "inconclusive"
            confidence = "low"
        
        return {
            "decision": decision,
            "confidence": confidence,
            "significant_metrics": significant_metrics,
            "non_significant_metrics": non_significant_metrics,
            "total_metrics_analyzed": len(analysis["metrics"])
        }
    
    def create_experiment_dashboard(self, experiment_id: str) -> str:
        """
        Create interactive experiment dashboard.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Path to dashboard HTML file
        """
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        analysis = self.analyze_experiment(experiment_id)
        
        if analysis.get("status") in ["insufficient_data", "insufficient_variants"]:
            logger.warning(f"Insufficient data for dashboard creation: {analysis}")
            return ""
        
        try:
            # Create subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=[
                    "Sample Sizes by Variant",
                    "Metric Comparison",
                    "Statistical Significance",
                    "Effect Sizes",
                    "Confidence Intervals",
                    "Power Analysis"
                ],
                specs=[
                    [{"type": "bar"}, {"type": "bar"}],
                    [{"type": "scatter"}, {"type": "bar"}],
                    [{"type": "scatter"}, {"type": "indicator"}]
                ]
            )
            
            # Sample sizes
            variants = list(analysis["sample_sizes"].keys())
            sizes = list(analysis["sample_sizes"].values())
            
            fig.add_trace(
                go.Bar(x=variants, y=sizes, name="Sample Sizes"),
                row=1, col=1
            )
            
            # Metric comparison
            metrics = []
            variant_a_means = []
            variant_b_means = []
            
            for metric_name, metric_data in analysis["metrics"].items():
                if "error" not in metric_data:
                    metrics.append(metric_name)
                    variant_a_means.append(metric_data["descriptive_stats"]["variant_a"]["mean"])
                    variant_b_means.append(metric_data["descriptive_stats"]["variant_b"]["mean"])
            
            if metrics:
                fig.add_trace(
                    go.Bar(x=metrics, y=variant_a_means, name="Variant A", marker_color='blue'),
                    row=1, col=2
                )
                fig.add_trace(
                    go.Bar(x=metrics, y=variant_b_means, name="Variant B", marker_color='red'),
                    row=1, col=2
                )
            
            # Statistical significance
            p_values = []
            significance = []
            
            for metric_name, metric_data in analysis["metrics"].items():
                if "error" not in metric_data:
                    p_val = metric_data["statistical_tests"]["t_test"]["p_value"]
                    p_values.append(p_val)
                    significance.append("Significant" if p_val < 0.05 else "Not Significant")
            
            if p_values:
                fig.add_trace(
                    go.Scatter(
                        x=metrics,
                        y=p_values,
                        mode='markers+text',
                        text=significance,
                        textposition="top center",
                        marker=dict(
                            size=10,
                            color=['red' if p < 0.05 else 'blue' for p in p_values]
                        ),
                        name="P-values"
                    ),
                    row=2, col=1
                )
                
                # Add significance threshold line
                fig.add_hline(y=0.05, line_dash="dash", line_color="red", row=2, col=1)
            
            # Update layout
            fig.update_layout(
                title=f"A/B Test Dashboard - {analysis['experiment_name']}",
                height=1200,
                showlegend=True
            )
            
            # Save dashboard
            dashboard_dir = os.path.join(settings.MODELS_DIR, "ab_testing", "dashboards")
            os.makedirs(dashboard_dir, exist_ok=True)
            
            dashboard_path = os.path.join(dashboard_dir, f"ab_test_{experiment_id}.html")
            fig.write_html(dashboard_path)
            
            logger.info(f"A/B test dashboard saved to {dashboard_path}")
            return dashboard_path
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return ""
    
    def get_experiment_status(self, experiment_id: str) -> Dict[str, Any]:
        """Get experiment status and summary."""
        if experiment_id not in self.experiments:
            return {"error": "Experiment not found"}
        
        experiment = self.experiments[experiment_id]
        results = self.experiment_results[experiment_id]
        
        # Calculate runtime
        runtime = datetime.now() - experiment.created_at
        
        # Traffic distribution
        variant_counts = {}
        for result in results:
            variant_counts[result.model_name] = variant_counts.get(result.model_name, 0) + 1
        
        status = {
            "experiment_id": experiment_id,
            "name": experiment.name,
            "status": "running",  # Simplified status
            "runtime_hours": runtime.total_seconds() / 3600,
            "total_samples": len(results),
            "variant_distribution": variant_counts,
            "progress": {
                "sample_progress": min(len(results) / experiment.minimum_sample_size, 1.0),
                "time_progress": min(runtime.days / experiment.max_duration_days, 1.0)
            },
            "configuration": {
                "model_a": experiment.model_a,
                "model_b": experiment.model_b,
                "traffic_split": experiment.traffic_split,
                "minimum_sample_size": experiment.minimum_sample_size
            }
        }
        
        return status


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Initialize A/B test manager
    ab_manager = ABTestManager()
    
    # Create experiment configuration
    config = ExperimentConfig(
        experiment_id="test_lstm_vs_xgb",
        name="LSTM vs XGBoost Comparison",
        description="Compare LSTM and XGBoost models for demand forecasting",
        model_a="lstm",
        model_b="xgboost",
        traffic_split=0.5,
        split_strategy=TrafficSplitStrategy.USER_ID_HASH,
        minimum_sample_size=500,
        effect_size=0.1
    )
    
    # Create experiment
    experiment_id = ab_manager.create_experiment(config)
    
    # Simulate experiment data
    np.random.seed(42)
    
    for i in range(1000):
        user_id = f"user_{i % 100}"  # 100 unique users
        features = {"feature_1": np.random.randn(), "feature_2": np.random.randn()}
        
        # Assign to variant
        variant = ab_manager.assign_to_variant(experiment_id, user_id, features)
        
        # Simulate prediction and actual (variant B performs slightly better)
        if variant == 'A':
            prediction = np.random.randn() * 2 + 5
            actual = prediction + np.random.randn() * 0.5
        else:
            prediction = np.random.randn() * 2 + 4.8  # Slightly better
            actual = prediction + np.random.randn() * 0.5
        
        # Log result
        ab_manager.log_result(
            experiment_id=experiment_id,
            variant=variant,
            prediction=prediction,
            actual=actual,
            features=features,
            user_id=user_id
        )
    
    # Analyze experiment
    analysis = ab_manager.analyze_experiment(experiment_id)
    print("Experiment Analysis:")
    print(json.dumps(analysis, indent=2, default=str))
    
    # Create dashboard
    dashboard_path = ab_manager.create_experiment_dashboard(experiment_id)
    print(f"Dashboard created: {dashboard_path}")
    
    # Get experiment status
    status = ab_manager.get_experiment_status(experiment_id)
    print("\nExperiment Status:")
    print(json.dumps(status, indent=2, default=str))