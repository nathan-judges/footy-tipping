# Implementation Plan: Prediction Model Enhancements

## Overview

This implementation plan breaks down the prediction model enhancements into discrete, testable tasks organized by dependency order. Each task is designed to be completable in a focused 2-4 hour session and includes clear acceptance criteria, file paths, and testing requirements.

The implementation follows a phased approach: Foundation → Feature Engineering → Model Architecture → Evaluation & Monitoring → Continuous Learning → Documentation & Polish.

## Tasks

### Phase 1: Foundation - Data Models, Configuration, Basic Infrastructure

- [x] 1. Create core data models and type definitions
  - Create `scripts/lib/weather_api.py` with `WeatherData` dataclass
  - Create `scripts/lib/injury_tracker.py` with `PlayerImpact` and `InjuryStatus` dataclasses
  - Create `scripts/lib/feature_cache.py` with `CachedFeatures` dataclass
  - Create `scripts/lib/model_registry.py` with `ModelMetadata` dataclass
  - Add type hints and frozen dataclasses for immutability
  - _Requirements: 1.1, 2.1, 3.1, 12.1_

- [x] 2. Extend FeatureSet with new NRL-specific and contextual features
  - [x] 2.1 Add NRL-specific feature fields to `FeatureSet` in `scripts/lib/features.py`
    - Add travel_distance_km, short_turnaround flags, State of Origin fields
    - Add venue_win_rate fields, rivalry_game, finals_match flags
    - Update `feature_vector()` function to include new features
    - Update `FEATURE_NAMES` list with new feature names
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7_
  
  - [x] 2.2 Add weather feature fields to `FeatureSet`
    - Add temperature_c, precipitation_mm, wind_speed_kmh, wet_weather fields
    - Update `feature_vector()` to include weather features
    - Update `FEATURE_NAMES` list
    - _Requirements: 1.1, 2.3, 2.4_
  
  - [x] 2.3 Add injury feature fields to `FeatureSet`
    - Add injury_impact_home/away, key_player_out_home/away fields
    - Update `feature_vector()` to include injury features
    - Update `FEATURE_NAMES` list
    - _Requirements: 1.1, 3.2, 3.3_

- [x] 3. Create configuration management system
  - Create `scripts/lib/config.py` for model hyperparameters and feature flags
  - Define YAML/JSON schema for configuration files
  - Implement configuration validation on startup
  - Add environment-specific configs (development, production)
  - Create `data/config/model_config.yaml` with default hyperparameters
  - _Requirements: 18.1, 18.2, 18.3, 18.5_


- [x] 3.1 Write unit tests for configuration management
  - Test configuration loading and validation
  - Test schema validation with invalid configs
  - Test environment-specific config selection
  - _Requirements: 18.3_

- [~] 4. Checkpoint - Verify foundation components
  - Ensure all tests pass, ask the user if questions arise.

### Phase 2: Feature Engineering - Weather API, Injury Tracking, NRL-Specific Features

- [ ] 5. Implement weather data integration
  - [ ] 5.1 Create venue coordinate mapping in `scripts/lib/weather_api.py`
    - Define `VENUE_COORDINATES` dict with lat/lon for all 16 NRL venues
    - Implement `get_venue_coordinates()` function
    - _Requirements: 2.1_
  
  - [~] 5.2 Implement weather API client with caching
    - Implement `fetch_weather()` function with OpenWeatherMap/WeatherAPI support
    - Add exponential backoff retry logic for transient failures
    - Implement weather cache persistence to `data/weather_cache.json`
    - Add fallback to venue-season averages when API unavailable
    - _Requirements: 2.1, 2.2, 2.5, 2.6, 19.1, 19.4_
  
  - [~] 5.3 Implement venue-season average computation
    - Implement `compute_venue_season_averages()` function
    - Group historical weather by venue and month
    - Compute mean temperature, precipitation, wind speed per venue-month
    - _Requirements: 2.2_


- [~] 5.4 Write unit tests for weather API integration
  - Test venue coordinate lookup
  - Test weather fetch with mocked API responses
  - Test cache hit/miss scenarios
  - Test fallback to venue-season averages
  - Test API failure handling
  - _Requirements: 2.1, 2.2, 2.5, 17.1_

- [ ] 6. Implement injury and suspension tracking
  - [-] 6.1 Create injury data schema and loader in `scripts/lib/injury_tracker.py`
    - Implement `load_injury_data()` function
    - Create `data/injuries/current.json` schema
    - Add fallback to empty status when file unavailable
    - _Requirements: 3.1, 3.5_
  
  - [~] 6.2 Implement team strength adjustment calculation
    - Implement `compute_team_strength_adjustment()` function
    - Map impact scores to ELO-equivalent adjustments
    - Return negative values for missing players (e.g., -30 ELO for key player)
    - _Requirements: 3.3_
  
  - [~] 6.3 Implement injury snapshot persistence
    - Implement `persist_injury_snapshot()` function
    - Save timestamped snapshots to `data/injuries/snapshots/`
    - _Requirements: 3.4_

- [~] 6.4 Write unit tests for injury tracking
  - Test injury data loading with valid/invalid JSON
  - Test strength adjustment calculation
  - Test snapshot persistence
  - _Requirements: 3.1, 3.3, 3.4, 17.1_


- [ ] 7. Implement NRL-specific feature extraction functions
  - [-] 7.1 Implement travel distance calculation in `scripts/lib/features.py`
    - Define team home venue mapping
    - Implement `compute_travel_distance()` using Haversine formula
    - Return great-circle distance in kilometers
    - _Requirements: 1.2_
  
  - [-] 7.2 Implement State of Origin detection
    - Implement `identify_state_of_origin_rounds()` function
    - Return set of affected round numbers per season
    - Handle year-to-year variation (typically rounds 13, 15, 17)
    - _Requirements: 1.3_
  
  - [-] 7.3 Implement venue-specific win rate calculation
    - Implement `compute_venue_specific_win_rate()` function
    - Filter history to team's games at specific venue
    - Require minimum 5 games for statistical validity
    - Return 0.5 (neutral) if insufficient data
    - _Requirements: 1.5_
  
  - [ ] 7.4 Implement rivalry game detection
    - Define `RIVALRY_PAIRS` set with traditional matchups
    - Implement `is_rivalry_game()` function
    - Use symmetric frozenset for bidirectional matching
    - _Requirements: 1.6_

- [~] 7.5 Write unit tests for NRL-specific features
  - Test travel distance calculation with known venue pairs
  - Test State of Origin round identification
  - Test venue win rate with various history sizes
  - Test rivalry detection for known pairs
  - _Requirements: 1.2, 1.3, 1.5, 1.6, 17.1, 17.5_


- [ ] 8. Integrate new features into main extraction pipeline
  - [~] 8.1 Update `extract_features()` in `scripts/lib/features.py`
    - Add weather_data and injury_data parameters
    - Call weather API for each fixture
    - Call injury tracker for team status
    - Compute all NRL-specific features
    - Populate all new FeatureSet fields
    - _Requirements: 1.1, 1.8, 2.1, 3.1_
  
  - [~] 8.2 Implement feature validation
    - Add validation checks for completeness
    - Flag missing weather data
    - Flag missing injury data
    - Log warnings for incomplete features
    - _Requirements: 1.8_

- [~] 8.3 Write integration tests for feature extraction
  - Test end-to-end feature extraction with mocked data
  - Test feature validation logic
  - Test handling of missing external data
  - _Requirements: 1.8, 17.2_

- [ ] 9. Implement feature caching system
  - [~] 9.1 Create feature cache persistence in `scripts/lib/feature_cache.py`
    - Implement `save_features()` function
    - Implement `load_features()` function
    - Add feature version validation
    - Create `data/features/` directory structure
    - _Requirements: 1.9, 16.1_
  
  - [~] 9.2 Implement cache-aware feature extraction
    - Implement `extract_features_with_cache()` function
    - Check cache before computing features
    - Save computed features to cache
    - _Requirements: 1.9, 16.1_


- [~] 9.3 Write unit tests for feature caching
  - Test cache save and load
  - Test feature version mismatch handling
  - Test cache-aware extraction (hit and miss)
  - _Requirements: 1.9, 17.4_

- [~] 10. Checkpoint - Verify feature engineering pipeline
  - Ensure all tests pass, ask the user if questions arise.

### Phase 3: Model Architecture - Gradient Boosting, Neural Networks, Ensemble Optimization

- [ ] 11. Implement gradient boosting models
  - [~] 11.1 Create XGBoost wrapper in `scripts/lib/models/gradient_boosting.py`
    - Implement `GradientBoostingPredictor` class
    - Add XGBoost initialization with hyperparameters
    - Implement `train()` method with early stopping
    - Implement `predict_proba()` method
    - Implement `get_feature_importance()` method
    - _Requirements: 4.1, 13.1_
  
  - [~] 11.2 Add LightGBM support to gradient boosting wrapper
    - Add LightGBM initialization option
    - Ensure consistent interface with XGBoost
    - _Requirements: 4.1_

- [~] 11.3 Write unit tests for gradient boosting models
  - Test model initialization
  - Test training with synthetic data
  - Test prediction output format
  - Test feature importance extraction
  - _Requirements: 4.1, 17.1_


- [ ] 12. Implement neural network model
  - [~] 12.1 Create PyTorch network architecture in `scripts/lib/models/neural_network.py`
    - Implement `NRLPredictionNet` class (feed-forward with dropout)
    - Define configurable hidden layer dimensions
    - Add ReLU activations and dropout layers
    - Add sigmoid output layer for binary classification
    - _Requirements: 4.2_
  
  - [~] 12.2 Create neural network training wrapper
    - Implement `NeuralNetworkPredictor` class
    - Implement `train()` method with early stopping
    - Implement `predict_proba()` method
    - Add batch training with DataLoader
    - _Requirements: 4.2_

- [~] 12.3 Write unit tests for neural network
  - Test network initialization
  - Test forward pass with synthetic data
  - Test training convergence
  - Test prediction output format
  - _Requirements: 4.2, 17.1_

- [ ] 13. Implement model registry
  - [~] 13.1 Create model persistence system in `scripts/lib/model_registry.py`
    - Implement `ModelRegistry` class
    - Implement `save_model()` method for all model types
    - Implement `load_model()` method for all model types
    - Create `data/models/` directory structure
    - _Requirements: 4.5, 4.6_
  
  - [~] 13.2 Implement production model management
    - Implement `get_production_model()` method
    - Implement `set_production_model()` method
    - Implement `list_models()` method
    - Use file-based pointer for production model
    - _Requirements: 4.5_


- [~] 13.3 Write unit tests for model registry
  - Test model save and load for each model type
  - Test production model pointer management
  - Test model listing and sorting
  - _Requirements: 4.5, 17.4_

- [ ] 14. Implement ensemble weight optimization
  - [~] 14.1 Create ensemble optimizer in `scripts/lib/models/ensemble.py`
    - Implement `EnsembleOptimizer` class
    - Implement `optimize_weights()` using scipy.optimize
    - Add constrained optimization (weights sum to 1, non-negative)
    - Support Brier score, log loss, and accuracy objectives
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [~] 14.2 Implement ensemble prediction with weight redistribution
    - Implement `predict()` method
    - Handle missing sub-models (e.g., market odds unavailable)
    - Redistribute weights proportionally when models missing
    - _Requirements: 5.4_

- [~] 14.3 Write unit tests for ensemble optimization
  - Test weight optimization with synthetic predictions
  - Test constraint satisfaction (sum to 1, non-negative)
  - Test weight redistribution with missing models
  - _Requirements: 5.1, 5.2, 5.4, 17.1_

- [~] 15. Checkpoint - Verify model architecture components
  - Ensure all tests pass, ask the user if questions arise.


### Phase 4: Evaluation & Monitoring - Enhanced Backtesting, Calibration, Dashboard

- [ ] 16. Enhance backtesting system
  - [~] 16.1 Extend backtester with comprehensive metrics in `scripts/lib/backtester.py`
    - Add log loss calculation to `summarize_backtest()`
    - Add per-season accuracy breakdown
    - Add per-team accuracy breakdown
    - Add regular season vs finals breakdown
    - Add rivalry game vs standard fixture breakdown
    - _Requirements: 8.2, 8.3, 8.6, 8.7_
  
  - [~] 16.2 Implement systematic bias detection
    - Add home win over-prediction detection
    - Add upset under-prediction detection
    - Add confidence calibration by probability bucket
    - _Requirements: 8.4_
  
  - [~] 16.3 Implement ROI simulation against market odds
    - Add betting simulation with market odds
    - Calculate ROI for various betting strategies
    - _Requirements: 8.3_

- [~] 16.4 Write unit tests for enhanced backtesting
  - Test metric calculations with known outcomes
  - Test bias detection logic
  - Test ROI simulation
  - _Requirements: 8.2, 8.3, 8.4, 17.3_


- [ ] 17. Implement calibration system
  - [~] 17.1 Create calibration module in `scripts/lib/calibration.py`
    - Implement calibration curve computation (10 probability buckets)
    - Implement expected calibration error (ECE) calculation
    - Implement Platt scaling calibration
    - Implement isotonic regression calibration
    - _Requirements: 7.1, 7.2, 7.4_
  
  - [~] 17.2 Integrate calibration into prediction pipeline
    - Add calibration layer after ensemble prediction
    - Load calibration parameters from model registry
    - Apply calibration to raw probabilities
    - _Requirements: 7.4_

- [~] 17.3 Write unit tests for calibration
  - Test calibration curve computation
  - Test ECE calculation
  - Test Platt scaling with synthetic data
  - Test isotonic regression with synthetic data
  - _Requirements: 7.1, 7.2, 7.4, 17.1_

- [ ] 18. Implement uncertainty quantification
  - [~] 18.1 Create confidence interval module in `scripts/lib/uncertainty.py`
    - Implement bootstrap resampling for confidence intervals
    - Implement 90% confidence interval computation
    - Add low-confidence prediction flagging (width > 0.3)
    - _Requirements: 6.1, 6.2, 6.4_
  
  - [~] 18.2 Integrate confidence intervals into predictions
    - Add confidence interval fields to TipResult diagnostics
    - Compute intervals during prediction generation
    - _Requirements: 6.1, 6.3_


- [~] 18.3 Write unit tests for uncertainty quantification
  - Test bootstrap resampling
  - Test confidence interval computation
  - Test interval calibration validation
  - _Requirements: 6.1, 6.5, 17.1_

- [ ] 19. Implement model monitoring dashboard
  - [~] 19.1 Create dashboard generator in `scripts/lib/dashboard.py`
    - Implement HTML template for monitoring dashboard
    - Add season-to-date accuracy, Brier score, log loss display
    - Add rolling 4-round accuracy with trend indicators
    - Add per-team accuracy table sorted by performance
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [~] 19.2 Add feature importance visualization
    - Add top 10 features by importance with bar chart
    - Add feature importance trend over time
    - _Requirements: 10.4, 13.2_
  
  - [~] 19.3 Add calibration and confidence visualizations
    - Add calibration curve plot
    - Add prediction confidence distribution histogram
    - _Requirements: 10.5, 10.6_
  
  - [~] 19.4 Integrate dashboard generation into pipeline
    - Generate dashboard after each round completion
    - Save to `data/dashboard.html`
    - Commit dashboard with data updates
    - _Requirements: 10.7_

- [~] 19.5 Write unit tests for dashboard generation
  - Test HTML generation with sample metrics
  - Test chart rendering with synthetic data
  - _Requirements: 10.1, 10.2, 10.3, 17.1_

- [~] 20. Checkpoint - Verify evaluation and monitoring components
  - Ensure all tests pass, ask the user if questions arise.


### Phase 5: Continuous Learning - Retraining Triggers, Model Registry, Deployment

- [ ] 21. Implement model training pipeline
  - [~] 21.1 Create model trainer in `scripts/lib/model_trainer.py`
    - Implement walk-forward validation data splitting
    - Implement training loop for all model types
    - Compute performance metrics for each model variant
    - Save trained models to registry with metadata
    - _Requirements: 4.3, 4.4, 4.7_
  
  - [~] 21.2 Implement model selection logic
    - Compare models across multiple seasons (minimum 2)
    - Select best model based on Brier score
    - Promote selected model to production
    - _Requirements: 4.7_
  
  - [~] 21.3 Implement ensemble weight optimization in training
    - Extract validation predictions from all sub-models
    - Optimize ensemble weights using validation data
    - Persist optimized weights to configuration
    - _Requirements: 5.1, 5.5, 5.6_

- [~] 21.4 Write integration tests for model training
  - Test end-to-end training with synthetic historical data
  - Test model selection logic
  - Test ensemble weight optimization
  - _Requirements: 4.3, 4.7, 5.1, 17.2_


- [ ] 22. Implement drift detection and retraining triggers
  - [~] 22.1 Create drift detector in `scripts/lib/drift_detector.py`
    - Implement rolling accuracy calculation (last 4 rounds)
    - Implement performance degradation detection (threshold: 55%)
    - Implement retraining trigger logic
    - Persist retraining events to `data/performance_log.json`
    - _Requirements: 9.1, 9.2, 9.7_
  
  - [~] 22.2 Implement automated retraining workflow
    - Trigger model retraining when drift detected
    - Rebuild ELO ratings from all historical data
    - Re-optimize ensemble weights using recent 2 seasons
    - Validate retrained model on holdout set
    - _Requirements: 9.3, 9.4, 9.5_
  
  - [~] 22.3 Implement model promotion safeguards
    - Compare retrained model to current production model
    - Only promote if retrained model performs better
    - Log alert if retrained model performs worse
    - _Requirements: 9.6_

- [~] 22.4 Write unit tests for drift detection
  - Test rolling accuracy calculation
  - Test retraining trigger conditions
  - Test model promotion logic
  - _Requirements: 9.1, 9.2, 9.6, 17.1_


- [ ] 23. Implement feature importance tracking
  - [~] 23.1 Create feature importance tracker in `scripts/lib/feature_importance.py`
    - Compute feature importance after each training cycle
    - Persist importance scores to JSON format
    - Track importance trends over time
    - _Requirements: 13.1, 13.2_
  
  - [~] 23.2 Implement feature ablation testing
    - Train models with specific features removed
    - Measure performance impact of feature removal
    - Identify low-value features for potential removal
    - _Requirements: 13.5_
  
  - [~] 23.3 Implement automatic feature flagging
    - Flag features in bottom 20% for 3 consecutive cycles
    - Log recommendations for feature removal
    - _Requirements: 13.4_

- [~] 23.4 Write unit tests for feature importance tracking
  - Test importance score computation
  - Test ablation testing logic
  - Test feature flagging conditions
  - _Requirements: 13.1, 13.4, 13.5, 17.1_

- [ ] 24. Implement prediction explainability
  - [~] 24.1 Create explainability module in `scripts/lib/explainability.py`
    - Compute per-feature contributions to predictions
    - Identify top 5 positive and negative contributors
    - Generate human-readable explanations
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [~] 24.2 Add sub-model agreement indicators
    - Compare predictions across sub-models
    - Flag disagreements between models
    - Add agreement indicators to diagnostics
    - _Requirements: 14.4_


- [~] 24.3 Write unit tests for explainability
  - Test feature contribution calculation
  - Test explanation text generation
  - Test sub-model agreement detection
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 17.1_

- [ ] 25. Implement manual override system
  - [~] 25.1 Create override manager in `scripts/lib/manual_overrides.py`
    - Load overrides from `data/config/manual_overrides.json`
    - Apply overrides to predictions before finalization
    - Preserve original model predictions in diagnostics
    - Log all applied overrides with justification
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  
  - [~] 25.2 Implement override tracking and expiration
    - Track override accuracy separately from model accuracy
    - Expire overrides after fixture kickoff time
    - _Requirements: 11.5, 11.6_

- [~] 25.3 Write unit tests for manual overrides
  - Test override loading and application
  - Test override expiration logic
  - Test override accuracy tracking
  - _Requirements: 11.1, 11.5, 11.6, 17.1_

- [~] 26. Checkpoint - Verify continuous learning components
  - Ensure all tests pass, ask the user if questions arise.


### Phase 6: Documentation & Polish - Runbooks, Inline Docs, Final Testing

- [ ] 27. Implement backward compatibility and error handling
  - [~] 27.1 Extend TipResult schema with new diagnostics fields
    - Add confidence_interval field to ModelDiagnostics
    - Add feature_contributions field to ModelDiagnostics
    - Add sub_model_agreement field to ModelDiagnostics
    - Ensure backward compatibility with existing consumers
    - _Requirements: 15.1, 15.2_
  
  - [~] 27.2 Implement graceful fallback mechanisms
    - Add feature flag system for new components
    - Fallback to baseline features when external APIs fail
    - Continue with default values when features unavailable
    - _Requirements: 15.3, 15.4, 19.1, 19.2_
  
  - [~] 27.3 Implement comprehensive error handling
    - Add exponential backoff for API retries
    - Log errors without blocking pipeline
    - Validate input data with descriptive error messages
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_

- [~] 27.4 Write integration tests for error handling
  - Test API failure scenarios
  - Test feature extraction with missing data
  - Test model training failure recovery
  - _Requirements: 19.1, 19.2, 19.3, 17.2_


- [ ] 28. Implement performance optimization
  - [~] 28.1 Add feature computation caching
    - Cache computed features to avoid redundant calculations
    - Parallelize feature extraction across fixtures
    - Load historical data once per pipeline run
    - _Requirements: 16.1, 16.2, 16.3_
  
  - [~] 28.2 Add model training optimizations
    - Implement early stopping for all model types
    - Add execution time logging for each pipeline stage
    - Identify and optimize bottlenecks
    - _Requirements: 16.4, 16.5_

- [~] 28.3 Write performance tests
  - Test pipeline completion within 5 minute target
  - Test cache hit rates
  - Test parallel feature extraction
  - _Requirements: 16.1, 16.2, 16.3, 16.4_

- [ ] 29. Implement historical data validation
  - [~] 29.1 Create data validation module in `scripts/lib/data_validation.py`
    - Validate minimum 2 complete seasons exist
    - Report data completeness metrics
    - Identify gaps in historical data
    - Validate team name normalization consistency
    - _Requirements: 12.1, 12.2, 12.3, 12.5_
  
  - [~] 29.2 Add data backfill recommendations
    - Identify missing weather data
    - Identify missing injury snapshots
    - Recommend backfill priorities
    - _Requirements: 12.4_


- [~] 29.3 Write unit tests for data validation
  - Test completeness metric calculation
  - Test gap identification
  - Test team name normalization validation
  - _Requirements: 12.1, 12.3, 12.5, 17.1_

- [ ] 30. Create comprehensive documentation
  - [~] 30.1 Write model architecture document
    - Document all components and data flows
    - Include architecture diagrams
    - Explain design decisions and tradeoffs
    - Save to `docs/model-architecture.md`
    - _Requirements: 20.1_
  
  - [~] 30.2 Write feature engineering guide
    - Document each feature's definition and rationale
    - Include feature importance insights
    - Explain NRL-specific contextual factors
    - Save to `docs/feature-engineering.md`
    - _Requirements: 20.2_
  
  - [~] 30.3 Write operational runbook
    - Document retraining procedures
    - Document manual override workflows
    - Document debugging poor predictions
    - Document common operational tasks
    - Save to `docs/model-operations-runbook.md`
    - _Requirements: 20.3_
  
  - [~] 30.4 Add inline code documentation
    - Add docstrings to all non-trivial functions
    - Follow PEP 257 docstring conventions
    - Include parameter types and return values
    - _Requirements: 20.4_
  
  - [~] 30.5 Create model changelog
    - Document model version history
    - Track performance changes over time
    - Record major feature additions
    - Save to `docs/model-changelog.md`
    - _Requirements: 20.5_


- [ ] 31. Integrate enhancements into main prediction pipeline
  - [~] 31.1 Update `scripts/lib/model.py` to use new features
    - Integrate weather API calls
    - Integrate injury tracker
    - Use cache-aware feature extraction
    - Load production model from registry
    - Apply calibration layer
    - Compute confidence intervals
    - _Requirements: 15.1, 15.2, 15.5_
  
  - [~] 31.2 Update `scripts/update_tips.py` to support new workflows
    - Add training mode flag for model retraining
    - Add evaluation mode for drift detection
    - Integrate dashboard generation
    - Maintain existing prediction workflow
    - _Requirements: 15.5, 15.6_

- [~] 31.3 Write end-to-end integration tests
  - Test complete prediction pipeline with new features
  - Test training workflow
  - Test evaluation and drift detection workflow
  - Test backward compatibility with existing data
  - _Requirements: 15.1, 15.5, 15.6, 17.2, 17.6_

- [x] 32. Update Python dependencies
  - Add xgboost, lightgbm, torch, scipy to `requirements.txt`
  - Pin versions for reproducibility
  - Test installation in clean environment
  - Update GitHub Actions workflow if needed
  - _Requirements: 4.1, 4.2, 5.1_

- [~] 33. Final checkpoint - End-to-end validation
  - Run complete test suite (`npm run check:all`)
  - Run backtesting on historical data
  - Generate predictions for current round
  - Verify dashboard generation
  - Ensure all tests pass, ask the user if questions arise.


## Notes

- **Optional Tasks**: Tasks marked with `*` are optional test-related sub-tasks that can be skipped for faster MVP delivery. However, they are strongly recommended for production quality.

- **Testing Strategy**: Each phase includes unit tests for individual components and integration tests for end-to-end workflows. Property-based tests are not included as the design focuses on data-driven model improvements rather than algorithmic correctness properties.

- **Incremental Validation**: Checkpoint tasks ensure that each phase is validated before moving to the next, catching errors early and maintaining system stability.

- **Backward Compatibility**: All enhancements extend existing infrastructure without breaking changes. The existing ELO ratings, feature extraction, and prediction pipeline remain functional throughout implementation.

- **Performance Constraints**: All tasks are designed to complete within GitHub Actions time limits (~5 minutes). Feature caching and parallel processing ensure efficient execution.

- **Requirements Traceability**: Each task explicitly references the requirements it satisfies, ensuring complete coverage of all 20 requirements.

- **Dependency Management**: Tasks are ordered by dependency - foundation components must be completed before feature engineering, which must be completed before model architecture, etc.

- **Error Handling**: All external API integrations include graceful fallback mechanisms to ensure the pipeline never blocks on transient failures.

- **Documentation**: Comprehensive documentation is created in Phase 6 to ensure maintainability and knowledge transfer.


## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1", "3", "32"]
    },
    {
      "id": 1,
      "tasks": ["2.1", "2.2", "2.3", "3.1"]
    },
    {
      "id": 2,
      "tasks": ["5.1", "6.1", "7.1", "7.2", "7.3", "7.4"]
    },
    {
      "id": 3,
      "tasks": ["5.2", "5.3", "5.4", "6.2", "6.3", "6.4", "7.5"]
    },
    {
      "id": 4,
      "tasks": ["8.1", "8.2"]
    },
    {
      "id": 5,
      "tasks": ["8.3", "9.1"]
    },
    {
      "id": 6,
      "tasks": ["9.2", "9.3"]
    },
    {
      "id": 7,
      "tasks": ["11.1", "11.2", "12.1"]
    },
    {
      "id": 8,
      "tasks": ["11.3", "12.2", "12.3", "13.1"]
    },
    {
      "id": 9,
      "tasks": ["13.2", "13.3", "14.1"]
    },
    {
      "id": 10,
      "tasks": ["14.2", "14.3"]
    },
    {
      "id": 11,
      "tasks": ["16.1", "16.2", "16.3", "17.1"]
    },
    {
      "id": 12,
      "tasks": ["16.4", "17.2", "17.3", "18.1"]
    },
    {
      "id": 13,
      "tasks": ["18.2", "18.3", "19.1"]
    },
    {
      "id": 14,
      "tasks": ["19.2", "19.3"]
    },
    {
      "id": 15,
      "tasks": ["19.4", "19.5"]
    },
    {
      "id": 16,
      "tasks": ["21.1"]
    },
    {
      "id": 17,
      "tasks": ["21.2", "21.3", "21.4"]
    },
    {
      "id": 18,
      "tasks": ["22.1", "23.1", "24.1", "25.1"]
    },
    {
      "id": 19,
      "tasks": ["22.2", "22.3", "22.4", "23.2", "23.3", "23.4", "24.2", "24.3", "25.2", "25.3"]
    },
    {
      "id": 20,
      "tasks": ["27.1", "27.2", "28.1", "29.1"]
    },
    {
      "id": 21,
      "tasks": ["27.3", "27.4", "28.2", "28.3", "29.2", "29.3"]
    },
    {
      "id": 22,
      "tasks": ["30.1", "30.2", "30.3", "30.4", "30.5"]
    },
    {
      "id": 23,
      "tasks": ["31.1"]
    },
    {
      "id": 24,
      "tasks": ["31.2", "31.3"]
    }
  ]
}
```
