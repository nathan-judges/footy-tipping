"""Integration tests for end-to-end feature extraction.

Tests the complete feature extraction pipeline with mocked external data
sources (weather and injury data) to verify that all features are populated
correctly and validation logic works as expected.

**Validates: Requirements 1.8, 17.2**
"""

from __future__ import annotations

import pytest

from scripts.lib.elo_ratings import EloEngine
from scripts.lib.features import (
    FeatureSet,
    FEATURE_NAMES,
    extract_features,
    feature_vector,
    validate_features,
)
from scripts.lib.historical_data import MatchResult
from scripts.lib.injury_tracker import InjuryStatus, PlayerImpact
from scripts.lib.types import Fixture
from scripts.lib.weather_api import WeatherData


# ---------------------------------------------------------------------------
# Test fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_elo_engine() -> EloEngine:
    """Create a minimal EloEngine with default ratings."""
    return EloEngine()


@pytest.fixture
def sample_history() -> list[MatchResult]:
    """Create a small history of match results for feature extraction."""
    return [
        MatchResult(
            season=2026,
            round_number=1,
            game_id="2026-r01-g01",
            home_team="Panthers",
            away_team="Storm",
            venue="CommBank Stadium",
            home_score=24,
            away_score=18,
            winner="Panthers",
            margin=6,
            kickoff_at="2026-03-06T09:00:00Z",
        ),
        MatchResult(
            season=2026,
            round_number=2,
            game_id="2026-r02-g01",
            home_team="Broncos",
            away_team="Cowboys",
            venue="Suncorp Stadium",
            home_score=20,
            away_score=16,
            winner="Broncos",
            margin=4,
            kickoff_at="2026-03-13T09:00:00Z",
        ),
        MatchResult(
            season=2026,
            round_number=3,
            game_id="2026-r03-g01",
            home_team="Panthers",
            away_team="Eels",
            venue="CommBank Stadium",
            home_score=30,
            away_score=12,
            winner="Panthers",
            margin=18,
            kickoff_at="2026-03-20T09:00:00Z",
        ),
    ]


@pytest.fixture
def sample_ladder() -> dict:
    """Create a sample ladder for feature extraction."""
    return {
        "rows": [
            {"rank": 1, "team": "Panthers", "played": 3, "pointsDiff": 48},
            {"rank": 5, "team": "Broncos", "played": 3, "pointsDiff": 12},
            {"rank": 10, "team": "Storm", "played": 3, "pointsDiff": -6},
        ]
    }


@pytest.fixture
def sample_fixture() -> Fixture:
    """Create a sample fixture for testing."""
    return Fixture(
        game_id="2026-r04-g01",
        nrl_match_id=None,
        nrl_slug=None,
        home_team="Panthers",
        away_team="Broncos",
        venue="CommBank Stadium",
        kickoff_at="2026-03-27T09:00:00Z",
        status="upcoming",
    )


@pytest.fixture
def sample_weather_data() -> WeatherData:
    """Create sample weather data with realistic values."""
    return WeatherData(
        venue="CommBank Stadium",
        timestamp="2026-03-27T09:00:00Z",
        temperature_c=22.5,
        precipitation_mm=2.0,
        wind_speed_kmh=15.0,
        conditions="partly cloudy",
        source="test",
        cached=False,
    )


@pytest.fixture
def sample_injury_data() -> dict[str, InjuryStatus]:
    """Create sample injury data for both teams."""
    return {
        "Panthers": InjuryStatus(
            team="Panthers",
            fixture_date="2026-03-27",
            unavailable_players=(
                PlayerImpact(
                    player_name="Nathan Cleary",
                    position="Halfback",
                    impact_score=0.85,
                    status="injured",
                ),
            ),
            total_impact=0.85,
            key_player_out=True,
        ),
        "Broncos": InjuryStatus(
            team="Broncos",
            fixture_date="2026-03-27",
            unavailable_players=(
                PlayerImpact(
                    player_name="Payne Haas",
                    position="Prop",
                    impact_score=0.65,
                    status="suspended",
                ),
            ),
            total_impact=0.65,
            key_player_out=False,
        ),
    }


# ---------------------------------------------------------------------------
# Test 1: Full data (weather + injury provided)
# ---------------------------------------------------------------------------


def test_extract_features_with_full_data(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
    sample_weather_data: WeatherData,
    sample_injury_data: dict[str, InjuryStatus],
) -> None:
    """Test feature extraction with all external data provided.
    
    Verifies that when both weather and injury data are provided, all
    feature fields are populated correctly with non-default values.
    
    **Validates: Requirement 1.8**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        weather_data=sample_weather_data,
        injury_data=sample_injury_data,
    )

    # Verify weather features are populated from provided data
    assert features.temperature_c == 22.5
    assert features.precipitation_mm == 2.0
    assert features.wind_speed_kmh == 15.0
    assert features.wet_weather is False  # 2.0mm < 5mm threshold

    # Verify injury features are populated from provided data
    assert features.injury_impact_home == 0.85  # Panthers
    assert features.injury_impact_away == 0.65  # Broncos
    assert features.key_player_out_home is True  # Nathan Cleary (0.85 > 0.7)
    assert features.key_player_out_away is False  # Payne Haas (0.65 < 0.7)

    # Verify other features are computed correctly
    assert features.elo_home == 1500.0  # Default ELO
    assert features.elo_away == 1500.0
    assert features.home_advantage == 1.0
    assert features.ladder_pos_diff == -4  # Panthers rank 1, Broncos rank 5 → 1-5 = -4

    # Verify feature vector length matches FEATURE_NAMES
    fv = feature_vector(features)
    assert len(fv) == len(FEATURE_NAMES)


def test_validate_features_with_full_data(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
    sample_weather_data: WeatherData,
    sample_injury_data: dict[str, InjuryStatus],
) -> None:
    """Test that validation passes when all data is provided.
    
    **Validates: Requirement 1.8**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        weather_data=sample_weather_data,
        injury_data=sample_injury_data,
    )

    validation = validate_features(
        features,
        game_id=sample_fixture.game_id,
        home_team=sample_fixture.home_team,
        away_team=sample_fixture.away_team,
    )

    assert validation.is_complete is True
    assert len(validation.missing_fields) == 0
    assert len(validation.warnings) == 0


# ---------------------------------------------------------------------------
# Test 2: No weather data (weather_data=None)
# ---------------------------------------------------------------------------


def test_extract_features_without_weather_data(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
    sample_injury_data: dict[str, InjuryStatus],
) -> None:
    """Test feature extraction when weather_data is None.
    
    Verifies that weather features default to placeholder values when
    no weather data is provided.
    
    **Validates: Requirement 1.8**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        weather_data=None,  # No weather data
        injury_data=sample_injury_data,
    )

    # Verify weather features use defaults
    assert features.temperature_c == 20.0  # Default
    assert features.precipitation_mm == 0.0  # Default
    assert features.wind_speed_kmh == 10.0  # Default
    assert features.wet_weather is False

    # Verify injury features are still populated
    assert features.injury_impact_home == 0.85
    assert features.injury_impact_away == 0.65


def test_validate_features_flags_missing_weather(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
    sample_injury_data: dict[str, InjuryStatus],
) -> None:
    """Test that validation flags missing weather data.
    
    **Validates: Requirement 1.8**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        weather_data=None,
        injury_data=sample_injury_data,
    )

    validation = validate_features(
        features,
        game_id=sample_fixture.game_id,
        home_team=sample_fixture.home_team,
        away_team=sample_fixture.away_team,
    )

    assert validation.is_complete is False
    assert "weather" in validation.missing_fields
    assert len(validation.warnings) == 1
    assert "weather" in validation.warnings[0].lower()


# ---------------------------------------------------------------------------
# Test 3: No injury data (injury_data=None)
# ---------------------------------------------------------------------------


def test_extract_features_without_injury_data(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
    sample_weather_data: WeatherData,
) -> None:
    """Test feature extraction when injury_data is None.
    
    Verifies that injury features default to zero adjustments when
    no injury data is provided.
    
    **Validates: Requirement 1.8**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        weather_data=sample_weather_data,
        injury_data=None,  # No injury data
    )

    # Verify injury features use defaults (zero adjustments)
    assert features.injury_impact_home == 0.0
    assert features.injury_impact_away == 0.0
    assert features.key_player_out_home is False
    assert features.key_player_out_away is False

    # Verify weather features are still populated
    assert features.temperature_c == 22.5
    assert features.precipitation_mm == 2.0


def test_validate_features_flags_missing_injury(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
    sample_weather_data: WeatherData,
) -> None:
    """Test that validation flags missing injury data.
    
    **Validates: Requirement 1.8**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        weather_data=sample_weather_data,
        injury_data=None,
    )

    validation = validate_features(
        features,
        game_id=sample_fixture.game_id,
        home_team=sample_fixture.home_team,
        away_team=sample_fixture.away_team,
    )

    assert validation.is_complete is False
    assert "injury" in validation.missing_fields
    assert len(validation.warnings) == 1
    assert "injury" in validation.warnings[0].lower()


# ---------------------------------------------------------------------------
# Test 4: Both weather and injury missing
# ---------------------------------------------------------------------------


def test_extract_features_without_external_data(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
) -> None:
    """Test feature extraction when both weather and injury data are None.
    
    Verifies that the pipeline continues with default values for both
    weather and injury features.
    
    **Validates: Requirement 1.8**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        weather_data=None,
        injury_data=None,
    )

    # Verify weather defaults
    assert features.temperature_c == 20.0
    assert features.precipitation_mm == 0.0
    assert features.wind_speed_kmh == 10.0
    assert features.wet_weather is False

    # Verify injury defaults
    assert features.injury_impact_home == 0.0
    assert features.injury_impact_away == 0.0
    assert features.key_player_out_home is False
    assert features.key_player_out_away is False

    # Verify core features are still computed
    assert features.elo_diff != 0.0 or features.elo_home == features.elo_away
    assert features.home_advantage == 1.0


def test_validate_features_flags_both_missing(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
) -> None:
    """Test that validation flags both missing weather and injury data.
    
    **Validates: Requirement 1.8**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        weather_data=None,
        injury_data=None,
    )

    validation = validate_features(
        features,
        game_id=sample_fixture.game_id,
        home_team=sample_fixture.home_team,
        away_team=sample_fixture.away_team,
    )

    assert validation.is_complete is False
    assert "weather" in validation.missing_fields
    assert "injury" in validation.missing_fields
    assert len(validation.warnings) == 2


# ---------------------------------------------------------------------------
# Test 5: Backward compatibility (4 positional args only)
# ---------------------------------------------------------------------------


def test_extract_features_backward_compatible_signature(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
) -> None:
    """Test backward compatibility with 4 positional arguments.
    
    Verifies that extract_features() can be called with only the original
    4 required arguments (fixture, elo_engine, history, ladder) without
    providing weather_data or injury_data.
    
    **Validates: Requirement 1.8**
    """
    # Call with only 4 positional arguments (no weather/injury)
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
    )

    # Should return a valid FeatureSet with defaults
    assert isinstance(features, FeatureSet)
    assert features.temperature_c == 20.0
    assert features.injury_impact_home == 0.0

    # Core features should still be computed
    assert features.elo_home == 1500.0
    assert features.home_advantage == 1.0


# ---------------------------------------------------------------------------
# Test 6: Feature vector length consistency
# ---------------------------------------------------------------------------


def test_feature_vector_length_matches_feature_names(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
) -> None:
    """Test that feature_vector() length matches FEATURE_NAMES length.
    
    Verifies the consistency between the feature vector output and the
    feature names list, which is critical for model training.
    
    **Validates: Requirement 17.2**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
    )

    fv = feature_vector(features)

    assert len(fv) == len(FEATURE_NAMES)
    assert len(FEATURE_NAMES) == 27  # 9 existing + 10 NRL + 4 weather + 4 injury


def test_feature_vector_all_numeric(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
    sample_weather_data: WeatherData,
    sample_injury_data: dict[str, InjuryStatus],
) -> None:
    """Test that all feature vector values are numeric (float).
    
    **Validates: Requirement 17.2**
    """
    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        weather_data=sample_weather_data,
        injury_data=sample_injury_data,
    )

    fv = feature_vector(features)

    assert all(isinstance(v, float) for v in fv), "All feature values must be floats"


# ---------------------------------------------------------------------------
# Test 7: Wet weather threshold
# ---------------------------------------------------------------------------


def test_wet_weather_flag_above_threshold() -> None:
    """Test that wet_weather flag is set when precipitation > 5mm.
    
    **Validates: Requirement 1.8**
    """
    weather_data = WeatherData(
        venue="Suncorp Stadium",
        timestamp="2026-03-27T09:00:00Z",
        temperature_c=18.0,
        precipitation_mm=6.0,  # Above 5mm threshold
        wind_speed_kmh=20.0,
        conditions="rain",
        source="test",
        cached=False,
    )

    fixture = Fixture(
        game_id="2026-r04-g01",
        nrl_match_id=None,
        nrl_slug=None,
        home_team="Broncos",
        away_team="Cowboys",
        venue="Suncorp Stadium",
        kickoff_at="2026-03-27T09:00:00Z",
        status="upcoming",
    )

    features = extract_features(
        fixture,
        EloEngine(),
        [],
        {"rows": []},
        weather_data=weather_data,
    )

    assert features.precipitation_mm == 6.0
    assert features.wet_weather is True


def test_wet_weather_flag_below_threshold() -> None:
    """Test that wet_weather flag is not set when precipitation <= 5mm.
    
    **Validates: Requirement 1.8**
    """
    weather_data = WeatherData(
        venue="Suncorp Stadium",
        timestamp="2026-03-27T09:00:00Z",
        temperature_c=18.0,
        precipitation_mm=4.0,  # Below 5mm threshold
        wind_speed_kmh=20.0,
        conditions="light rain",
        source="test",
        cached=False,
    )

    fixture = Fixture(
        game_id="2026-r04-g01",
        nrl_match_id=None,
        nrl_slug=None,
        home_team="Broncos",
        away_team="Cowboys",
        venue="Suncorp Stadium",
        kickoff_at="2026-03-27T09:00:00Z",
        status="upcoming",
    )

    features = extract_features(
        fixture,
        EloEngine(),
        [],
        {"rows": []},
        weather_data=weather_data,
    )

    assert features.precipitation_mm == 4.0
    assert features.wet_weather is False


# ---------------------------------------------------------------------------
# Test 8: Key player threshold
# ---------------------------------------------------------------------------


def test_key_player_out_above_threshold() -> None:
    """Test that key_player_out flag is set when impact > 0.7.
    
    **Validates: Requirement 1.8**
    """
    injury_data = {
        "Panthers": InjuryStatus(
            team="Panthers",
            fixture_date="2026-03-27",
            unavailable_players=(
                PlayerImpact(
                    player_name="Nathan Cleary",
                    position="Halfback",
                    impact_score=0.85,  # Above 0.7 threshold
                    status="injured",
                ),
            ),
            total_impact=0.85,
            key_player_out=True,
        ),
    }

    fixture = Fixture(
        game_id="2026-r04-g01",
        nrl_match_id=None,
        nrl_slug=None,
        home_team="Panthers",
        away_team="Broncos",
        venue="CommBank Stadium",
        kickoff_at="2026-03-27T09:00:00Z",
        status="upcoming",
    )

    features = extract_features(
        fixture,
        EloEngine(),
        [],
        {"rows": []},
        injury_data=injury_data,
    )

    assert features.injury_impact_home == 0.85
    assert features.key_player_out_home is True


def test_key_player_out_below_threshold() -> None:
    """Test that key_player_out flag is not set when impact <= 0.7.
    
    **Validates: Requirement 1.8**
    """
    injury_data = {
        "Broncos": InjuryStatus(
            team="Broncos",
            fixture_date="2026-03-27",
            unavailable_players=(
                PlayerImpact(
                    player_name="Payne Haas",
                    position="Prop",
                    impact_score=0.65,  # Below 0.7 threshold
                    status="suspended",
                ),
            ),
            total_impact=0.65,
            key_player_out=False,
        ),
    }

    fixture = Fixture(
        game_id="2026-r04-g01",
        nrl_match_id=None,
        nrl_slug=None,
        home_team="Panthers",
        away_team="Broncos",
        venue="CommBank Stadium",
        kickoff_at="2026-03-27T09:00:00Z",
        status="upcoming",
    )

    features = extract_features(
        fixture,
        EloEngine(),
        [],
        {"rows": []},
        injury_data=injury_data,
    )

    assert features.injury_impact_away == 0.65
    assert features.key_player_out_away is False


# ---------------------------------------------------------------------------
# Test 9: Empty injury data for a team
# ---------------------------------------------------------------------------


def test_extract_features_with_partial_injury_data(
    sample_fixture: Fixture,
    minimal_elo_engine: EloEngine,
    sample_history: list[MatchResult],
    sample_ladder: dict,
) -> None:
    """Test feature extraction when injury data exists but team is not present.
    
    Verifies that when injury_data dict is provided but doesn't contain
    an entry for one or both teams, those teams default to zero adjustments.
    
    **Validates: Requirement 1.8**
    """
    # Injury data only for Panthers, not Broncos
    injury_data = {
        "Panthers": InjuryStatus(
            team="Panthers",
            fixture_date="2026-03-27",
            unavailable_players=(
                PlayerImpact(
                    player_name="Nathan Cleary",
                    position="Halfback",
                    impact_score=0.85,
                    status="injured",
                ),
            ),
            total_impact=0.85,
            key_player_out=True,
        ),
    }

    features = extract_features(
        sample_fixture,
        minimal_elo_engine,
        sample_history,
        sample_ladder,
        injury_data=injury_data,
    )

    # Panthers should have injury data
    assert features.injury_impact_home == 0.85
    assert features.key_player_out_home is True

    # Broncos should default to zero (not in injury_data dict)
    assert features.injury_impact_away == 0.0
    assert features.key_player_out_away is False
