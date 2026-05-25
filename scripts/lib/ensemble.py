"""Ensemble weight optimization for the NRL prediction pipeline.

Provides data-driven weight optimization using scipy constrained
optimization to minimize Brier score on validation data.

Optimized weights are persisted to data/config/model_config.yaml
under the ``ensemble_weights`` key.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path("data/config/model_config.yaml")


def _brier_score(weights: np.ndarray, predictions: np.ndarray, actuals: np.ndarray) -> float:
    """Compute Brier score for a weighted ensemble.

    Args:
        weights: 1-D array of sub-model weights (must sum to 1).
        predictions: 2-D array of shape (n_models, n_games) with home-win
            probabilities from each sub-model.
        actuals: 1-D binary array of shape (n_games,) where 1 = home win.

    Returns:
        Mean squared error of the weighted ensemble probabilities.
    """
    ensemble_probs = predictions.T @ weights  # shape: (n_games,)
    return float(np.mean((ensemble_probs - actuals) ** 2))


def optimize_weights(
    predictions: dict[str, np.ndarray],
    actuals: np.ndarray,
) -> dict[str, float]:
    """Find ensemble weights that minimize Brier score via scipy SLSQP.

    Constraints:
    - All weights >= 0 (non-negative)
    - Weights sum to 1.0

    Falls back to equal weights if optimization fails or scipy is unavailable.

    Args:
        predictions: Mapping of model name to 1-D array of home-win
            probabilities (one value per game).  All arrays must have the
            same length as *actuals*.
        actuals: 1-D binary array where 1 = home win, 0 = away win.

    Returns:
        Dict mapping model name to optimized weight.  Weights sum to 1.0
        and are all non-negative.

    Example::

        weights = optimize_weights(
            predictions={
                "elo": elo_probs,
                "xgboost": xgb_probs,
                "market": market_probs,
            },
            actuals=np.array([1, 0, 1, 1, 0]),
        )
        # {"elo": 0.35, "xgboost": 0.40, "market": 0.25}
    """
    model_names = list(predictions.keys())
    n_models = len(model_names)

    if n_models == 0:
        return {}

    if n_models == 1:
        return {model_names[0]: 1.0}

    # Stack predictions into a (n_models, n_games) matrix
    pred_matrix = np.stack([predictions[name] for name in model_names], axis=0)
    actuals_arr = np.asarray(actuals, dtype=float)

    # Equal weights as starting point and fallback
    equal_weights = np.ones(n_models) / n_models

    try:
        from scipy.optimize import minimize  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("scipy not available — using equal ensemble weights")
        return dict(zip(model_names, equal_weights.tolist()))

    # Constraints: weights sum to 1.0
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    # Bounds: each weight in [0, 1]
    bounds = [(0.0, 1.0)] * n_models

    try:
        result = minimize(
            fun=_brier_score,
            x0=equal_weights,
            args=(pred_matrix, actuals_arr),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        if result.success:
            optimized = np.clip(result.x, 0.0, 1.0)
            # Re-normalize to ensure exact sum-to-1 after clipping
            total = optimized.sum()
            if total > 0:
                optimized = optimized / total
            else:
                optimized = equal_weights
            logger.info(
                "Ensemble weight optimization succeeded (Brier: %.4f → %.4f)",
                _brier_score(equal_weights, pred_matrix, actuals_arr),
                _brier_score(optimized, pred_matrix, actuals_arr),
            )
            return dict(zip(model_names, optimized.tolist()))
        else:
            logger.warning(
                "Ensemble weight optimization did not converge (%s) — using equal weights",
                result.message,
            )
            return dict(zip(model_names, equal_weights.tolist()))

    except Exception as exc:
        logger.warning("Ensemble weight optimization failed: %s — using equal weights", exc)
        return dict(zip(model_names, equal_weights.tolist()))


def save_weights(
    weights: dict[str, float],
    config_path: Path | None = None,
) -> None:
    """Persist optimized ensemble weights to the YAML config file.

    Updates only the ``ensemble_weights`` section; all other config
    values are preserved.

    Args:
        weights: Dict mapping model name to weight (must sum to ~1.0).
        config_path: Path to the YAML config file.  Defaults to
            ``data/config/model_config.yaml``.
    """
    path = config_path or _DEFAULT_CONFIG_PATH

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("PyYAML not available — cannot save ensemble weights")
        return

    # Load existing config to preserve other sections
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            logger.warning("Could not read existing config at %s: %s", path, exc)

    existing["ensemble_weights"] = {k: round(float(v), 6) for k, v in weights.items()}

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(yaml.dump(existing, default_flow_style=False, sort_keys=False), encoding="utf-8")
        logger.info("Saved ensemble weights to %s: %s", path, weights)
    except Exception as exc:
        logger.warning("Failed to write config to %s: %s", path, exc)


def redistribute_weights(
    weights: dict[str, float],
    unavailable: set[str],
) -> dict[str, float]:
    """Redistribute weights from unavailable models proportionally to available ones.

    When a sub-model is unavailable (e.g. market odds missing, XGBoost model
    file not found), its weight is redistributed proportionally among the
    remaining models.

    Args:
        weights: Original weight mapping (should sum to ~1.0).
        unavailable: Set of model names that are not available.

    Returns:
        New weight mapping with unavailable models removed and remaining
        weights renormalized to sum to 1.0.

    Example::

        redistribute_weights(
            {"elo": 0.40, "xgboost": 0.35, "market": 0.25},
            unavailable={"market"},
        )
        # {"elo": 0.533..., "xgboost": 0.466...}
    """
    available = {k: v for k, v in weights.items() if k not in unavailable}
    if not available:
        # All models unavailable — return equal weights for all original models
        n = len(weights)
        return {k: 1.0 / n for k in weights} if n > 0 else {}

    total = sum(available.values())
    if total <= 0:
        n = len(available)
        return {k: 1.0 / n for k in available}

    return {k: v / total for k, v in available.items()}
