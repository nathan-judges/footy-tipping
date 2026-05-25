"""Unit tests for the simplified configuration loader (scripts/lib/config.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib.config import ModelConfig, load_config


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "model_config.yaml"
    p.write_text(content)
    return p


class TestLoadConfig:
    def test_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(config, ModelConfig)
        assert config.xgboost_n_estimators == 100
        assert config.xgboost_max_depth == 4
        assert config.xgboost_learning_rate == pytest.approx(0.1)

    def test_loads_xgboost_hyperparameters(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, """
xgboost:
  n_estimators: 200
  max_depth: 6
  learning_rate: 0.05
ensemble_weights:
  elo: 0.40
  xgboost: 0.35
  market: 0.25
""")
        config = load_config(path)
        assert config.xgboost_n_estimators == 200
        assert config.xgboost_max_depth == 6
        assert config.xgboost_learning_rate == pytest.approx(0.05)

    def test_loads_ensemble_weights(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, """
xgboost:
  n_estimators: 100
  max_depth: 4
  learning_rate: 0.1
ensemble_weights:
  elo: 0.50
  xgboost: 0.30
  market: 0.20
""")
        config = load_config(path)
        assert config.ensemble_weights["elo"] == pytest.approx(0.50)
        assert config.ensemble_weights["xgboost"] == pytest.approx(0.30)
        assert config.ensemble_weights["market"] == pytest.approx(0.20)

    def test_partial_config_uses_defaults_for_missing_keys(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, """
xgboost:
  n_estimators: 50
""")
        config = load_config(path)
        assert config.xgboost_n_estimators == 50
        # Missing keys fall back to defaults
        assert config.xgboost_max_depth == 4
        assert config.xgboost_learning_rate == pytest.approx(0.1)
        assert config.ensemble_weights["elo"] == pytest.approx(0.40)

    def test_empty_yaml_returns_defaults(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, "")
        config = load_config(path)
        assert config.xgboost_n_estimators == 100

    def test_default_ensemble_weights_sum_to_one(self) -> None:
        config = ModelConfig()
        total = sum(config.ensemble_weights.values())
        assert total == pytest.approx(1.0)
