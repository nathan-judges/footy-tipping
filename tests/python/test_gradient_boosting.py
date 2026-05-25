"""Unit tests for the XGBoost model wrapper (scripts/lib/models/gradient_boosting.py)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts.lib.features import FEATURE_NAMES
from scripts.lib.models.gradient_boosting import XGBoostPredictor

N_FEATURES = len(FEATURE_NAMES)


def _make_data(n_samples: int = 100, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n_samples, N_FEATURES)).astype(np.float32)
    y = rng.integers(0, 2, size=n_samples).astype(np.float32)
    return X, y


class TestInitialisation:
    def test_default_init(self) -> None:
        predictor = XGBoostPredictor()
        assert predictor.model is not None

    def test_hyperparameter_overrides(self) -> None:
        predictor = XGBoostPredictor(n_estimators=50, max_depth=3, learning_rate=0.05)
        params = predictor.model.get_params()
        assert params["n_estimators"] == 50
        assert params["max_depth"] == 3
        assert params["learning_rate"] == pytest.approx(0.05)

    def test_from_config_loads_yaml(self, tmp_path: Path) -> None:
        """from_config() reads n_estimators, max_depth, learning_rate from YAML."""
        config_file = tmp_path / "model_config.yaml"
        config_file.write_text(
            "xgboost:\n  n_estimators: 42\n  max_depth: 3\n  learning_rate: 0.05\n"
        )
        predictor = XGBoostPredictor.from_config(config_file)
        params = predictor.model.get_params()
        assert params["n_estimators"] == 42
        assert params["max_depth"] == 3
        assert params["learning_rate"] == pytest.approx(0.05)

    def test_from_config_falls_back_to_defaults_when_missing(self, tmp_path: Path) -> None:
        """from_config() uses defaults when the config file does not exist."""
        predictor = XGBoostPredictor.from_config(tmp_path / "nonexistent.yaml")
        params = predictor.model.get_params()
        assert params["n_estimators"] == 100
        assert params["max_depth"] == 4
        assert params["learning_rate"] == pytest.approx(0.1)


class TestTraining:
    def test_train_completes(self) -> None:
        predictor = XGBoostPredictor(n_estimators=10)
        X, y = _make_data()
        predictor.train(X, y)
        assert hasattr(predictor.model, "feature_importances_")

    def test_train_small_dataset(self) -> None:
        predictor = XGBoostPredictor(n_estimators=5)
        X, y = _make_data(n_samples=10)
        predictor.train(X, y)
        assert hasattr(predictor.model, "feature_importances_")


class TestPredictProba:
    def test_output_shape(self) -> None:
        predictor = XGBoostPredictor(n_estimators=10)
        X, y = _make_data()
        predictor.train(X, y)
        X_test, _ = _make_data(n_samples=15, seed=7)
        probs = predictor.predict_proba(X_test)
        assert probs.ndim == 1
        assert len(probs) == 15

    def test_values_in_unit_interval(self) -> None:
        predictor = XGBoostPredictor(n_estimators=10)
        X, y = _make_data()
        predictor.train(X, y)
        X_test, _ = _make_data(n_samples=50, seed=13)
        probs = predictor.predict_proba(X_test)
        assert np.all(probs >= 0.0)
        assert np.all(probs <= 1.0)

    def test_single_sample(self) -> None:
        predictor = XGBoostPredictor(n_estimators=10)
        X, y = _make_data()
        predictor.train(X, y)
        rng = np.random.default_rng(55)
        X_single = rng.standard_normal((1, N_FEATURES)).astype(np.float32)
        probs = predictor.predict_proba(X_single)
        assert len(probs) == 1
        assert 0.0 <= float(probs[0]) <= 1.0


class TestSaveLoad:
    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        predictor = XGBoostPredictor(n_estimators=10)
        X, y = _make_data()
        predictor.train(X, y)

        model_path = tmp_path / "xgboost_model.json"
        predictor.save(model_path)
        assert model_path.exists()

        loaded = XGBoostPredictor(n_estimators=10)
        loaded.load(model_path)

        X_test, _ = _make_data(n_samples=10, seed=99)
        original_probs = predictor.predict_proba(X_test)
        loaded_probs = loaded.predict_proba(X_test)
        np.testing.assert_allclose(original_probs, loaded_probs, rtol=1e-5)

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        predictor = XGBoostPredictor()
        with pytest.raises(FileNotFoundError):
            predictor.load(tmp_path / "nonexistent.json")

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        predictor = XGBoostPredictor(n_estimators=5)
        X, y = _make_data()
        predictor.train(X, y)
        nested_path = tmp_path / "data" / "models" / "xgboost_model.json"
        predictor.save(nested_path)
        assert nested_path.exists()


class TestFeatureImportance:
    def test_keys_match_feature_names(self) -> None:
        predictor = XGBoostPredictor(n_estimators=10)
        X, y = _make_data()
        predictor.train(X, y)
        importance = predictor.feature_importance()
        assert set(importance.keys()) == set(FEATURE_NAMES)

    def test_values_are_non_negative(self) -> None:
        predictor = XGBoostPredictor(n_estimators=10)
        X, y = _make_data()
        predictor.train(X, y)
        importance = predictor.feature_importance()
        assert all(v >= 0.0 for v in importance.values())

    def test_at_least_one_nonzero(self) -> None:
        predictor = XGBoostPredictor(n_estimators=10)
        X, y = _make_data()
        predictor.train(X, y)
        importance = predictor.feature_importance()
        assert any(v > 0.0 for v in importance.values())
