"""Unit tests for configuration management (scripts/lib/config.py).

Validates: Requirements 18.3
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from scripts.lib.config import (
    ConfigValidationError,
    ModelConfig,
    get_default_config,
    load_config,
    validate_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path: Path, content: str) -> Path:
    """Write a YAML config file and return its path."""
    p = tmp_path / "model_config.yaml"
    p.write_text(textwrap.dedent(content))
    return p


def _write_json(tmp_path: Path, data: dict) -> Path:
    """Write a JSON config file and return its path."""
    p = tmp_path / "model_config.json"
    p.write_text(json.dumps(data))
    return p


def _minimal_yaml() -> str:
    """Return a minimal but fully valid YAML config string."""
    return """
        model:
          version: "v2.1"
          features:
            version: "v2.1"
            enable_weather: true
            enable_injuries: true
            enable_travel: true
            enable_origin_tracking: true
          ensemble:
            sub_models: [elo, xgboost, neural]
            optimization_objective: brier
          calibration:
            enabled: true
            method: isotonic
          uncertainty:
            enabled: true
            bootstrap_samples: 100
            confidence_level: 0.90
          retraining:
            enabled: true
            accuracy_threshold: 0.55
            window_size: 4
            min_games_before_check: 16
        apis:
          weather:
            provider: openweathermap
            api_key_env: WEATHER_API_KEY
            cache_enabled: true
            fallback_to_averages: true
          odds:
            provider: the-odds-api
            api_key_env: ODDS_API_KEY
            fallback_enabled: true
        feature_flags:
          use_gradient_boosting: true
          use_neural_network: true
          use_ensemble_stacking: true
          enable_prediction_explanations: true
          enable_confidence_intervals: true
          enable_dashboard: true
    """


def _minimal_dict() -> dict:
    """Return the same config as a plain Python dict (for JSON tests)."""
    return {
        "model": {
            "version": "v2.1",
            "features": {
                "version": "v2.1",
                "enable_weather": True,
                "enable_injuries": True,
                "enable_travel": True,
                "enable_origin_tracking": True,
            },
            "ensemble": {
                "sub_models": ["elo", "xgboost", "neural"],
                "optimization_objective": "brier",
            },
            "calibration": {"enabled": True, "method": "isotonic"},
            "uncertainty": {
                "enabled": True,
                "bootstrap_samples": 100,
                "confidence_level": 0.90,
            },
            "retraining": {
                "enabled": True,
                "accuracy_threshold": 0.55,
                "window_size": 4,
                "min_games_before_check": 16,
            },
        },
        "apis": {
            "weather": {
                "provider": "openweathermap",
                "api_key_env": "WEATHER_API_KEY",
                "cache_enabled": True,
                "fallback_to_averages": True,
            },
            "odds": {
                "provider": "the-odds-api",
                "api_key_env": "ODDS_API_KEY",
                "fallback_enabled": True,
            },
        },
        "feature_flags": {
            "use_gradient_boosting": True,
            "use_neural_network": True,
            "use_ensemble_stacking": True,
            "enable_prediction_explanations": True,
            "enable_confidence_intervals": True,
            "enable_dashboard": True,
        },
    }


# ---------------------------------------------------------------------------
# Configuration loading — YAML
# ---------------------------------------------------------------------------


class TestLoadConfigYaml:
    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _minimal_yaml())
        config = load_config(path)
        assert isinstance(config, ModelConfig)

    def test_version_parsed_correctly(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _minimal_yaml())
        config = load_config(path)
        assert config.version == "v2.1"
        assert config.feature_version == "v2.1"

    def test_feature_flags_parsed(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _minimal_yaml())
        config = load_config(path)
        assert config.feature_flags["use_gradient_boosting"] is True
        assert config.feature_flags["enable_dashboard"] is True

    def test_ensemble_sub_models_parsed(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _minimal_yaml())
        config = load_config(path)
        assert config.ensemble_sub_models == ["elo", "xgboost", "neural"]

    def test_numeric_fields_parsed(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _minimal_yaml())
        config = load_config(path)
        assert config.bootstrap_samples == 100
        assert config.confidence_level == pytest.approx(0.90)
        assert config.accuracy_threshold == pytest.approx(0.55)
        assert config.window_size == 4
        assert config.min_games_before_check == 16

    def test_boolean_feature_fields_parsed(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _minimal_yaml())
        config = load_config(path)
        assert config.enable_weather is True
        assert config.enable_injuries is True
        assert config.enable_travel is True
        assert config.calibration_enabled is True
        assert config.uncertainty_enabled is True
        assert config.retraining_enabled is True

    def test_api_fields_parsed(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, _minimal_yaml())
        config = load_config(path)
        assert config.weather_provider == "openweathermap"
        assert config.weather_api_key_env == "WEATHER_API_KEY"
        assert config.weather_cache_enabled is True
        assert config.weather_fallback is True
        assert config.odds_provider == "the-odds-api"
        assert config.odds_fallback is True


# ---------------------------------------------------------------------------
# Configuration loading — JSON
# ---------------------------------------------------------------------------


class TestLoadConfigJson:
    def test_loads_valid_json(self, tmp_path: Path) -> None:
        path = _write_json(tmp_path, _minimal_dict())
        config = load_config(path)
        assert isinstance(config, ModelConfig)

    def test_json_values_match_yaml(self, tmp_path: Path) -> None:
        yaml_config = load_config(_write_yaml(tmp_path / "y", _minimal_yaml()) if False else _write_yaml(tmp_path, _minimal_yaml()))
        # Re-use tmp_path with a different filename
        json_path = tmp_path / "model_config.json"
        json_path.write_text(json.dumps(_minimal_dict()))
        json_config = load_config(json_path)

        assert yaml_config.version == json_config.version
        assert yaml_config.ensemble_sub_models == json_config.ensemble_sub_models
        assert yaml_config.optimization_objective == json_config.optimization_objective
        assert yaml_config.bootstrap_samples == json_config.bootstrap_samples

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "config.toml"
        p.write_text("[model]\nversion = 'v2.1'\n")
        with pytest.raises(ValueError, match="Unsupported config file format"):
            load_config(p)


# ---------------------------------------------------------------------------
# Missing / absent config file
# ---------------------------------------------------------------------------


class TestMissingConfigFile:
    def test_returns_default_when_file_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.yaml"
        config = load_config(missing)
        assert isinstance(config, ModelConfig)

    def test_default_config_has_safe_feature_flags(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "nonexistent.yaml")
        # Default config disables expensive components
        assert config.enable_weather is False
        assert config.enable_injuries is False
        assert config.feature_flags["use_gradient_boosting"] is False
        assert config.feature_flags["use_neural_network"] is False

    def test_default_config_is_valid(self) -> None:
        config = get_default_config()
        # Should not raise
        validate_config(config)


# ---------------------------------------------------------------------------
# Schema validation — valid configs
# ---------------------------------------------------------------------------


class TestValidateConfigValid:
    def test_valid_config_does_not_raise(self, tmp_path: Path) -> None:
        config = load_config(_write_yaml(tmp_path, _minimal_yaml()))
        # validate_config is called inside load_config; calling again is fine
        validate_config(config)

    def test_logloss_objective_is_valid(self, tmp_path: Path) -> None:
        data = _minimal_dict()
        data["model"]["ensemble"]["optimization_objective"] = "logloss"
        config = load_config(_write_json(tmp_path, data))
        assert config.optimization_objective == "logloss"

    def test_accuracy_objective_is_valid(self, tmp_path: Path) -> None:
        data = _minimal_dict()
        data["model"]["ensemble"]["optimization_objective"] = "accuracy"
        config = load_config(_write_json(tmp_path, data))
        assert config.optimization_objective == "accuracy"

    def test_platt_calibration_is_valid(self, tmp_path: Path) -> None:
        data = _minimal_dict()
        data["model"]["calibration"]["method"] = "platt"
        config = load_config(_write_json(tmp_path, data))
        assert config.calibration_method == "platt"

    def test_weatherapi_provider_is_valid(self, tmp_path: Path) -> None:
        data = _minimal_dict()
        data["apis"]["weather"]["provider"] = "weatherapi"
        config = load_config(_write_json(tmp_path, data))
        assert config.weather_provider == "weatherapi"


# ---------------------------------------------------------------------------
# Schema validation — invalid configs
# ---------------------------------------------------------------------------


class TestValidateConfigInvalid:
    def test_invalid_optimization_objective_raises(self) -> None:
        config = get_default_config()
        config.optimization_objective = "invalid_objective"
        with pytest.raises(ConfigValidationError, match="optimization_objective"):
            validate_config(config)

    def test_invalid_calibration_method_raises(self) -> None:
        config = get_default_config()
        config.calibration_method = "unknown_method"
        with pytest.raises(ConfigValidationError, match="calibration.method"):
            validate_config(config)

    def test_invalid_weather_provider_raises(self) -> None:
        config = get_default_config()
        config.weather_provider = "fake_provider"
        with pytest.raises(ConfigValidationError, match="weather.provider"):
            validate_config(config)

    def test_zero_bootstrap_samples_raises(self) -> None:
        config = get_default_config()
        config.bootstrap_samples = 0
        with pytest.raises(ConfigValidationError, match="bootstrap_samples"):
            validate_config(config)

    def test_negative_bootstrap_samples_raises(self) -> None:
        config = get_default_config()
        config.bootstrap_samples = -10
        with pytest.raises(ConfigValidationError, match="bootstrap_samples"):
            validate_config(config)

    def test_confidence_level_zero_raises(self) -> None:
        config = get_default_config()
        config.confidence_level = 0.0
        with pytest.raises(ConfigValidationError, match="confidence_level"):
            validate_config(config)

    def test_confidence_level_one_raises(self) -> None:
        config = get_default_config()
        config.confidence_level = 1.0
        with pytest.raises(ConfigValidationError, match="confidence_level"):
            validate_config(config)

    def test_accuracy_threshold_zero_raises(self) -> None:
        config = get_default_config()
        config.accuracy_threshold = 0.0
        with pytest.raises(ConfigValidationError, match="accuracy_threshold"):
            validate_config(config)

    def test_accuracy_threshold_one_raises(self) -> None:
        config = get_default_config()
        config.accuracy_threshold = 1.0
        with pytest.raises(ConfigValidationError, match="accuracy_threshold"):
            validate_config(config)

    def test_zero_window_size_raises(self) -> None:
        config = get_default_config()
        config.window_size = 0
        with pytest.raises(ConfigValidationError, match="window_size"):
            validate_config(config)

    def test_empty_sub_models_raises(self) -> None:
        config = get_default_config()
        config.ensemble_sub_models = []
        with pytest.raises(ConfigValidationError, match="sub_models"):
            validate_config(config)

    def test_empty_version_raises(self) -> None:
        config = get_default_config()
        config.version = ""
        with pytest.raises(ConfigValidationError, match="version"):
            validate_config(config)

    def test_missing_feature_flag_key_raises(self) -> None:
        config = get_default_config()
        del config.feature_flags["use_gradient_boosting"]
        with pytest.raises(ConfigValidationError, match="use_gradient_boosting"):
            validate_config(config)

    def test_non_boolean_feature_flag_raises(self) -> None:
        config = get_default_config()
        config.feature_flags["use_gradient_boosting"] = "yes"  # type: ignore[assignment]
        with pytest.raises(ConfigValidationError, match="use_gradient_boosting"):
            validate_config(config)

    def test_invalid_yaml_raises_on_load(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("model: [this, is, not, a, dict")
        with pytest.raises(Exception):
            load_config(p)

    def test_non_dict_top_level_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("- item1\n- item2\n")
        with pytest.raises(ConfigValidationError, match="top level"):
            load_config(p)


# ---------------------------------------------------------------------------
# Environment-specific config selection
# ---------------------------------------------------------------------------


class TestEnvironmentConfig:
    def _yaml_with_env_overrides(self) -> str:
        return textwrap.dedent("""
            model:
              version: "v2.1"
              features:
                version: "v2.1"
                enable_weather: true
                enable_injuries: true
                enable_travel: true
                enable_origin_tracking: true
              ensemble:
                sub_models: [elo, xgboost, neural]
                optimization_objective: brier
              calibration:
                enabled: true
                method: isotonic
              uncertainty:
                enabled: true
                bootstrap_samples: 100
                confidence_level: 0.90
              retraining:
                enabled: true
                accuracy_threshold: 0.55
                window_size: 4
                min_games_before_check: 16
            apis:
              weather:
                provider: openweathermap
                api_key_env: WEATHER_API_KEY
                cache_enabled: true
                fallback_to_averages: true
              odds:
                provider: the-odds-api
                api_key_env: ODDS_API_KEY
                fallback_enabled: true
            feature_flags:
              use_gradient_boosting: true
              use_neural_network: true
              use_ensemble_stacking: true
              enable_prediction_explanations: true
              enable_confidence_intervals: true
              enable_dashboard: true
            environments:
              development:
                model:
                  retraining:
                    enabled: false
                  uncertainty:
                    bootstrap_samples: 10
                apis:
                  weather:
                    cache_enabled: false
                feature_flags:
                  use_gradient_boosting: false
                  use_neural_network: false
                  use_ensemble_stacking: false
                  enable_prediction_explanations: false
                  enable_confidence_intervals: false
                  enable_dashboard: false
        """)

    def test_production_environment_uses_base_config(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, self._yaml_with_env_overrides())
        config = load_config(path, environment="production")
        assert config.retraining_enabled is True
        assert config.bootstrap_samples == 100
        assert config.weather_cache_enabled is True
        assert config.feature_flags["use_gradient_boosting"] is True

    def test_development_environment_applies_overrides(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, self._yaml_with_env_overrides())
        config = load_config(path, environment="development")
        assert config.retraining_enabled is False
        assert config.bootstrap_samples == 10
        assert config.weather_cache_enabled is False

    def test_development_disables_expensive_feature_flags(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, self._yaml_with_env_overrides())
        config = load_config(path, environment="development")
        assert config.feature_flags["use_gradient_boosting"] is False
        assert config.feature_flags["use_neural_network"] is False
        assert config.feature_flags["use_ensemble_stacking"] is False
        assert config.feature_flags["enable_dashboard"] is False

    def test_unknown_environment_falls_back_to_base(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, self._yaml_with_env_overrides())
        config = load_config(path, environment="staging")
        # No staging overrides → base config values
        assert config.retraining_enabled is True
        assert config.bootstrap_samples == 100

    def test_production_and_development_differ_on_retraining(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, self._yaml_with_env_overrides())
        prod = load_config(path, environment="production")
        dev = load_config(path, environment="development")
        assert prod.retraining_enabled is True
        assert dev.retraining_enabled is False

    def test_non_overridden_fields_unchanged_in_development(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path, self._yaml_with_env_overrides())
        config = load_config(path, environment="development")
        # Fields not in the development override block stay at base values
        assert config.version == "v2.1"
        assert config.optimization_objective == "brier"
        assert config.calibration_method == "isotonic"
        assert config.accuracy_threshold == pytest.approx(0.55)

    def test_default_environment_is_production(self, tmp_path: Path) -> None:
        """load_config with no environment arg should behave like production."""
        path = _write_yaml(tmp_path, self._yaml_with_env_overrides())
        config_default = load_config(path)
        config_prod = load_config(path, environment="production")
        assert config_default.retraining_enabled == config_prod.retraining_enabled
        assert config_default.bootstrap_samples == config_prod.bootstrap_samples


# ---------------------------------------------------------------------------
# Default config helper
# ---------------------------------------------------------------------------


class TestGetDefaultConfig:
    def test_returns_model_config_instance(self) -> None:
        config = get_default_config()
        assert isinstance(config, ModelConfig)

    def test_default_version(self) -> None:
        config = get_default_config()
        assert config.version == "v2.1"

    def test_default_disables_weather_and_injuries(self) -> None:
        config = get_default_config()
        assert config.enable_weather is False
        assert config.enable_injuries is False

    def test_default_enables_travel_and_origin(self) -> None:
        config = get_default_config()
        assert config.enable_travel is True
        assert config.enable_origin_tracking is True

    def test_default_feature_flags_all_false(self) -> None:
        config = get_default_config()
        assert all(not v for v in config.feature_flags.values())

    def test_default_retraining_disabled(self) -> None:
        config = get_default_config()
        assert config.retraining_enabled is False

    def test_default_calibration_disabled(self) -> None:
        config = get_default_config()
        assert config.calibration_enabled is False

    def test_default_uncertainty_disabled(self) -> None:
        config = get_default_config()
        assert config.uncertainty_enabled is False
