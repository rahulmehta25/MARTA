"""
Model Explainability for MARTA Demand Forecasting

This module provides comprehensive model interpretability using SHAP, LIME,
and other explainability techniques for better understanding of ML predictions.
"""
import os
import logging
import json
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import shap
import lime
import lime.lime_tabular
from sklearn.inspection import permutation_importance, partial_dependence
from sklearn.tree import export_text
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import tempfile
import mlflow
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from src.models.ml_experiment_tracker import get_experiment_tracker

logger = logging.getLogger(__name__)


class ModelExplainer:
    """
    Comprehensive model explainability system.
    
    Features:
    - SHAP explanations (global and local)
    - LIME explanations for individual predictions
    - Permutation feature importance
    - Partial dependence plots
    - Feature interaction analysis
    - Decision tree visualization
    - Interactive explanations
    """
    
    def __init__(self, 
                 model: Any, 
                 model_type: str,
                 feature_names: List[str],
                 class_names: Optional[List[str]] = None,
                 model_name: str = "model"):
        """
        Initialize model explainer.
        
        Args:
            model: Trained ML model
            model_type: Type of model ('tree', 'linear', 'neural', 'ensemble')
            feature_names: List of feature names
            class_names: List of class names (for classification)
            model_name: Name of the model for logging
        """
        self.model = model
        self.model_type = model_type.lower()
        self.feature_names = feature_names
        self.class_names = class_names
        self.model_name = model_name
        
        # Initialize explainers
        self.shap_explainer = None
        self.lime_explainer = None
        self.shap_values = None
        self.expected_value = None
        
        # Explanation results
        self.global_explanations = {}
        self.local_explanations = {}
        
        self.experiment_tracker = get_experiment_tracker()
        
        # Create explanations directory
        self.explanations_dir = os.path.join(settings.MODELS_DIR, "explanations", model_name)
        os.makedirs(self.explanations_dir, exist_ok=True)
        
        logger.info(f"Initialized explainer for {model_name} ({model_type})")
    
    def setup_explainers(self, 
                        X_background: np.ndarray,
                        max_samples: int = 1000) -> None:
        """
        Setup SHAP and LIME explainers.
        
        Args:
            X_background: Background dataset for SHAP
            max_samples: Maximum samples for background
        """
        logger.info("Setting up explainers...")
        
        # Sample background data if too large
        if len(X_background) > max_samples:
            indices = np.random.choice(len(X_background), max_samples, replace=False)
            X_background_sample = X_background[indices]
        else:
            X_background_sample = X_background
        
        # Setup SHAP explainer based on model type
        try:
            if self.model_type in ['tree', 'ensemble']:
                if hasattr(self.model, 'feature_importances_'):
                    # Tree-based models
                    self.shap_explainer = shap.TreeExplainer(self.model)
                else:
                    # General case
                    self.shap_explainer = shap.Explainer(self.model, X_background_sample)
            elif self.model_type == 'linear':
                self.shap_explainer = shap.LinearExplainer(self.model, X_background_sample)
            elif self.model_type == 'neural':
                self.shap_explainer = shap.DeepExplainer(self.model, X_background_sample)
            else:
                # Kernel explainer for any model type
                self.shap_explainer = shap.KernelExplainer(self.model.predict, X_background_sample)
            
            logger.info(f"SHAP explainer setup: {type(self.shap_explainer).__name__}")
            
        except Exception as e:
            logger.warning(f"Failed to setup SHAP explainer: {e}")
            # Fallback to kernel explainer
            try:
                self.shap_explainer = shap.KernelExplainer(self.model.predict, X_background_sample)
                logger.info("Using SHAP KernelExplainer as fallback")
            except Exception as e2:
                logger.error(f"Failed to setup fallback SHAP explainer: {e2}")
        
        # Setup LIME explainer
        try:
            self.lime_explainer = lime.lime_tabular.LimeTabularExplainer(
                X_background_sample,
                feature_names=self.feature_names,
                class_names=self.class_names,
                mode='regression' if self.class_names is None else 'classification',
                discretize_continuous=True,
                random_state=settings.RANDOM_SEED
            )
            logger.info("LIME explainer setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup LIME explainer: {e}")
    
    def explain_global(self, 
                      X_explain: np.ndarray,
                      max_samples: int = 1000,
                      save_plots: bool = True) -> Dict[str, Any]:
        """
        Generate global explanations.
        
        Args:
            X_explain: Data to explain
            max_samples: Maximum samples to use
            save_plots: Whether to save explanation plots
            
        Returns:
            Dictionary of global explanations
        """
        logger.info("Generating global explanations...")
        
        # Sample data if too large
        if len(X_explain) > max_samples:
            indices = np.random.choice(len(X_explain), max_samples, replace=False)
            X_sample = X_explain[indices]
        else:
            X_sample = X_explain
        
        global_explanations = {}
        
        # SHAP global explanations
        if self.shap_explainer is not None:
            try:
                logger.info("Computing SHAP values...")
                self.shap_values = self.shap_explainer.shap_values(X_sample)
                
                if hasattr(self.shap_explainer, 'expected_value'):
                    self.expected_value = self.shap_explainer.expected_value
                
                # Global feature importance (mean absolute SHAP values)
                if isinstance(self.shap_values, list):
                    # Multi-class case
                    mean_shap = np.mean([np.abs(shap_vals).mean(0) for shap_vals in self.shap_values], axis=0)
                else:
                    # Single output case
                    mean_shap = np.abs(self.shap_values).mean(0)
                
                feature_importance = dict(zip(self.feature_names, mean_shap))
                global_explanations['shap_feature_importance'] = feature_importance
                
                logger.info("SHAP global explanations computed")
                
            except Exception as e:
                logger.error(f"Failed to compute SHAP global explanations: {e}")
        
        # Permutation importance
        try:
            logger.info("Computing permutation importance...")
            perm_importance = permutation_importance(
                self.model, X_sample, self.model.predict(X_sample),
                n_repeats=10, random_state=settings.RANDOM_SEED, n_jobs=-1
            )
            
            perm_importance_dict = dict(zip(
                self.feature_names, 
                perm_importance.importances_mean
            ))
            global_explanations['permutation_importance'] = perm_importance_dict
            
        except Exception as e:
            logger.error(f"Failed to compute permutation importance: {e}")
        
        # Feature importance from tree-based models
        if hasattr(self.model, 'feature_importances_'):
            tree_importance = dict(zip(self.feature_names, self.model.feature_importances_))
            global_explanations['tree_feature_importance'] = tree_importance
        
        # Save plots
        if save_plots and self.shap_values is not None:
            self._create_global_plots(X_sample)
        
        self.global_explanations = global_explanations
        return global_explanations
    
    def explain_local(self, 
                     X_instance: np.ndarray,
                     instance_id: str = "sample",
                     save_plots: bool = True) -> Dict[str, Any]:
        """
        Generate local explanations for a single instance.
        
        Args:
            X_instance: Single instance to explain (2D array with 1 row)
            instance_id: Identifier for the instance
            save_plots: Whether to save explanation plots
            
        Returns:
            Dictionary of local explanations
        """
        logger.info(f"Generating local explanations for instance: {instance_id}")
        
        local_explanations = {}
        
        # SHAP local explanation
        if self.shap_explainer is not None:
            try:
                shap_values = self.shap_explainer.shap_values(X_instance)
                
                if isinstance(shap_values, list):
                    # Multi-class case - take first class
                    shap_values_single = shap_values[0][0]
                else:
                    shap_values_single = shap_values[0]
                
                local_explanations['shap_values'] = dict(zip(self.feature_names, shap_values_single))
                local_explanations['shap_expected_value'] = self.expected_value
                
            except Exception as e:
                logger.error(f"Failed to compute SHAP local explanation: {e}")
        
        # LIME local explanation
        if self.lime_explainer is not None:
            try:
                lime_exp = self.lime_explainer.explain_instance(
                    X_instance[0], 
                    self.model.predict,
                    num_features=len(self.feature_names)
                )
                
                lime_values = dict(lime_exp.as_list())
                local_explanations['lime_values'] = lime_values
                
                # Save LIME explanation
                if save_plots:
                    lime_path = os.path.join(self.explanations_dir, f"lime_{instance_id}.html")
                    lime_exp.save_to_file(lime_path)
                
            except Exception as e:
                logger.error(f"Failed to compute LIME local explanation: {e}")
        
        # Save plots
        if save_plots and 'shap_values' in local_explanations:
            self._create_local_plots(X_instance, local_explanations, instance_id)
        
        self.local_explanations[instance_id] = local_explanations
        return local_explanations
    
    def create_partial_dependence_plots(self, 
                                      X_data: np.ndarray,
                                      features: Optional[List[str]] = None,
                                      max_samples: int = 1000) -> None:
        """
        Create partial dependence plots for top features.
        
        Args:
            X_data: Data for partial dependence calculation
            features: Specific features to plot (top 5 by default)
            max_samples: Maximum samples to use
        """
        logger.info("Creating partial dependence plots...")
        
        try:
            from sklearn.inspection import PartialDependenceDisplay
            
            # Sample data
            if len(X_data) > max_samples:
                indices = np.random.choice(len(X_data), max_samples, replace=False)
                X_sample = X_data[indices]
            else:
                X_sample = X_data
            
            # Select features
            if features is None:
                # Use top 5 features by importance
                if 'shap_feature_importance' in self.global_explanations:
                    importance = self.global_explanations['shap_feature_importance']
                elif 'permutation_importance' in self.global_explanations:
                    importance = self.global_explanations['permutation_importance']
                elif hasattr(self.model, 'feature_importances_'):
                    importance = dict(zip(self.feature_names, self.model.feature_importances_))
                else:
                    importance = {name: 1.0 for name in self.feature_names[:5]}
                
                features = sorted(importance.keys(), key=importance.get, reverse=True)[:5]
            
            # Get feature indices
            feature_indices = [self.feature_names.index(f) for f in features if f in self.feature_names]
            
            # Create PDP plots
            fig, axes = plt.subplots(2, 3, figsize=(15, 10))
            axes = axes.flatten()
            
            for i, feature_idx in enumerate(feature_indices[:6]):
                if i >= 6:
                    break
                
                display = PartialDependenceDisplay.from_estimator(
                    self.model, X_sample, [feature_idx],
                    ax=axes[i], feature_names=self.feature_names
                )
                axes[i].set_title(f"PDP: {self.feature_names[feature_idx]}")
            
            # Remove empty subplots
            for i in range(len(feature_indices), 6):
                axes[i].remove()
            
            plt.tight_layout()
            
            # Save plot
            pdp_path = os.path.join(self.explanations_dir, "partial_dependence_plots.png")
            plt.savefig(pdp_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Partial dependence plots saved to {pdp_path}")
            
        except Exception as e:
            logger.error(f"Failed to create partial dependence plots: {e}")
    
    def create_interaction_plots(self, 
                               X_data: np.ndarray,
                               top_n: int = 3,
                               max_samples: int = 1000) -> None:
        """
        Create feature interaction plots using SHAP.
        
        Args:
            X_data: Data for interaction analysis
            top_n: Number of top interactions to plot
            max_samples: Maximum samples to use
        """
        logger.info("Creating feature interaction plots...")
        
        if self.shap_values is None:
            logger.warning("SHAP values not available for interaction plots")
            return
        
        try:
            # Sample data
            if len(X_data) > max_samples:
                indices = np.random.choice(len(X_data), max_samples, replace=False)
                X_sample = X_data[indices]
                if isinstance(self.shap_values, list):
                    shap_sample = [sv[indices] for sv in self.shap_values]
                else:
                    shap_sample = self.shap_values[indices]
            else:
                X_sample = X_data
                shap_sample = self.shap_values
            
            # Create interaction plots
            if isinstance(shap_sample, list):
                shap_values_plot = shap_sample[0]
            else:
                shap_values_plot = shap_sample
            
            # Summary plot
            plt.figure(figsize=(10, 8))
            shap.summary_plot(shap_values_plot, X_sample, feature_names=self.feature_names, show=False)
            summary_path = os.path.join(self.explanations_dir, "shap_summary_plot.png")
            plt.savefig(summary_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            # Dependence plots for top features
            importance = np.abs(shap_values_plot).mean(0)
            top_features = np.argsort(importance)[-top_n:]
            
            fig, axes = plt.subplots(1, top_n, figsize=(5*top_n, 4))
            if top_n == 1:
                axes = [axes]
            
            for i, feature_idx in enumerate(top_features):
                shap.dependence_plot(
                    feature_idx, shap_values_plot, X_sample,
                    feature_names=self.feature_names,
                    ax=axes[i], show=False
                )
                axes[i].set_title(f"SHAP Dependence: {self.feature_names[feature_idx]}")
            
            plt.tight_layout()
            dependence_path = os.path.join(self.explanations_dir, "shap_dependence_plots.png")
            plt.savefig(dependence_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info("Feature interaction plots created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create interaction plots: {e}")
    
    def create_decision_tree_explanation(self, max_depth: int = 3) -> Optional[str]:
        """
        Create decision tree explanation for tree-based models.
        
        Args:
            max_depth: Maximum depth for tree explanation
            
        Returns:
            Tree explanation text
        """
        if not hasattr(self.model, 'estimators_') and not hasattr(self.model, 'tree_'):
            logger.warning("Model is not tree-based, skipping tree explanation")
            return None
        
        try:
            if hasattr(self.model, 'estimators_'):
                # Ensemble model - explain first tree
                tree_model = self.model.estimators_[0]
            else:
                tree_model = self.model
            
            tree_rules = export_text(
                tree_model, 
                feature_names=self.feature_names,
                max_depth=max_depth
            )
            
            # Save tree explanation
            tree_path = os.path.join(self.explanations_dir, "tree_explanation.txt")
            with open(tree_path, 'w') as f:
                f.write(tree_rules)
            
            logger.info(f"Decision tree explanation saved to {tree_path}")
            return tree_rules
            
        except Exception as e:
            logger.error(f"Failed to create decision tree explanation: {e}")
            return None
    
    def create_interactive_dashboard(self, 
                                   X_data: np.ndarray,
                                   y_data: np.ndarray,
                                   max_samples: int = 1000) -> str:
        """
        Create interactive explanation dashboard using Plotly.
        
        Args:
            X_data: Feature data
            y_data: Target data
            max_samples: Maximum samples to include
            
        Returns:
            Path to the saved HTML dashboard
        """
        logger.info("Creating interactive explanation dashboard...")
        
        try:
            # Sample data
            if len(X_data) > max_samples:
                indices = np.random.choice(len(X_data), max_samples, replace=False)
                X_sample = X_data[indices]
                y_sample = y_data[indices]
            else:
                X_sample = X_data
                y_sample = y_data
            
            # Create subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=[
                    "Feature Importance (SHAP)", 
                    "Feature Importance (Permutation)",
                    "Prediction vs Actual",
                    "Feature Correlation",
                    "SHAP Waterfall (Sample)",
                    "Model Performance"
                ],
                specs=[
                    [{"type": "bar"}, {"type": "bar"}],
                    [{"type": "scatter"}, {"type": "heatmap"}],
                    [{"type": "waterfall"}, {"type": "indicator"}]
                ]
            )
            
            # Feature importance plots
            if 'shap_feature_importance' in self.global_explanations:
                shap_importance = self.global_explanations['shap_feature_importance']
                features_shap = list(shap_importance.keys())
                values_shap = list(shap_importance.values())
                
                fig.add_trace(
                    go.Bar(x=features_shap, y=values_shap, name="SHAP Importance"),
                    row=1, col=1
                )
            
            if 'permutation_importance' in self.global_explanations:
                perm_importance = self.global_explanations['permutation_importance']
                features_perm = list(perm_importance.keys())
                values_perm = list(perm_importance.values())
                
                fig.add_trace(
                    go.Bar(x=features_perm, y=values_perm, name="Permutation Importance"),
                    row=1, col=2
                )
            
            # Prediction vs Actual
            y_pred = self.model.predict(X_sample)
            fig.add_trace(
                go.Scatter(x=y_sample, y=y_pred, mode='markers', name="Predictions"),
                row=2, col=1
            )
            
            # Add perfect prediction line
            min_val, max_val = min(y_sample.min(), y_pred.min()), max(y_sample.max(), y_pred.max())
            fig.add_trace(
                go.Scatter(x=[min_val, max_val], y=[min_val, max_val], 
                          mode='lines', name="Perfect Prediction", line=dict(dash='dash')),
                row=2, col=1
            )
            
            # Feature correlation heatmap
            df_features = pd.DataFrame(X_sample, columns=self.feature_names)
            corr_matrix = df_features.corr()
            
            fig.add_trace(
                go.Heatmap(z=corr_matrix.values, 
                          x=corr_matrix.columns, 
                          y=corr_matrix.index,
                          colorscale='RdBu'),
                row=2, col=2
            )
            
            # Model performance indicator
            from sklearn.metrics import r2_score, mean_squared_error
            r2 = r2_score(y_sample, y_pred)
            rmse = np.sqrt(mean_squared_error(y_sample, y_pred))
            
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=r2,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "R² Score"},
                    gauge={'axis': {'range': [None, 1]},
                           'bar': {'color': "darkblue"},
                           'steps': [{'range': [0, 0.5], 'color': "lightgray"},
                                    {'range': [0.5, 0.8], 'color': "yellow"},
                                    {'range': [0.8, 1], 'color': "green"}],
                           'threshold': {'line': {'color': "red", 'width': 4},
                                        'thickness': 0.75, 'value': 0.9}}
                ),
                row=3, col=2
            )
            
            # Update layout
            fig.update_layout(
                title=f"Model Explainability Dashboard - {self.model_name}",
                height=1200,
                showlegend=False
            )
            
            # Save dashboard
            dashboard_path = os.path.join(self.explanations_dir, "interactive_dashboard.html")
            fig.write_html(dashboard_path)
            
            logger.info(f"Interactive dashboard saved to {dashboard_path}")
            return dashboard_path
            
        except Exception as e:
            logger.error(f"Failed to create interactive dashboard: {e}")
            return ""
    
    def generate_explanation_report(self, 
                                   X_data: np.ndarray,
                                   y_data: np.ndarray,
                                   sample_instances: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive explanation report.
        
        Args:
            X_data: Feature data
            y_data: Target data
            sample_instances: Specific instances to explain locally
            
        Returns:
            Complete explanation report
        """
        logger.info("Generating comprehensive explanation report...")
        
        with self.experiment_tracker.start_run(
            run_name=f"explanation_{self.model_name}",
            tags={"model_type": self.model_type, "explanation_type": "comprehensive"}
        ) as run:
            
            # Global explanations
            global_exp = self.explain_global(X_data)
            
            # Local explanations for sample instances
            if sample_instances is None:
                sample_instances = np.random.choice(len(X_data), min(5, len(X_data)), replace=False)
            
            local_exp = {}
            for i, idx in enumerate(sample_instances):
                instance_exp = self.explain_local(X_data[idx:idx+1], f"instance_{idx}")
                local_exp[f"instance_{idx}"] = instance_exp
            
            # Additional analyses
            self.create_partial_dependence_plots(X_data)
            self.create_interaction_plots(X_data)
            tree_explanation = self.create_decision_tree_explanation()
            dashboard_path = self.create_interactive_dashboard(X_data, y_data)
            
            # Create summary report
            report = {
                "model_name": self.model_name,
                "model_type": self.model_type,
                "feature_names": self.feature_names,
                "global_explanations": global_exp,
                "local_explanations": local_exp,
                "tree_explanation": tree_explanation,
                "dashboard_path": dashboard_path,
                "explanation_dir": self.explanations_dir,
                "generated_at": datetime.now().isoformat()
            }
            
            # Save report
            report_path = os.path.join(self.explanations_dir, "explanation_report.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Log to MLflow
            mlflow.log_artifacts(self.explanations_dir, "explanations")
            
            if global_exp.get('shap_feature_importance'):
                for feature, importance in global_exp['shap_feature_importance'].items():
                    mlflow.log_metric(f"shap_importance_{feature}", importance)
            
            logger.info(f"Explanation report saved to {report_path}")
            return report
    
    def _create_global_plots(self, X_data: np.ndarray) -> None:
        """Create global explanation plots."""
        try:
            # SHAP summary plot
            plt.figure(figsize=(10, 8))
            if isinstance(self.shap_values, list):
                shap.summary_plot(self.shap_values[0], X_data, feature_names=self.feature_names, show=False)
            else:
                shap.summary_plot(self.shap_values, X_data, feature_names=self.feature_names, show=False)
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.explanations_dir, "global_shap_summary.png"), 
                       dpi=150, bbox_inches='tight')
            plt.close()
            
            # Feature importance bar plot
            if 'shap_feature_importance' in self.global_explanations:
                importance = self.global_explanations['shap_feature_importance']
                
                plt.figure(figsize=(12, 6))
                features = list(importance.keys())
                values = list(importance.values())
                
                # Sort by importance
                sorted_pairs = sorted(zip(features, values), key=lambda x: x[1], reverse=True)
                features_sorted, values_sorted = zip(*sorted_pairs)
                
                plt.barh(range(len(features_sorted)), values_sorted)
                plt.yticks(range(len(features_sorted)), features_sorted)
                plt.xlabel('Mean |SHAP Value|')
                plt.title('Global Feature Importance (SHAP)')
                plt.tight_layout()
                
                plt.savefig(os.path.join(self.explanations_dir, "global_feature_importance.png"),
                           dpi=150, bbox_inches='tight')
                plt.close()
            
        except Exception as e:
            logger.error(f"Failed to create global plots: {e}")
    
    def _create_local_plots(self, 
                           X_instance: np.ndarray,
                           explanations: Dict[str, Any],
                           instance_id: str) -> None:
        """Create local explanation plots."""
        try:
            if 'shap_values' in explanations and self.shap_explainer is not None:
                # SHAP waterfall plot
                if hasattr(shap, 'waterfall_plot'):
                    shap_values = self.shap_explainer.shap_values(X_instance)
                    
                    if isinstance(shap_values, list):
                        shap_values_plot = shap_values[0][0]
                    else:
                        shap_values_plot = shap_values[0]
                    
                    # Create explanation object for waterfall plot
                    explanation = shap.Explanation(
                        values=shap_values_plot,
                        base_values=self.expected_value,
                        data=X_instance[0],
                        feature_names=self.feature_names
                    )
                    
                    plt.figure(figsize=(10, 6))
                    shap.waterfall_plot(explanation, show=False)
                    plt.tight_layout()
                    
                    waterfall_path = os.path.join(self.explanations_dir, f"shap_waterfall_{instance_id}.png")
                    plt.savefig(waterfall_path, dpi=150, bbox_inches='tight')
                    plt.close()
                
                # Local feature importance bar plot
                shap_dict = explanations['shap_values']
                
                plt.figure(figsize=(10, 6))
                features = list(shap_dict.keys())
                values = list(shap_dict.values())
                
                # Sort by absolute value
                sorted_pairs = sorted(zip(features, values), key=lambda x: abs(x[1]), reverse=True)
                features_sorted, values_sorted = zip(*sorted_pairs)
                
                colors = ['red' if v < 0 else 'blue' for v in values_sorted]
                plt.barh(range(len(features_sorted)), values_sorted, color=colors)
                plt.yticks(range(len(features_sorted)), features_sorted)
                plt.xlabel('SHAP Value')
                plt.title(f'Local Feature Contributions - {instance_id}')
                plt.axvline(x=0, color='black', linestyle='-', alpha=0.3)
                plt.tight_layout()
                
                local_path = os.path.join(self.explanations_dir, f"local_shap_{instance_id}.png")
                plt.savefig(local_path, dpi=150, bbox_inches='tight')
                plt.close()
            
        except Exception as e:
            logger.error(f"Failed to create local plots for {instance_id}: {e}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.datasets import make_regression
    
    # Generate sample data
    X, y = make_regression(n_samples=1000, n_features=10, noise=0.1, random_state=42)
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    
    # Train model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Create explainer
    explainer = ModelExplainer(
        model=model,
        model_type="ensemble",
        feature_names=feature_names,
        model_name="example_rf"
    )
    
    # Setup explainers
    explainer.setup_explainers(X[:100])
    
    # Generate comprehensive report
    report = explainer.generate_explanation_report(X, y, sample_instances=[0, 1, 2])
    print("Explanation report generated successfully!")
    print(f"Report saved to: {report['explanation_dir']}")