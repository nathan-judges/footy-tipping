"""Tests for ensemble weight optimization (scripts/lib/ensemble.py).

Covers:
- Weight optimization constraints (sum to 1, non-negative) — Requirements 5.1, 5.2
- Missing model fallback / weight redistribution — Requirements 4.5, 5.4
- save_weights / persist round-trip
- Edge cases: single model, empty predictions, optimization failure fallback
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts.lib.ensemble import optimize_weights, redistribute_weights, save_weights


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_predictions(n_games: int = 50, seed: int = 42) -> dict[str, np.ndarray]:
    """Generate synthetic model predictions for testing."""
    rng = np.random.default_rng(seed)
    return {
        "elo": rng.uniform(0.3, 0.7, n_games),
        "xgboost": rng.uniform(0.3, 0.7, n_games),
        "market": rng.uniform(0.3, 0.7, n_games),
    }


def _make_actuals(n_games: int = 50, seed: int = 99) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2, n_games).astype(float)


# ---------------------------------------------------------------------------
# optimize_weights: constraint tests
# ---------------------------------------------------------------------------

class TestOptimizeWeightsConstraints:
    """Validates: Requirements 5.1, 5.2"""

    def test_weights_sum_to_one(self) -> None:
        """Optimized weights must sum to exactly 1.0."""
        predictions = _make_predictions()
        actuals = _make_actuals()
        weights = optimize_weights(predictions, actuals)
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-6, f"Weights sum to {total}, expected 1.0"

    def test_weights_non_negative(self) -> None:
        """All optimized weights must be >= 0."""
        predictions = _make_predictions()
        actuals = _make_actuals()
        weights = optimize_weights(predictions, actuals)
        for name, w in weights.items():
            assert w >= 0.0, f"Weight for '{name}' is negative: {w}"

    def test_weights_keys_match_input_models(self) -> None:
        """Output keys must match the input model names."""
        predictions = _make_predictions()
        actuals = _make_actuals()
        weights = optimize_weights(predictions, actuals)
        assert set(weights.keys()) == set(predictions.keys())

    def test_weights_sum_to_one_two_models(self) -> None:
        """Constraint holds with only two models."""
        rng = np.random.default_rng(7)
        predictions = {
            "elo": rng.uniform(0.3, 0.7, 40),
            "market": rng.uniform(0.3, 0.7, 40),
        }
        actuals = rng.integers(0, 2, 40).astype(float)
        weights = optimize_weights(predictions, actuals)
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        for w in weights.values():
            assert w >= 0.0

    def test_weights_sum_to_one_many_models(self) -> None:
        """Constraint holds with four models."""
        rng = np.random.default_rng(13)
        n = 60
        predictions = {
            "elo": rng.uniform(0.3, 0.7, n),
            "xgboost": rng.uniform(0.3, 0.7, n),
            "market": rng.uniform(0.3, 0.7, n),
            "features": rng.uniform(0.3, 0.7, n),
        }
        actuals = rng.integers(0, 2, n).astype(float)
        weights = optimize_weights(predictions, actuals)
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        for w in weights.values():
            assert w >= 0.0

    def test_optimization_improves_or_matches_equal_weights(self) -> None:
        """Optimized Brier score should be <= equal-weight Brier score."""
        predictions = _make_predictions(n_games=100)
        actuals = _make_actuals(n_games=100)
        weights = optimize_weights(predictions, actuals)

        n_models = len(predictions)
        equal_w = 1.0 / n_models
        pred_matrix = np.stack(list(predictions.values()), axis=0)

        equal_brier = float(np.mean((pred_matrix.T @ np.full(n_models, equal_w) - actuals) ** 2))
        opt_w_arr = np.array([weights[k] for k in predictions])
        opt_brier = float(np.mean((pred_matrix.T @ opt_w_arr - actuals) ** 2))

        assert opt_brier <= equal_brier + 1e-6, (
            f"Optimized Brier ({opt_brier:.6f}) worse than equal weights ({equal_brier:.6f})"
        )


# ---------------------------------------------------------------------------
# optimize_weights: edge cases
# ---------------------------------------------------------------------------

class TestOptimizeWeightsEdgeCases:
    def test_single_model_returns_weight_one(self) -> None:
        """Single model should get weight 1.0."""
        rng = np.random.default_rng(1)
        predictions = {"elo": rng.uniform(0.3, 0.7, 30)}
        actuals = rng.integers(0, 2, 30).astype(float)
        weights = optimize_weights(predictions, actuals)
        assert weights == {"elo": 1.0}

    def test_empty_predictions_returns_empty(self) -> None:
        """Empty predictions dict returns empty weights."""
        weights = optimize_weights({}, np.array([1, 0, 1]))
        assert weights == {}

    def test_identical_models_equal_weights(self) -> None:
        """When all models are identical, weights should be equal (sum to 1)."""
        rng = np.random.default_rng(5)
        probs = rng.uniform(0.3, 0.7, 50)
        actuals = rng.integers(0, 2, 50).astype(float)
        predictions = {"a": probs.copy(), "b": probs.copy()}
        weights = optimize_weights(predictions, actuals)
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        for w in weights.values():
            assert w >= 0.0


# ---------------------------------------------------------------------------
# redistribute_weights: missing model fallback
# ---------------------------------------------------------------------------

class TestRedistributeWeights:
    """Validates: Requirements 4.5, 5.4"""

    def test_redistribute_removes_unavailable_model(self) -> None:
        """Unavailable model should not appear in output."""
        weights = {"elo": 0.40, "xgboost": 0.35, "market": 0.25}
        result = redistribute_weights(weights, unavailable={"market"})
        assert "market" not in result

    def test_redistribute_sums_to_one(self) -> None:
        """Redistributed weights must still sum to 1.0."""
        weights = {"elo": 0.40, "xgboost": 0.35, "market": 0.25}
        result = redistribute_weights(weights, unavailable={"market"})
        assert abs(sum(result.values()) - 1.0) < 1e-9

    def test_redistribute_non_negative(self) -> None:
        """Redistributed weights must be non-negative."""
        weights = {"elo": 0.40, "xgboost": 0.35, "market": 0.25}
        result = redistribute_weights(weights, unavailable={"xgboost"})
        for w in result.values():
            assert w >= 0.0

    def test_redistribute_xgboost_missing(self) -> None:
        """When XGBoost is unavailable, its weight is redistributed to ELO and market."""
        weights = {"elo": 0.40, "xgboost": 0.35, "market": 0.25}
        result = redistribute_weights(weights, unavailable={"xgboost"})
        assert "xgboost" not in result
        assert abs(sum(result.values()) - 1.0) < 1e-9
        assert result["elo"] > 0.40  # ELO should have received some of XGBoost's weight
        assert result["market"] > 0.25

    def test_redistribute_proportional(self) -> None:
        """Redistribution should be proportional to existing weights."""
        weights = {"elo": 0.40, "xgboost": 0.35, "market": 0.25}
        result = redistribute_weights(weights, unavailable={"xgboost"})
        # elo:market ratio should be preserved: 0.40/0.25 = 1.6
        ratio = result["elo"] / result["market"]
        assert abs(ratio - 0.40 / 0.25) < 1e-6

    def test_redistribute_no_unavailable(self) -> None:
        """With no unavailable models, weights are returned unchanged."""
        weights = {"elo": 0.40, "xgboost": 0.35, "market": 0.25}
        result = redistribute_weights(weights, unavailable=set())
        assert abs(result["elo"] - 0.40) < 1e-9
        assert abs(result["xgboost"] - 0.35) < 1e-9
        assert abs(result["market"] - 0.25) < 1e-9

    def test_redistribute_all_unavailable_returns_equal(self) -> None:
        """When all models are unavailable, return equal weights for all."""
        weights = {"elo": 0.40, "xgboost": 0.35, "market": 0.25}
        result = redistribute_weights(weights, unavailable={"elo", "xgboost", "market"})
        # All unavailable — should return equal weights for all original models
        assert len(result) == 3
        for w in result.values():
            assert abs(w - 1 / 3) < 1e-9


# ---------------------------------------------------------------------------
# save_weights: persistence
# ---------------------------------------------------------------------------

class TestSaveWeights:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        config_path = tmp_path / "model_config.yaml"
        weights = {"elo": 0.40, "xgboost": 0.35, "market": 0.25}
        save_weights(weights, config_path=config_path)
        assert config_path.exists()

    def test_save_preserves_other_config_sections(self, tmp_path: Path) -> None:
        """save_weights should not overwrite xgboost hyperparameters."""
        config_path = tmp_path / "model_config.yaml"
        config_path.write_text(
            "xgboost:\n  n_estimators: 42\n  max_depth: 3\n  learning_rate: 0.05\n"
            "ensemble_weights:\n  elo: 0.40\n  xgboost: 0.35\n  market: 0.25\n"
        )
        new_weights = {"elo": 0.50, "xgboost": 0.30, "market": 0.20}
        save_weights(new_weights, config_path=config_path)

        import yaml  # type: ignore[import-untyped]
        data = yaml.safe_load(config_path.read_text())
        assert data["xgboost"]["n_estimators"] == 42
        assert abs(data["ensemble_weights"]["elo"] - 0.50) < 1e-6

    def test_save_and_reload_via_load_config(self, tmp_path: Path) -> None:
        """Weights saved by save_weights should be loadable via load_config."""
        config_path = tmp_path / "model_config.yaml"
        # Write a minimal config first
        config_path.write_text(
            "xgboost:\n  n_estimators: 100\n  max_depth: 4\n  learning_rate: 0.1\n"
        )
        weights = {"elo": 0.45, "xgboost": 0.30, "market": 0.25}
        save_weights(weights, config_path=config_path)

        from scripts.lib.config import load_config
        cfg = load_config(config_path)
        assert abs(cfg.ensemble_weights["elo"] - 0.45) < 1e-5
        assert abs(cfg.ensemble_weights["xgboost"] - 0.30) < 1e-5
        assert abs(cfg.ensemble_weights["market"] - 0.25) < 1e-5


# ---------------------------------------------------------------------------
# Missing XGBoost model fallback (integration-level)
# ---------------------------------------------------------------------------

class TestMissingModelFallback:
    """Validates: Requirements 4.5, 7.2"""

    def test_model_predict_without_xgboost_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EnsemblePredictor should work when xgboost_model.json is missing."""
        from scripts.lib.model import EnsemblePredictor
        from scripts.lib.types import Fixture

        # Point XGBoost model path to a non-existent file
        monkeypatch.setattr("scripts.lib.model._XGBOOST_MODEL_PATH", tmp_path / "nonexistent.json")

        predictor = EnsemblePredictor()
        predictor.initialize()

        assert not predictor._xgb_available
        assert predictor._xgb_predictor is None

        # Should still produce a valid prediction
        fixture = Fixture(
            game_id="2026-r01-g01",
            nrl_match_id="",
            nrl_slug="",
            home_team="Broncos",
            away_team="Storm",
            venue="Suncorp Stadium",
            kickoff_at="2026-03-05T19:50:00Z",
            status="upcoming",
        )
        result = predictor.predict_fixture(fixture)
        assert result.tip_team in ("Broncos", "Storm")
        assert 0.0 < result.confidence <= 1.0

    def test_xgboost_not_in_sub_predictions_when_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When XGBoost is unavailable, it should not appear in sub_predictions."""
        from scripts.lib.model import EnsemblePredictor
        from scripts.lib.types import Fixture

        monkeypatch.setattr("scripts.lib.model._XGBOOST_MODEL_PATH", tmp_path / "nonexistent.json")

        predictor = EnsemblePredictor()
        predictor.initialize()

        fixture = Fixture(
            game_id="2026-r01-g02",
            nrl_match_id="",
            nrl_slug="",
            home_team="Panthers",
            away_team="Roosters",
            venue="CommBank Stadium",
            kickoff_at="2026-03-06T19:50:00Z",
            status="upcoming",
        )
        result = predictor.predict_fixture(fixture)
        if result.diagnostics is not None:
            model_names = [sp.model_name for sp in result.diagnostics.sub_predictions]
            assert "xgboost" not in model_names
