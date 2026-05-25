"""XGBoost model wrapper for NRL match prediction.

Provides a thin wrapper around XGBClassifier with a consistent interface
for training, prediction, persistence, and feature importance.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..config import load_config
from ..features import FEATURE_NAMES


class XGBoostPredictor:
    """XGBoost classifier for NRL match outcome prediction.

    Args:
        n_estimators: Number of boosting rounds. Defaults to 100.
        max_depth: Maximum tree depth. Defaults to 4.
        learning_rate: Step size shrinkage. Defaults to 0.1.

    Example::

        predictor = XGBoostPredictor()
        predictor.train(X_train, y_train)
        probs = predictor.predict_proba(X_test)  # values in [0, 1]
        predictor.save(Path("data/models/xgboost_model.json"))
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 4,
        learning_rate: float = 0.1,
    ) -> None:
        from xgboost import XGBClassifier  # type: ignore[import-untyped]

        self.model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
        )

    @classmethod
    def from_config(cls, config_path: Path | None = None) -> "XGBoostPredictor":
        """Create an :class:`XGBoostPredictor` using hyperparameters from YAML config.

        Reads ``n_estimators``, ``max_depth``, and ``learning_rate`` from
        ``data/config/model_config.yaml`` (or *config_path* if provided).
        Falls back to defaults when the file is missing or unreadable.

        Args:
            config_path: Optional path to the YAML config file.  Defaults to
                ``data/config/model_config.yaml``.

        Returns:
            A new :class:`XGBoostPredictor` initialised with config values.
        """
        cfg = load_config(config_path)
        return cls(
            n_estimators=cfg.xgboost_n_estimators,
            max_depth=cfg.xgboost_max_depth,
            learning_rate=cfg.xgboost_learning_rate,
        )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the model on feature matrix X and binary target y.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
            y: Binary target vector of shape (n_samples,) where 1 = home win.
        """
        self.model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return predicted home-win probabilities.

        Args:
            X: Feature matrix of shape (n_samples, n_features).

        Returns:
            1-D array of shape (n_samples,) with values in [0.0, 1.0].
        """
        return self.model.predict_proba(X)[:, 1]

    def save(self, path: Path) -> None:
        """Persist the trained model to a JSON file.

        Args:
            path: Destination file path (e.g. data/models/xgboost_model.json).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(path))

    def load(self, path: Path) -> None:
        """Load a previously saved model from a JSON file.

        Args:
            path: Path to the saved model file.

        Raises:
            FileNotFoundError: If the model file does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        self.model.load_model(str(path))

    def feature_importance(self) -> dict[str, float]:
        """Return feature importance scores keyed by feature name.

        Returns:
            Dict mapping feature name to importance score (gain).
            All values are non-negative floats.
        """
        importances: np.ndarray = self.model.feature_importances_
        return dict(zip(FEATURE_NAMES, importances.astype(float).tolist()))
