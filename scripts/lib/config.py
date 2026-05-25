"""Configuration loader for the NRL prediction model.

Loads XGBoost hyperparameters and ensemble weights from
data/config/model_config.yaml. Intentionally minimal — no schema
validation framework, no environment-specific overrides, no feature flags.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path("data/config/model_config.yaml")


@dataclass
class ModelConfig:
    """Model configuration loaded from YAML.

    Attributes:
        xgboost_n_estimators: Number of XGBoost boosting rounds.
        xgboost_max_depth: Maximum tree depth for XGBoost.
        xgboost_learning_rate: Learning rate for XGBoost.
        ensemble_weights: Weights for each sub-model. Must sum to ~1.0.
            Keys: "elo", "xgboost", "market".
    """

    xgboost_n_estimators: int = 100
    xgboost_max_depth: int = 4
    xgboost_learning_rate: float = 0.1
    ensemble_weights: dict[str, float] = field(
        default_factory=lambda: {"elo": 0.40, "xgboost": 0.35, "market": 0.25}
    )


def load_config(config_path: Path | None = None) -> ModelConfig:
    """Load model configuration from a YAML file.

    Falls back to default values if the file is missing or unreadable.

    Args:
        config_path: Path to the YAML config file. Defaults to
            data/config/model_config.yaml.

    Returns:
        A ModelConfig with values from the file, or defaults if unavailable.
    """
    path = config_path or _DEFAULT_CONFIG_PATH

    if not path.exists():
        logger.warning("Config file not found at %s — using defaults", path)
        return ModelConfig()

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("PyYAML not installed — using default config")
        return ModelConfig()

    try:
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning("Failed to load config from %s: %s — using defaults", path, exc)
        return ModelConfig()

    xgb = data.get("xgboost", {})
    weights = data.get("ensemble_weights", {})

    return ModelConfig(
        xgboost_n_estimators=int(xgb.get("n_estimators", 100)),
        xgboost_max_depth=int(xgb.get("max_depth", 4)),
        xgboost_learning_rate=float(xgb.get("learning_rate", 0.1)),
        ensemble_weights={
            "elo": float(weights.get("elo", 0.40)),
            "xgboost": float(weights.get("xgboost", 0.35)),
            "market": float(weights.get("market", 0.25)),
        },
    )
