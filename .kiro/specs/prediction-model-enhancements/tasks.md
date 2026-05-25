# Implementation Plan: Prediction Model Enhancements

## Overview

Seven focused tasks that deliver meaningful model improvements without over-engineering. Tasks are ordered by dependency — each builds on the previous. Estimated total effort: 2-3 days.

## Tasks

### Phase 1: Feature Engineering

- [x] 1. Add NRL-specific features to FeatureSet
  - Add fields to `FeatureSet` dataclass in `scripts/lib/features.py`: `travel_distance_km`, `short_turnaround_home`, `short_turnaround_away`, `state_of_origin_round`, `venue_win_rate_home`, `venue_win_rate_away`, `finals_match`
  - Implement `compute_travel_distance(away_team, venue)` using Haversine formula with `TEAM_HOME_VENUES` mapping
  - Implement `identify_state_of_origin_rounds(season)` returning a hardcoded set of round numbers per season
  - Implement `compute_venue_win_rate(team, venue, history)` returning 0.5 when fewer than 5 games exist
  - Update `feature_vector()` and `FEATURE_NAMES` to include all new fields
  - Write pytest tests: travel distance for known venue pairs, SOO round detection, venue win rate edge cases (< 5 games, exactly 5 games)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2. Implement weather data integration
  - Create `scripts/lib/weather_api.py` with `WeatherData` dataclass and `VENUE_COORDINATES` dict for all NRL venues
  - Implement `fetch_weather(venue, kickoff_at)` calling Open-Meteo Archive API (`https://archive-api.open-meteo.com/v1/archive`)
  - Implement cache read/write to `data/weather_cache.json` (keyed by `"{venue}|{date}"`)
  - Implement `get_venue_season_average(venue, month)` as fallback when API fails
  - Add weather fields to `FeatureSet`: `temperature_c`, `precipitation_mm`, `wind_speed_kmh`, `wet_weather`
  - Update `extract_features()` to accept optional `weather_data` parameter; populate weather fields when provided
  - Write pytest tests: cache hit/miss, fallback on API failure, `wet_weather` flag at 5mm threshold
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Implement injury tracking
  - Create `scripts/lib/injury_tracker.py` with `load_injury_data(path)` that reads `data/injuries/current.json`
  - Return empty dict (zero impact) when file is missing; log a warning
  - Add injury fields to `FeatureSet`: `injury_impact_home`, `injury_impact_away`
  - Update `extract_features()` to accept optional `injury_data` parameter; populate injury fields when provided
  - Write pytest tests: loading valid JSON, missing file fallback, impact score computation
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 4. Implement feature caching
  - Create `scripts/lib/feature_cache.py` with `save_features(game_id, features)` and `load_features(game_id)`
  - Store to `data/features/{game_id}.json` with a `feature_version` field (invalidate cache on version bump)
  - Write pytest tests: save/load round-trip, version mismatch returns None
  - _Requirements: 7.4 (pipeline performance)_

### Phase 2: Model & Ensemble

- [x] 5. Implement XGBoost model
  - Create `scripts/lib/models/gradient_boosting.py` with `XGBoostPredictor` class
  - Implement `train(X, y)`, `predict_proba(X)`, `save(path)`, `load(path)`, `feature_importance()`
  - Load hyperparameters from `data/config/model_config.yaml` (n_estimators, max_depth, learning_rate)
  - Write pytest tests: train on synthetic data, predict returns values in [0, 1], save/load round-trip
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6. Implement ensemble weight optimization and training pipeline
  - Add `optimize_weights(predictions, actuals)` to `scripts/lib/ensemble.py` using `scipy.optimize.minimize` (SLSQP, Brier score objective, weights sum to 1)
  - Add `--train` flag to `scripts/update_tips.py` that: loads historical archive data, extracts features (with cache), runs walk-forward training (seasons N-2/N-1 → validate N), saves XGBoost model, optimizes and saves ensemble weights
  - Update the prediction path in `update_tips.py` to load and use the XGBoost model as an ensemble component alongside ELO and market odds
  - Fall back gracefully when `data/models/xgboost_model.json` is missing (use existing ensemble without XGBoost)
  - Write pytest tests: weight optimization constraints (sum to 1, non-negative), missing model fallback
  - _Requirements: 4.4, 5.1, 5.2, 5.3, 5.4, 7.1, 7.2_

### Phase 3: Evaluation

- [x] 7. Enhance backtesting with detailed breakdowns
  - Extend `summarize_backtest()` in `scripts/lib/backtester.py` to return a `BacktestSummary` dataclass with: `overall_accuracy`, `brier_score`, `log_loss`, `per_season` dict, `per_team` dict, `regular_season_accuracy`, `finals_accuracy`
  - Print a formatted summary table to console; optionally write to `data/backtest_results.json`
  - Write pytest tests: metric calculations with known outcomes, per-team breakdown, finals vs regular season split
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

## Notes

- Tasks 1–4 can be worked on independently before integrating in task 6
- The `--train` flag in task 6 is the only new entry point; the existing weekly pipeline is extended, not replaced
- No model registry, no drift detection, no monitoring dashboard — if the model needs retraining, run `python scripts/update_tips.py --train` manually
- XGBoost adds ~15MB to the dependency footprint; PyTorch and LightGBM are explicitly excluded
- All new modules follow existing PEP 8 and docstring conventions in `scripts/lib/`

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": ["1", "2", "3", "4", "5"],
      "description": "NRL features, weather, injuries, feature cache, and XGBoost model — all independent, can be worked in any order"
    },
    {
      "wave": 2,
      "tasks": ["6"],
      "description": "Ensemble weight optimization and training pipeline — depends on tasks 1–5"
    },
    {
      "wave": 3,
      "tasks": ["7"],
      "description": "Enhanced backtesting — depends on task 6"
    }
  ]
}
```
