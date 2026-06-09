"""
Model Registry System

Comprehensive model versioning, tracking, and promotion system for ML models.
Supports MLflow integration and local file-based registry.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pathlib import Path
import json
import shutil
import hashlib
import logging

logger = logging.getLogger(__name__)


class ModelStage(Enum):
    """Model lifecycle stages."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


@dataclass
class ModelMetrics:
    """
    Model performance metrics.

    Attributes:
        mae: Mean Absolute Error.
        mse: Mean Squared Error.
        rmse: Root Mean Squared Error.
        r2: R-squared score.
        mape: Mean Absolute Percentage Error.
        accuracy: Classification accuracy.
        f1_score: F1 score.
        custom_metrics: Additional custom metrics.
    """
    mae: Optional[float] = None
    mse: Optional[float] = None
    rmse: Optional[float] = None
    r2: Optional[float] = None
    mape: Optional[float] = None
    accuracy: Optional[float] = None
    f1_score: Optional[float] = None
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = {
            "mae": self.mae,
            "mse": self.mse,
            "rmse": self.rmse,
            "r2": self.r2,
            "mape": self.mape,
            "accuracy": self.accuracy,
            "f1_score": self.f1_score,
        }
        d.update(self.custom_metrics)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelMetrics":
        """Create from dictionary."""
        known_keys = {"mae", "mse", "rmse", "r2", "mape", "accuracy", "f1_score"}
        known = {k: d.get(k) for k in known_keys}
        custom = {k: v for k, v in d.items() if k not in known_keys}
        return cls(**known, custom_metrics=custom)


@dataclass
class ModelVersion:
    """
    Model version information.

    Attributes:
        model_name: Name of the registered model.
        version: Version number.
        stage: Current lifecycle stage.
        model_path: Path to model artifacts.
        config: Model configuration.
        metrics: Performance metrics.
        training_info: Training metadata.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        description: Version description.
        tags: Version tags.
        checksum: Model file checksum.
    """
    model_name: str
    version: int
    stage: ModelStage = ModelStage.DEVELOPMENT
    model_path: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: ModelMetrics = field(default_factory=ModelMetrics)
    training_info: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    checksum: str = ""

    @property
    def version_id(self) -> str:
        """Get unique version identifier."""
        return f"{self.model_name}/v{self.version}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "stage": self.stage.value,
            "model_path": self.model_path,
            "config": self.config,
            "metrics": self.metrics.to_dict(),
            "training_info": self.training_info,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "description": self.description,
            "tags": self.tags,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelVersion":
        """Create from dictionary."""
        d = d.copy()
        d["stage"] = ModelStage(d.get("stage", "development"))
        d["metrics"] = ModelMetrics.from_dict(d.get("metrics", {}))
        d["created_at"] = datetime.fromisoformat(d.get("created_at", datetime.now().isoformat()))
        d["updated_at"] = datetime.fromisoformat(d.get("updated_at", datetime.now().isoformat()))
        return cls(**d)


@dataclass
class RegisteredModel:
    """
    Registered model with multiple versions.

    Attributes:
        name: Model name.
        description: Model description.
        versions: List of model versions.
        tags: Model tags.
        created_at: Creation timestamp.
        latest_version: Latest version number.
        production_version: Current production version.
    """
    name: str
    description: str = ""
    versions: List[ModelVersion] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def latest_version(self) -> Optional[int]:
        """Get latest version number."""
        if not self.versions:
            return None
        return max(v.version for v in self.versions)

    @property
    def production_version(self) -> Optional[ModelVersion]:
        """Get production version."""
        for v in self.versions:
            if v.stage == ModelStage.PRODUCTION:
                return v
        return None

    def get_version(self, version: int) -> Optional[ModelVersion]:
        """Get specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "versions": [v.to_dict() for v in self.versions],
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RegisteredModel":
        """Create from dictionary."""
        d = d.copy()
        d["versions"] = [ModelVersion.from_dict(v) for v in d.get("versions", [])]
        d["created_at"] = datetime.fromisoformat(d.get("created_at", datetime.now().isoformat()))
        return cls(**d)


class ModelRegistry:
    """
    Local model registry for versioning and managing ML models.

    Features:
    - Model versioning with semantic versions
    - Stage promotion (development -> staging -> production)
    - Metric tracking per version
    - Model artifact storage
    - Version comparison
    - Rollback support

    Example:
        >>> registry = ModelRegistry("./model_registry")
        >>> version = registry.register_model(
        ...     model_path="./models/lstm_v1",
        ...     model_name="demand_lstm",
        ...     config=config.to_dict(),
        ...     metrics=ModelMetrics(rmse=0.25, mae=0.15)
        ... )
        >>> registry.promote_model("demand_lstm", version.version, ModelStage.PRODUCTION)
    """

    def __init__(self, registry_path: str = "./model_registry"):
        """
        Initialize model registry.

        Args:
            registry_path: Path to registry storage directory.
        """
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)

        self.models_path = self.registry_path / "models"
        self.models_path.mkdir(exist_ok=True)

        self.metadata_path = self.registry_path / "metadata.json"
        self.models: Dict[str, RegisteredModel] = {}

        self._load_registry()
        logger.info(f"ModelRegistry initialized at {self.registry_path}")

    def _load_registry(self) -> None:
        """Load registry from disk."""
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                data = json.load(f)
                self.models = {
                    name: RegisteredModel.from_dict(model_data)
                    for name, model_data in data.get("models", {}).items()
                }
            logger.info(f"Loaded {len(self.models)} registered models")

    def _save_registry(self) -> None:
        """Save registry to disk."""
        data = {
            "models": {name: model.to_dict() for name, model in self.models.items()},
            "updated_at": datetime.now().isoformat(),
        }
        with open(self.metadata_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def _compute_checksum(self, path: Path) -> str:
        """Compute checksum for model artifacts."""
        hasher = hashlib.sha256()

        if path.is_file():
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
        elif path.is_dir():
            for file_path in sorted(path.rglob('*')):
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)

        return hasher.hexdigest()[:16]

    def register_model(
        self,
        model_path: str,
        model_name: str,
        config: Optional[Dict[str, Any]] = None,
        metrics: Optional[ModelMetrics] = None,
        training_info: Optional[Dict[str, Any]] = None,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
        copy_artifacts: bool = True,
    ) -> ModelVersion:
        """
        Register a new model version.

        Args:
            model_path: Path to model artifacts.
            model_name: Name for the registered model.
            config: Model configuration.
            metrics: Performance metrics.
            training_info: Training metadata.
            description: Version description.
            tags: Version tags.
            copy_artifacts: Whether to copy artifacts to registry.

        Returns:
            Created ModelVersion.
        """
        source_path = Path(model_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Model path not found: {model_path}")

        # Get or create registered model
        if model_name not in self.models:
            self.models[model_name] = RegisteredModel(name=model_name)
            logger.info(f"Created new registered model: {model_name}")

        registered_model = self.models[model_name]

        # Determine version number
        version_num = (registered_model.latest_version or 0) + 1

        # Create version directory
        version_dir = self.models_path / model_name / f"v{version_num}"
        version_dir.mkdir(parents=True, exist_ok=True)

        # Copy or link artifacts
        if copy_artifacts:
            if source_path.is_dir():
                dest_path = version_dir / "artifacts"
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
            else:
                shutil.copy2(source_path, version_dir / source_path.name)
            stored_path = str(version_dir)
        else:
            stored_path = str(source_path)

        # Compute checksum
        checksum = self._compute_checksum(source_path)

        # Create version
        version = ModelVersion(
            model_name=model_name,
            version=version_num,
            stage=ModelStage.DEVELOPMENT,
            model_path=stored_path,
            config=config or {},
            metrics=metrics or ModelMetrics(),
            training_info=training_info or {},
            description=description,
            tags=tags or {},
            checksum=checksum,
        )

        registered_model.versions.append(version)
        self._save_registry()

        logger.info(f"Registered model version: {version.version_id}")
        return version

    def get_model(self, model_name: str) -> Optional[RegisteredModel]:
        """Get registered model by name."""
        return self.models.get(model_name)

    def get_model_version(
        self,
        model_name: str,
        version: Optional[int] = None,
        stage: Optional[ModelStage] = None,
    ) -> Optional[ModelVersion]:
        """
        Get specific model version.

        Args:
            model_name: Name of registered model.
            version: Version number (None for latest).
            stage: Get version by stage (e.g., production).

        Returns:
            ModelVersion or None.
        """
        registered_model = self.models.get(model_name)
        if not registered_model:
            return None

        if stage:
            for v in registered_model.versions:
                if v.stage == stage:
                    return v
            return None

        if version is None:
            version = registered_model.latest_version

        return registered_model.get_version(version)

    def list_models(self) -> List[str]:
        """List all registered model names."""
        return list(self.models.keys())

    def list_versions(self, model_name: str) -> List[ModelVersion]:
        """List all versions of a model."""
        registered_model = self.models.get(model_name)
        if not registered_model:
            return []
        return sorted(registered_model.versions, key=lambda v: v.version)

    def promote_model(
        self,
        model_name: str,
        version: int,
        target_stage: ModelStage,
    ) -> ModelVersion:
        """
        Promote model version to a new stage.

        Args:
            model_name: Name of registered model.
            version: Version to promote.
            target_stage: Target stage.

        Returns:
            Updated ModelVersion.
        """
        model_version = self.get_model_version(model_name, version)
        if not model_version:
            raise ValueError(f"Model version not found: {model_name}/v{version}")

        # If promoting to production, demote current production version
        if target_stage == ModelStage.PRODUCTION:
            current_prod = self.get_model_version(model_name, stage=ModelStage.PRODUCTION)
            if current_prod and current_prod.version != version:
                current_prod.stage = ModelStage.ARCHIVED
                current_prod.updated_at = datetime.now()
                logger.info(f"Archived previous production: {current_prod.version_id}")

        model_version.stage = target_stage
        model_version.updated_at = datetime.now()
        self._save_registry()

        logger.info(f"Promoted {model_version.version_id} to {target_stage.value}")
        return model_version

    def update_metrics(
        self,
        model_name: str,
        version: int,
        metrics: ModelMetrics,
    ) -> ModelVersion:
        """
        Update metrics for a model version.

        Args:
            model_name: Name of registered model.
            version: Version to update.
            metrics: New metrics.

        Returns:
            Updated ModelVersion.
        """
        model_version = self.get_model_version(model_name, version)
        if not model_version:
            raise ValueError(f"Model version not found: {model_name}/v{version}")

        model_version.metrics = metrics
        model_version.updated_at = datetime.now()
        self._save_registry()

        logger.info(f"Updated metrics for {model_version.version_id}")
        return model_version

    def compare_versions(
        self,
        model_name: str,
        versions: Optional[List[int]] = None,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare multiple versions of a model.

        Args:
            model_name: Name of registered model.
            versions: Versions to compare (None for all).
            metrics: Metrics to compare.

        Returns:
            Comparison results.
        """
        registered_model = self.models.get(model_name)
        if not registered_model:
            return {"error": f"Model not found: {model_name}"}

        if versions is None:
            model_versions = registered_model.versions
        else:
            model_versions = [v for v in registered_model.versions if v.version in versions]

        comparison = {
            "model_name": model_name,
            "versions": [],
        }

        for v in sorted(model_versions, key=lambda x: x.version):
            version_data = {
                "version": v.version,
                "stage": v.stage.value,
                "created_at": v.created_at.isoformat(),
            }

            version_metrics = v.metrics.to_dict()
            if metrics:
                version_metrics = {k: v for k, v in version_metrics.items() if k in metrics}
            version_data["metrics"] = version_metrics

            comparison["versions"].append(version_data)

        return comparison

    def get_production_model(self, model_name: str) -> Optional[ModelVersion]:
        """Get the production version of a model."""
        return self.get_model_version(model_name, stage=ModelStage.PRODUCTION)

    def rollback(
        self,
        model_name: str,
        target_version: int,
    ) -> ModelVersion:
        """
        Rollback to a previous version.

        Args:
            model_name: Name of registered model.
            target_version: Version to rollback to.

        Returns:
            Rolled back ModelVersion.
        """
        return self.promote_model(model_name, target_version, ModelStage.PRODUCTION)

    def delete_version(
        self,
        model_name: str,
        version: int,
        delete_artifacts: bool = False,
    ) -> bool:
        """
        Delete a model version.

        Args:
            model_name: Name of registered model.
            version: Version to delete.
            delete_artifacts: Whether to delete artifact files.

        Returns:
            True if deleted successfully.
        """
        registered_model = self.models.get(model_name)
        if not registered_model:
            return False

        model_version = registered_model.get_version(version)
        if not model_version:
            return False

        if model_version.stage == ModelStage.PRODUCTION:
            raise ValueError("Cannot delete production version. Promote another version first.")

        registered_model.versions = [v for v in registered_model.versions if v.version != version]

        if delete_artifacts:
            version_dir = self.models_path / model_name / f"v{version}"
            if version_dir.exists():
                shutil.rmtree(version_dir)

        self._save_registry()
        logger.info(f"Deleted version: {model_name}/v{version}")
        return True

    def export_registry(self, export_path: str) -> None:
        """Export registry to JSON file."""
        data = {
            "models": {name: model.to_dict() for name, model in self.models.items()},
            "exported_at": datetime.now().isoformat(),
        }
        with open(export_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Registry exported to {export_path}")

    def get_summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        summary = {
            "total_models": len(self.models),
            "total_versions": sum(len(m.versions) for m in self.models.values()),
            "models": {},
        }

        for name, model in self.models.items():
            prod_version = model.production_version
            summary["models"][name] = {
                "versions": len(model.versions),
                "latest_version": model.latest_version,
                "production_version": prod_version.version if prod_version else None,
            }

        return summary
