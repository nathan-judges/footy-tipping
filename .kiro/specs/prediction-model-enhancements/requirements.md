# Requirements Document

## Introduction

This document specifies requirements for enhancing the NRL prediction model to improve accuracy and add meaningful contextual signals. The existing ensemble model (ELO + logistic regression + market odds) is a solid base. These enhancements add NRL-specific features, a gradient boosting model, and better backtesting — without introducing infrastructure complexity that doesn't serve a personal project.

## Glossary

- **Prediction_System**: The Python pipeline that generates NRL match predictions
- **Ensemble_Model**: The weighted combination of ELO, feature-based model, and market odds
- **Feature_Extractor**: Component that computes predictive features from historical data and contextual factors
- **ELO_Engine**: Rating system that updates team strengths based on match results
- **Backtester**: Walk-forward validation engine that measures model performance on historical data
- **Brier_Score**: Mean squared error of probability forecasts (lower is better, 0.25 is random)
- **State_of_Origin**: Annual representative series that removes key players from NRL clubs for ~3 rounds
- **Short_Turnaround**: Match played with less than 6 days rest since previous game
- **Feature_Cache**: JSON files storing computed features to avoid redundant recalculation

## Requirements

### Requirement 1: NRL-Specific Feature Engineering

**User Story:** As a prediction system, I want NRL-specific contextual features, so that the model can learn from factors that genuinely affect match outcomes.

#### Acceptance Criteria

1. WHEN a fixture is analyzed, THE Feature_Extractor SHALL compute travel distance (km) for the away team from their home venue to the match venue using the Haversine formula
2. WHEN computing rest days, THE Feature_Extractor SHALL flag short turnarounds (less than 6 days) as a binary feature for both home and away teams
3. WHEN a fixture occurs during a State of Origin round, THE Feature_Extractor SHALL set a boolean flag on the feature set
4. WHEN analyzing team performance, THE Feature_Extractor SHALL compute venue-specific win rates for each team at each stadium, returning 0.5 (neutral) when fewer than 5 historical games exist at that venue
5. WHEN a fixture is in the finals series, THE Feature_Extractor SHALL set a finals indicator flag
6. THE Feature_Extractor SHALL add all new features to the existing `FeatureSet` dataclass and `feature_vector()` function without removing existing features

### Requirement 2: Weather Data Integration

**User Story:** As a prediction system, I want weather conditions for match venues, so that I can account for conditions that affect scoring patterns.

#### Acceptance Criteria

1. WHEN a match fixture is loaded, THE Prediction_System SHALL fetch weather data for the venue location and kickoff time using the Open-Meteo Archive API (free, no authentication required)
2. WHEN weather data is unavailable or the API fails, THE Prediction_System SHALL use venue-month averages as fallback values and continue without blocking the pipeline
3. THE Prediction_System SHALL extract precipitation (mm), temperature (°C), and wind speed (km/h) as numeric features, plus a `wet_weather` boolean flag when precipitation exceeds 5mm
4. THE Prediction_System SHALL cache fetched weather data to `data/weather_cache.json` to avoid redundant API calls on subsequent runs

### Requirement 3: Injury Tracking

**User Story:** As a prediction system, I want to account for key player absences, so that predictions reflect team strength at the time of the match.

#### Acceptance Criteria

1. WHEN generating predictions, THE Prediction_System SHALL load injury and suspension data from `data/injuries/current.json` (manually maintained)
2. WHEN a player is listed as unavailable, THE Feature_Extractor SHALL compute a `injury_impact` score for each team based on manually configured player impact weights
3. WHEN injury data is missing or the file does not exist, THE Prediction_System SHALL proceed with zero adjustment and log a warning

### Requirement 4: Gradient Boosting Model

**User Story:** As a model developer, I want a gradient boosting model trained on the extended feature set, so that the ensemble benefits from a non-linear learner.

#### Acceptance Criteria

1. THE Prediction_System SHALL train an XGBoost classifier on historical match features and outcomes
2. WHEN training, THE Prediction_System SHALL use walk-forward validation (train on seasons N-2 and N-1, validate on season N) to prevent data leakage
3. THE trained model SHALL be persisted to `data/models/xgboost_model.json` for use in the prediction pipeline
4. THE Prediction_System SHALL include XGBoost predictions as a weighted component in the existing ensemble alongside ELO and market odds
5. WHEN XGBoost predictions are unavailable (e.g., model file missing), THE Prediction_System SHALL fall back to the existing ensemble without XGBoost

### Requirement 5: Ensemble Weight Optimization

**User Story:** As a model developer, I want ensemble weights determined by validation performance, so that the combination is data-driven rather than hand-tuned.

#### Acceptance Criteria

1. WHEN training the ensemble, THE Prediction_System SHALL optimize sub-model weights using scipy constrained optimization against historical validation data
2. THE optimization SHALL minimize Brier score with weights constrained to sum to 1.0 and be non-negative
3. THE optimized weights SHALL be persisted to `data/config/model_config.yaml` for use in the prediction pipeline
4. WHEN a sub-model is unavailable (e.g., market odds missing), THE Prediction_System SHALL redistribute weights proportionally to available models

### Requirement 6: Enhanced Backtesting

**User Story:** As a model developer, I want backtesting results broken down by season and team, so that I can identify where the model performs well and where it struggles.

#### Acceptance Criteria

1. WHEN backtesting completes, THE Backtester SHALL report overall accuracy, Brier score, and log loss
2. THE Backtester SHALL report per-season accuracy breakdown
3. THE Backtester SHALL report per-team accuracy breakdown sorted by performance
4. THE Backtester SHALL report accuracy separately for regular season vs finals matches
5. THE Backtester SHALL output results to the console and optionally to `data/backtest_results.json`

### Requirement 7: Backward Compatibility and Resilience

**User Story:** As a system maintainer, I want enhancements to extend the existing pipeline without breaking it, so that the weekly GitHub Actions run remains stable.

#### Acceptance Criteria

1. THE Prediction_System SHALL continue to output predictions in the existing `TipResult` JSON schema
2. WHEN any new feature source fails (weather API, injury file), THE Prediction_System SHALL log the error and continue with default/fallback values
3. THE Prediction_System SHALL maintain the existing ELO ratings file format
4. THE Prediction_System SHALL complete the full prediction pipeline within the existing GitHub Actions time budget (~5 minutes)
