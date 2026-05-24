"""Model registry for trained prediction model variants.

Manages storage, versioning, and metadata for trained model artifacts
including performance metrics and feature importance tracking.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Model registry data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelMetadata:
    """Metadata for a trained model variant.
    
    Attributes:
        model_id: Unique identifier (e.g., "xgboost-v1-20260415")
        model_type: Model architecture type
        trained_at: ISO-8601 timestamp of training completion
        feature_version: Feature schema version used for training
        hyperparameters: Model-specific hyperparameter configuration
        accuracy: Overall prediction accuracy (0.0-1.0)
        brier_score: Brier score (lower is better, 0.25 is random)
        log_loss: Logarithmic loss (lower is better)
        calibration_error: Expected calibration error (lower is better)
        train_seasons: List of seasons used for training
        train_games: Number of games in training set
        validation_games: Number of games in validation set
        feature_importance: Top features by importance score
    """

    model_id: str  # e.g., "xgboost-v1-20260415"
    model_type: str  # "xgboost", "lightgbm", "neural", "ensemble"
    trained_at: str  # ISO-8601 timestamp
    feature_version: str  # "v2.1"
    hyperparameters: dict
    
    # Performance metrics
    accuracy: float
    brier_score: float
    log_loss: float
    calibration_error: float
    
    # Training data
    train_seasons: list[int]
    train_games: int
    validation_games: int
    
    # Feature importance (top 10)
    feature_importance: dict[str, float]
