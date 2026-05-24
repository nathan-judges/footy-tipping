"""Configuration management for the NRL prediction model system.

Loads model hyperparameters and feature flags from YAML/JSON configuration
files, supports environment-specific overrides, and validates configuration
on startup.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema constants used for validation
# ---------------------------------------------------------------------------

VALID_OPTIMIZATION_OBJECTIVES = {"brier", "logloss", "accuracy"}
VALID_CALIBRATION_METHODS = {"isotonic", "platt"}
VALID_WEATHER_PROVIDERS = {"openweathermap", "weatherapi"}
VALID_ODDS_PROVIDERS = {"the-odds-api"}
VALID_ENVIRONMENTS = {"development", "production"}

REQUIRED_FEATURE_FLAG_KEYS = {
    "use_gradient_boosting",
    "use_neural_network",
    "use_ensemble_stacking",
    "enable_prediction_explanations",
    "enable_confidence_intervals",
    "enable_dashboard",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ModelConfig:
    """Validated model configuration settings."""

    version: str
    feature_version: str
    enable_weather: bool
    enable_injuries: bool
    enable_travel: bool
    enable_origin_tracking: bool

    ensemble_sub_models: list[str]
    optimization_objective: str

    calibration_enabled: bool
    calibration_method: str

    uncertainty_enabled: bool
    bootstrap_samples: int
    confidence_level: float

    retraining_enabled: bool
    accuracy_threshold: float
    window_size: int
    min_games_before_check: int

    weather_provider: str
    weather_api_key_env: str
    weather_cache_enabled: bool
    weather_fallback: bool

    odds_provider: str
    odds_api_key_env: str
    odds_fallback: bool

    feature_flags: dict[str, bool] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ConfigValidationError(ValueError):
    """Raised when a configuration file fails schema validation."""


def validate_config(config: ModelConfig) -> None:
    """Validate a ModelConfig against the expected schema.

    Raises:
        ConfigValidationError: if any field is invalid.
    """
    errors: list[str] = []

    # Version strings must be non-empty
    if not config.version or not isinstance(config.version, str):
        errors.append("model.version must be a non-empty string")
    if not config.feature_version or not isinstance(config.feature_version, str):
        errors.append("model.features.version must be a non-empty string")

    # Ensemble
    if not config.ensemble_sub_models:
        errors.append("model.ensemble.sub_models must be a non-empty list")
    if config.optimization_objective not in VALID_OPTIMIZATION_OBJECTIVES:
        errors.append(
            f"model.ensemble.optimization_objective must be one of "
            f"{VALID_OPTIMIZATION_OBJECTIVES}, got '{config.optimization_objective}'"
        )

    # Calibration
    if config.calibration_method not in VALID_CALIBRATION_METHODS:
        errors.append(
            f"model.calibration.method must be one of "
            f"{VALID_CALIBRATION_METHODS}, got '{config.calibration_method}'"
        )

    # Uncertainty
    if config.bootstrap_samples < 1:
        errors.append("model.uncertainty.bootstrap_samples must be >= 1")
    if not (0.0 < config.confidence_level < 1.0):
        errors.append("model.uncertainty.confidence_level must be in (0, 1)")

    # Retraining
    if not (0.0 < config.accuracy_threshold < 1.0):
        errors.append("model.retraining.accuracy_threshold must be in (0, 1)")
    if config.window_size < 1:
        errors.append("model.retraining.window_size must be >= 1")
    if config.min_games_before_check < 1:
        errors.append("model.retraining.min_games_before_check must be >= 1")

    # APIs
    if config.weather_provider not in VALID_WEATHER_PROVIDERS:
        errors.append(
            f"apis.weather.provider must be one of "
            f"{VALID_WEATHER_PROVIDERS}, got '{config.weather_provider}'"
        )

    # Feature flags — all required keys must be present and boolean
    for key in REQUIRED_FEATURE_FLAG_KEYS:
        if key not in config.feature_flags:
            errors.append(f"feature_flags.{key} is required")
        elif not isinstance(config.feature_flags[key], bool):
            errors.append(f"feature_flags.{key} must be a boolean")

    if errors:
        raise ConfigValidationError(
            "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _parse_yaml_or_json(path: Path) -> dict[str, Any]:
    """Load a YAML or JSON file and return the parsed dict."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "PyYAML is required to load YAML config files. "
                "Install it with: pip install pyyaml"
            ) from exc
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        raise ValueError(f"Unsupported config file format: {suffix!r}")

    if not isinstance(data, dict):
        raise ConfigValidationError(
            f"Config file {path} must contain a YAML/JSON object at the top level"
        )
    return data


def _build_config_from_dict(config_data: dict[str, Any]) -> ModelConfig:
    """Construct a ModelConfig from a raw parsed config dict."""
    model = config_data.get("model", {})
    features = model.get("features", {})
    ensemble = model.get("ensemble", {})
    calibration = model.get("calibration", {})
    uncertainty = model.get("uncertainty", {})
    retraining = model.get("retraining", {})

    apis = config_data.get("apis", {})
    weather = apis.get("weather", {})
    odds = apis.get("odds", {})

    feature_flags = config_data.get("feature_flags", {})

    return ModelConfig(
        version=model.get("version", "v2.1"),
        feature_version=features.get("version", "v2.1"),
        enable_weather=bool(features.get("enable_weather", True)),
        enable_injuries=bool(features.get("enable_injuries", True)),
        enable_travel=bool(features.get("enable_travel", True)),
        enable_origin_tracking=bool(features.get("enable_origin_tracking", True)),
        ensemble_sub_models=list(ensemble.get("sub_models", ["elo", "xgboost", "neural"])),
        optimization_objective=str(ensemble.get("optimization_objective", "brier")),
        calibration_enabled=bool(calibration.get("enabled", True)),
        calibration_method=str(calibration.get("method", "isotonic")),
        uncertainty_enabled=bool(uncertainty.get("enabled", True)),
        bootstrap_samples=int(uncertainty.get("bootstrap_samples", 100)),
        confidence_level=float(uncertainty.get("confidence_level", 0.90)),
        retraining_enabled=bool(retraining.get("enabled", True)),
        accuracy_threshold=float(retraining.get("accuracy_threshold", 0.55)),
        window_size=int(retraining.get("window_size", 4)),
        min_games_before_check=int(retraining.get("min_games_before_check", 16)),
        weather_provider=str(weather.get("provider", "openweathermap")),
        weather_api_key_env=str(weather.get("api_key_env", "WEATHER_API_KEY")),
        weather_cache_enabled=bool(weather.get("cache_enabled", True)),
        weather_fallback=bool(weather.get("fallback_to_averages", True)),
        odds_provider=str(odds.get("provider", "the-odds-api")),
        odds_api_key_env=str(odds.get("api_key_env", "ODDS_API_KEY")),
        odds_fallback=bool(odds.get("fallback_enabled", True)),
        feature_flags=dict(feature_flags),
    )


def _apply_environment_overrides(
    config_data: dict[str, Any],
    environment: str,
) -> dict[str, Any]:
    """Merge environment-specific overrides into the base config dict.

    Looks for a top-level ``environments.<environment>`` key and deep-merges
    it over the base config.  Unknown environments are silently ignored so
    that the base config is always returned.
    """
    environments = config_data.get("environments", {})
    overrides = environments.get(environment, {})
    if not overrides:
        return config_data

    import copy

    merged = copy.deepcopy(config_data)
    _deep_merge(merged, overrides)
    return merged


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> None:
    """Recursively merge *overrides* into *base* in-place."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def load_config(
    config_path: Path | None = None,
    environment: str = "production",
) -> ModelConfig:
    """Load and validate configuration from a YAML or JSON file.

    Args:
        config_path: Path to the config file.  Defaults to
            ``data/config/model_config.yaml`` relative to the current
            working directory.
        environment: One of ``"development"`` or ``"production"``.
            Environment-specific overrides are merged from the
            ``environments.<environment>`` section of the config file.

    Returns:
        A validated :class:`ModelConfig` instance.

    Raises:
        ConfigValidationError: if the loaded configuration is invalid.
    """
    if config_path is None:
        config_path = Path("data/config/model_config.yaml")

    if not config_path.exists():
        logger.warning(
            "Config file not found at %s — using default configuration", config_path
        )
        return get_default_config()

    config_data = _parse_yaml_or_json(config_path)
    config_data = _apply_environment_overrides(config_data, environment)
    config = _build_config_from_dict(config_data)
    validate_config(config)

    logger.info("Loaded config from %s (environment=%s)", config_path, environment)
    return config


def get_default_config() -> ModelConfig:
    """Return a safe default configuration when no config file is available."""
    return ModelConfig(
        version="v2.1",
        feature_version="v2.1",
        enable_weather=False,
        enable_injuries=False,
        enable_travel=True,
        enable_origin_tracking=True,
        ensemble_sub_models=["elo", "features"],
        optimization_objective="brier",
        calibration_enabled=False,
        calibration_method="isotonic",
        uncertainty_enabled=False,
        bootstrap_samples=100,
        confidence_level=0.90,
        retraining_enabled=False,
        accuracy_threshold=0.55,
        window_size=4,
        min_games_before_check=16,
        weather_provider="openweathermap",
        weather_api_key_env="WEATHER_API_KEY",
        weather_cache_enabled=True,
        weather_fallback=True,
        odds_provider="the-odds-api",
        odds_api_key_env="ODDS_API_KEY",
        odds_fallback=True,
        feature_flags={
            "use_gradient_boosting": False,
            "use_neural_network": False,
            "use_ensemble_stacking": False,
            "enable_prediction_explanations": False,
            "enable_confidence_intervals": False,
            "enable_dashboard": False,
        },
    )
