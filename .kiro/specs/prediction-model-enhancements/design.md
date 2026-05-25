# Design Document: Prediction Model Enhancements

## Overview

This design extends the existing NRL prediction pipeline with NRL-specific features, weather data, injury tracking, an XGBoost model, and data-driven ensemble weight optimization. All changes extend existing modules — no new infrastructure, no new services, no new databases.

### Design Goals

1. **Better signals**: Add contextual features that genuinely affect NRL outcomes
2. **Better model**: Replace hand-tuned logistic regression weights with XGBoost + optimized ensemble
3. **Better evaluation**: Richer backtesting breakdowns to understand model strengths and weaknesses
4. **Stay simple**: No model registry, no drift detection, no dashboards — just a better pipeline

### Constraints

- All processing runs in GitHub Actions (~5 minute budget)
- No database — baked JSON files only
- Python 3.13, existing dependencies plus `xgboost` and `scipy`
- Existing `TipResult` schema must not break

## Data Models

### Extended FeatureSet

Extends the existing `FeatureSet` dataclass in `scripts/lib/features.py`:

```python
@dataclass
class FeatureSet:
    # --- Existing fields (unchanged) ---
    elo_diff: float = 0.0
    elo_home: float = 1500.0
    elo_away: float = 1500.0
    home_advantage: float = 1.0
    form_home_5: float = 0.5
    form_away_5: float = 0.5
    pd_per_game_home: float = 0.0
    pd_per_game_away: float = 0.0
    ladder_pos_diff: int = 0
    rest_days_home: int = 7
    rest_days_away: int = 7
    h2h_home_wins_recent: int = 0
    scoring_trend_home: float = 20.0
    scoring_trend_away: float = 20.0
    defensive_trend_home: float = 20.0
    defensive_trend_away: float = 20.0

    # --- New NRL-specific features ---
    travel_distance_km: float = 0.0
    short_turnaround_home: bool = False
    short_turnaround_away: bool = False
    state_of_origin_round: bool = False
    venue_win_rate_home: float = 0.5
    venue_win_rate_away: float = 0.5
    finals_match: bool = False

    # --- New weather features ---
    temperature_c: float = 20.0
    precipitation_mm: float = 0.0
    wind_speed_kmh: float = 10.0
    wet_weather: bool = False

    # --- New injury features ---
    injury_impact_home: float = 0.0
    injury_impact_away: float = 0.0
```

### WeatherData

New dataclass in `scripts/lib/weather_api.py`:

```python
@dataclass(frozen=True)
class WeatherData:
    venue: str
    timestamp: str          # ISO-8601
    temperature_c: float
    precipitation_mm: float
    wind_speed_kmh: float
    wet_weather: bool       # precipitation > 5mm
    source: str             # "open-meteo" | "fallback"
```

### InjuryData

Simple dict loaded from `data/injuries/current.json`:

```json
{
  "lastUpdated": "2026-05-01T10:00:00Z",
  "teams": {
    "Panthers": {
      "unavailablePlayers": [
        { "playerName": "Nathan Cleary", "position": "Halfback", "impactScore": 0.85 }
      ],
      "totalImpact": 0.85
    }
  }
}
```

## Architecture

The pipeline remains a single Python script (`scripts/update_tips.py`) calling modules in `scripts/lib/`. No new top-level scripts are needed.

```
scripts/update_tips.py
    └── scripts/lib/
        ├── features.py          ← extend FeatureSet, add new extraction functions
        ├── weather_api.py       ← new: fetch + cache Open-Meteo data
        ├── injury_tracker.py    ← new: load injury JSON, compute impact
        ├── feature_cache.py     ← new: save/load computed features to data/features/
        ├── models/
        │   └── gradient_boosting.py  ← new: XGBoost wrapper
        ├── ensemble.py          ← extend: add weight optimization
        └── backtester.py        ← extend: add per-season/team breakdowns
```

## Components

### 1. Weather API (`scripts/lib/weather_api.py`)

Uses the [Open-Meteo Archive API](https://open-meteo.com/) — free, no auth, unlimited historical data.

```python
VENUE_COORDINATES: dict[str, tuple[float, float]] = {
    "Accor Stadium": (-33.8474, 151.0631),
    "Suncorp Stadium": (-27.4648, 153.0095),
    "AAMI Park": (-37.8250, 144.9834),
    "CommBank Stadium": (-33.8005, 150.9820),
    "Allianz Stadium": (-33.8886, 151.2250),
    "McDonald Jones Stadium": (-32.9167, 151.7500),
    "Queensland Country Bank Stadium": (-19.2590, 146.8169),
    "GIO Stadium": (-35.2533, 149.1028),
    "Cbus Super Stadium": (-28.0667, 153.3833),
    "PointsBet Stadium": (-34.0667, 151.1333),
    "Brookvale Oval": (-33.7667, 151.2667),
    "Leichhardt Oval": (-33.8833, 151.1500),
    "Campbelltown Sports Stadium": (-34.0667, 150.8167),
    "Mt Smart Stadium": (-36.9167, 174.7833),
    "WIN Stadium": (-34.4167, 150.8833),
}

def fetch_weather(venue: str, kickoff_at: str, *, use_cache: bool = True) -> WeatherData | None:
    """Fetch weather for a venue/time. Caches to data/weather_cache.json.
    Returns None on failure — caller uses fallback values."""

def get_venue_season_average(venue: str, month: int) -> WeatherData:
    """Fallback: return average conditions for a venue in a given month."""
```

Cache format (`data/weather_cache.json`): a flat dict keyed by `"{venue}|{date}"`.

### 2. Injury Tracker (`scripts/lib/injury_tracker.py`)

```python
def load_injury_data(path: Path | None = None) -> dict[str, float]:
    """Load injury data. Returns dict mapping team name to total impact score.
    Returns empty dict if file missing — caller treats as zero impact."""

def compute_injury_impact(team: str, injury_data: dict[str, float]) -> float:
    """Return impact score for a team (0.0 if no data)."""
```

No snapshots, no persistence — just read the current JSON and use it.

### 3. Extended Feature Extraction (`scripts/lib/features.py`)

New extraction functions added to the existing module:

```python
# Team home venue mapping for travel distance
TEAM_HOME_VENUES: dict[str, str] = {
    "Broncos": "Suncorp Stadium",
    "Roosters": "Allianz Stadium",
    "Storm": "AAMI Park",
    # ... all 16 teams
}

def compute_travel_distance(away_team: str, venue: str) -> float:
    """Haversine distance from away team's home to match venue (km)."""

def identify_state_of_origin_rounds(season: int) -> set[int]:
    """Return round numbers affected by State of Origin for a given season.
    Hardcoded per season — typically rounds 13, 15, 17."""

def compute_venue_win_rate(team: str, venue: str, history: list[MatchResult]) -> float:
    """Win rate at a specific venue. Returns 0.5 if fewer than 5 games."""
```

The existing `extract_features()` function gains `weather_data` and `injury_data` optional parameters. When `None`, new fields default to their zero/neutral values.

### 4. Feature Cache (`scripts/lib/feature_cache.py`)

Simple JSON cache to avoid recomputing features for historical games:

```python
FEATURE_VERSION = "v2.0"

def save_features(game_id: str, features: FeatureSet) -> None:
    """Write features to data/features/{game_id}.json with version tag."""

def load_features(game_id: str) -> FeatureSet | None:
    """Load cached features. Returns None if missing or version mismatch."""
```

### 5. XGBoost Model (`scripts/lib/models/gradient_boosting.py`)

```python
class XGBoostPredictor:
    """Thin wrapper around XGBClassifier for the NRL prediction pipeline."""

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train with default hyperparameters. No early stopping needed at this scale."""

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return home-win probabilities."""

    def save(self, path: Path) -> None:
        """Persist model to JSON."""

    def load(self, path: Path) -> None:
        """Load model from JSON."""

    def feature_importance(self) -> dict[str, float]:
        """Return feature importance scores keyed by feature name."""
```

Default hyperparameters (stored in `data/config/model_config.yaml`):
- `n_estimators: 100`
- `max_depth: 4`
- `learning_rate: 0.1`
- `objective: binary:logistic`

### 6. Ensemble Weight Optimization (`scripts/lib/ensemble.py`)

Extends the existing ensemble module:

```python
def optimize_weights(
    predictions: dict[str, np.ndarray],  # model_name -> probability array
    actuals: np.ndarray,
) -> dict[str, float]:
    """Find weights that minimize Brier score via scipy SLSQP.
    Constraints: weights >= 0, sum to 1.0.
    Falls back to equal weights if optimization fails."""
```

Optimized weights are written back to `data/config/model_config.yaml` under a `ensemble_weights` key.

### 7. Enhanced Backtester (`scripts/lib/backtester.py`)

Extends the existing `summarize_backtest()` function with additional breakdowns:

```python
@dataclass
class BacktestSummary:
    overall_accuracy: float
    brier_score: float
    log_loss: float
    per_season: dict[int, float]          # season -> accuracy
    per_team: dict[str, float]            # team -> accuracy
    regular_season_accuracy: float
    finals_accuracy: float
    total_games: int
```

## Data Flow

**Weekly prediction run** (unchanged entry point, extended internals):

```
update_tips.py
  1. Fetch fixtures from NRL API
  2. For each fixture:
     a. Check feature cache → skip if hit
     b. Fetch weather (Open-Meteo or fallback)
     c. Load injury data
     d. Extract extended FeatureSet
     e. Save to feature cache
  3. Load XGBoost model from data/models/xgboost_model.json
  4. Generate predictions: ELO + XGBoost + market odds (weighted)
  5. Serialize to data/current_round_tips.json (existing schema)
```

**Training run** (new `--train` flag on update_tips.py):

```
update_tips.py --train
  1. Load all historical data from data/archive/
  2. Extract features for all historical games (with cache)
  3. Walk-forward train XGBoost (seasons N-2, N-1 → validate N)
  4. Optimize ensemble weights on validation predictions
  5. Save model to data/models/xgboost_model.json
  6. Save weights to data/config/model_config.yaml
  7. Print backtest summary
```

## Dependencies

Add to `requirements.txt`:
- `xgboost==2.1.4`
- `scipy==1.15.3` (likely already present via scikit-learn)

No PyTorch, no LightGBM, no SHAP — keep the dependency footprint small.

## Components and Interfaces

See the Components section above for all module interfaces. Key public interfaces:

- `fetch_weather(venue, kickoff_at) -> WeatherData | None` — `scripts/lib/weather_api.py`
- `load_injury_data(path) -> dict[str, float]` — `scripts/lib/injury_tracker.py`
- `extract_features(fixture, elo_engine, history, ladder, weather_data, injury_data) -> FeatureSet` — `scripts/lib/features.py`
- `save_features(game_id, features) / load_features(game_id) -> FeatureSet | None` — `scripts/lib/feature_cache.py`
- `XGBoostPredictor.train / predict_proba / save / load` — `scripts/lib/models/gradient_boosting.py`
- `optimize_weights(predictions, actuals) -> dict[str, float]` — `scripts/lib/ensemble.py`
- `summarize_backtest(...) -> BacktestSummary` — `scripts/lib/backtester.py`

## Correctness Properties

### Property 1: Feature Vector Consistency
Feature vector length must equal `len(FEATURE_NAMES)` for every fixture processed.

**Validates: Requirements 1.6**

### Property 2: Travel Distance Non-Negativity
Travel distance must be non-negative for all team/venue combinations.

**Validates: Requirements 1.1**

### Property 3: Venue Win Rate Bounds
Venue win rate must be in [0.0, 1.0] for all team/venue combinations.

**Validates: Requirements 1.4**

### Property 4: Ensemble Weight Validity
Ensemble weights must sum to 1.0 and each weight must be non-negative.

**Validates: Requirements 5.2**

### Property 5: Probability Bounds
All predicted probabilities must be in (0.0, 1.0).

**Validates: Requirements 4.4**

### Property 6: Pipeline Resilience
The pipeline must produce output even when both the weather API and injury file are unavailable.

**Validates: Requirements 7.2**

## Error Handling

- Weather API failure: log warning, use venue-month average fallback, continue
- Injury file missing: log warning, use zero impact, continue
- XGBoost model file missing: log warning, run ensemble without XGBoost component, continue
- Feature cache version mismatch: silently recompute and overwrite

## Testing Strategy

- Unit tests for each new function in `tests/python/`
- Integration test for the full feature extraction path with mocked weather and injury data
- Backtest smoke test: run against existing archive data and assert accuracy > 50%
