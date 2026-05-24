"""Tests for the feature extraction engine."""

from scripts.lib.elo_ratings import EloEngine
from scripts.lib.features import (
    FeatureSet,
    compute_venue_specific_win_rate,
    extract_features,
    feature_vector,
    FEATURE_NAMES,
)
from scripts.lib.historical_data import MatchResult
from scripts.lib.types import Fixture


def _make_fixture(**overrides) -> Fixture:
    defaults = dict(
        game_id="test-g01",
        nrl_match_id=None,
        nrl_slug=None,
        home_team="Panthers",
        away_team="Dragons",
        venue="BlueBet Stadium",
        kickoff_at="2026-04-24T09:50:00Z",
        status="upcoming",
    )
    defaults.update(overrides)
    return Fixture(**defaults)


def _make_history() -> list[MatchResult]:
    return [
        MatchResult(season=2026, round_number=1, game_id="g1", home_team="Panthers", away_team="Storm", venue="BlueBet Stadium", home_score=24, away_score=12, winner="Panthers", margin=12, kickoff_at="2026-03-06T09:00:00Z"),
        MatchResult(season=2026, round_number=2, game_id="g2", home_team="Dragons", away_team="Panthers", venue="WIN Stadium", home_score=10, away_score=20, winner="Panthers", margin=10, kickoff_at="2026-03-13T09:00:00Z"),
        MatchResult(season=2026, round_number=3, game_id="g3", home_team="Panthers", away_team="Eels", venue="BlueBet Stadium", home_score=30, away_score=6, winner="Panthers", margin=24, kickoff_at="2026-03-20T09:00:00Z"),
        MatchResult(season=2026, round_number=3, game_id="g4", home_team="Dragons", away_team="Storm", venue="WIN Stadium", home_score=18, away_score=14, winner="Dragons", margin=4, kickoff_at="2026-03-20T10:00:00Z"),
    ]


def test_feature_vector_length() -> None:
    fs = FeatureSet()
    fv = feature_vector(fs)
    assert len(fv) == len(FEATURE_NAMES) == 27


def test_feature_vector_names_match() -> None:
    assert FEATURE_NAMES[0] == "elo_diff"
    assert FEATURE_NAMES[8] == "defensive_diff"
    assert FEATURE_NAMES[9] == "travel_distance_km"
    assert FEATURE_NAMES[18] == "finals_match"
    assert FEATURE_NAMES[19] == "temperature_c"
    assert FEATURE_NAMES[20] == "precipitation_mm"
    assert FEATURE_NAMES[21] == "wind_speed_kmh"
    assert FEATURE_NAMES[22] == "wet_weather"
    assert FEATURE_NAMES[23] == "injury_impact_home"
    assert FEATURE_NAMES[24] == "injury_impact_away"
    assert FEATURE_NAMES[25] == "key_player_out_home"
    assert FEATURE_NAMES[-1] == "key_player_out_away"


def test_recent_form_with_empty_history() -> None:
    engine = EloEngine()
    fixture = _make_fixture()
    ladder = {"rows": []}
    features = extract_features(fixture, engine, [], ladder)
    # With empty history, form defaults to 0.5
    assert features.form_home_5 == 0.5
    assert features.form_away_5 == 0.5


def test_extract_features_returns_featureset() -> None:
    engine = EloEngine()
    fixture = _make_fixture()
    history = _make_history()
    ladder = {
        "rows": [
            {"rank": 1, "team": "Panthers", "played": 3, "pointsDiff": 46},
            {"rank": 10, "team": "Dragons", "played": 2, "pointsDiff": -8},
        ]
    }
    features = extract_features(fixture, engine, history, ladder)

    assert isinstance(features, FeatureSet)
    # Panthers have won all 3 games in history
    assert features.form_home_5 == 1.0
    # Dragons: won 1 of 2
    assert features.form_away_5 == 0.5
    # Ladder diff: Panthers rank 1, Dragons rank 10 → 1-10 = -9
    assert features.ladder_pos_diff == -9


def test_feature_vector_produces_floats() -> None:
    fs = FeatureSet(elo_diff=50.0, ladder_pos_diff=-5, rest_days_home=7, rest_days_away=5)
    fv = feature_vector(fs)
    assert all(isinstance(v, float) for v in fv)


def test_weather_fields_defaults() -> None:
    fs = FeatureSet()
    assert fs.temperature_c == 20.0
    assert fs.precipitation_mm == 0.0
    assert fs.wind_speed_kmh == 10.0
    assert fs.wet_weather is False


def test_weather_fields_in_feature_vector() -> None:
    fs = FeatureSet(
        temperature_c=28.5,
        precipitation_mm=12.0,
        wind_speed_kmh=35.0,
        wet_weather=True,
    )
    fv = feature_vector(fs)
    # Weather features are at indices 19-22 (injury features follow at 23-26)
    assert fv[19] == 28.5
    assert fv[20] == 12.0
    assert fv[21] == 35.0
    assert fv[22] == 1.0  # wet_weather True → 1.0


def test_wet_weather_false_encodes_as_zero() -> None:
    fs = FeatureSet(wet_weather=False)
    fv = feature_vector(fs)
    assert fv[22] == 0.0


def test_injury_fields_defaults() -> None:
    fs = FeatureSet()
    assert fs.injury_impact_home == 0.0
    assert fs.injury_impact_away == 0.0
    assert fs.key_player_out_home is False
    assert fs.key_player_out_away is False


def test_injury_fields_in_feature_vector() -> None:
    fs = FeatureSet(
        injury_impact_home=0.85,
        injury_impact_away=0.3,
        key_player_out_home=True,
        key_player_out_away=False,
    )
    fv = feature_vector(fs)
    # Injury features are the last 4 entries
    assert fv[-4] == 0.85
    assert fv[-3] == 0.3
    assert fv[-2] == 1.0   # key_player_out_home True → 1.0
    assert fv[-1] == 0.0   # key_player_out_away False → 0.0


def test_key_player_out_encodes_as_float() -> None:
    fs_true = FeatureSet(key_player_out_home=True, key_player_out_away=True)
    fv = feature_vector(fs_true)
    assert fv[-2] == 1.0
    assert fv[-1] == 1.0

    fs_false = FeatureSet(key_player_out_home=False, key_player_out_away=False)
    fv = feature_vector(fs_false)
    assert fv[-2] == 0.0
    assert fv[-1] == 0.0


# ---------------------------------------------------------------------------
# compute_venue_specific_win_rate tests
# ---------------------------------------------------------------------------

def _make_venue_history() -> list[MatchResult]:
    """Build a small history with games at two venues."""
    def _r(gid, home, away, venue, home_score, away_score, winner):
        return MatchResult(
            season=2025,
            round_number=1,
            game_id=gid,
            home_team=home,
            away_team=away,
            venue=venue,
            home_score=home_score,
            away_score=away_score,
            winner=winner,
            margin=abs(home_score - away_score),
            kickoff_at="2025-03-01T09:00:00Z",
        )

    return [
        # Panthers at Suncorp (home) — 3 wins, 1 loss
        _r("v1", "Panthers", "Broncos",  "Suncorp Stadium", 24, 12, "Panthers"),
        _r("v2", "Panthers", "Storm",    "Suncorp Stadium", 18, 20, "Storm"),
        _r("v3", "Panthers", "Raiders",  "Suncorp Stadium", 30,  6, "Panthers"),
        _r("v4", "Panthers", "Cowboys",  "Suncorp Stadium", 22, 10, "Panthers"),
        # Panthers at Suncorp (away) — 1 win
        _r("v5", "Broncos",  "Panthers", "Suncorp Stadium", 10, 20, "Panthers"),
        # Panthers at AAMI Park — only 2 games (below min_games)
        _r("v6", "Panthers", "Storm",    "AAMI Park",       14, 20, "Storm"),
        _r("v7", "Storm",    "Panthers", "AAMI Park",       22, 10, "Storm"),
        # Broncos at Suncorp — 2 games (below min_games)
        _r("v8", "Broncos",  "Raiders",  "Suncorp Stadium", 20, 10, "Broncos"),
        _r("v9", "Broncos",  "Storm",    "Suncorp Stadium", 16, 18, "Storm"),
    ]


def test_venue_win_rate_sufficient_data() -> None:
    """Win rate is computed correctly when >= min_games exist."""
    history = _make_venue_history()
    # Panthers at Suncorp: 5 games (v1-v5), 4 wins
    rate = compute_venue_specific_win_rate("Panthers", "Suncorp Stadium", history, min_games=5)
    assert rate == 4 / 5


def test_venue_win_rate_insufficient_data_returns_neutral() -> None:
    """Returns 0.5 when fewer than min_games have been played at the venue."""
    history = _make_venue_history()
    # Panthers at AAMI Park: only 2 games
    rate = compute_venue_specific_win_rate("Panthers", "AAMI Park", history, min_games=5)
    assert rate == 0.5


def test_venue_win_rate_no_games_returns_neutral() -> None:
    """Returns 0.5 when the team has never played at the venue."""
    history = _make_venue_history()
    rate = compute_venue_specific_win_rate("Panthers", "Unknown Venue", history, min_games=5)
    assert rate == 0.5


def test_venue_win_rate_counts_both_home_and_away() -> None:
    """Games where the team is the away side are included in the count."""
    history = _make_venue_history()
    # v5 is Panthers as away team at Suncorp — must be included
    rate = compute_venue_specific_win_rate("Panthers", "Suncorp Stadium", history, min_games=5)
    # 5 total games (4 home + 1 away), 4 wins
    assert rate == pytest.approx(0.8)


def test_venue_win_rate_custom_min_games() -> None:
    """Custom min_games threshold is respected."""
    history = _make_venue_history()
    # Panthers at AAMI Park: 2 games, 0 wins — valid with min_games=2
    rate = compute_venue_specific_win_rate("Panthers", "AAMI Park", history, min_games=2)
    assert rate == 0.0


def test_venue_win_rate_all_wins() -> None:
    """Returns 1.0 when the team has won every game at the venue."""
    history = [
        MatchResult(
            season=2025, round_number=i, game_id=f"w{i}",
            home_team="Panthers", away_team="Eels",
            venue="BlueBet Stadium",
            home_score=20, away_score=10, winner="Panthers",
            margin=10, kickoff_at="2025-03-01T09:00:00Z",
        )
        for i in range(1, 7)  # 6 games, all Panthers wins
    ]
    rate = compute_venue_specific_win_rate("Panthers", "BlueBet Stadium", history, min_games=5)
    assert rate == 1.0


def test_venue_win_rate_all_losses() -> None:
    """Returns 0.0 when the team has lost every game at the venue."""
    history = [
        MatchResult(
            season=2025, round_number=i, game_id=f"l{i}",
            home_team="Storm", away_team="Panthers",
            venue="AAMI Park",
            home_score=20, away_score=10, winner="Storm",
            margin=10, kickoff_at="2025-03-01T09:00:00Z",
        )
        for i in range(1, 7)  # 6 games, all Storm wins
    ]
    rate = compute_venue_specific_win_rate("Panthers", "AAMI Park", history, min_games=5)
    assert rate == 0.0


def test_venue_win_rate_exactly_at_min_games_threshold() -> None:
    """Returns a computed rate (not 0.5) when total_games == min_games."""
    history = [
        MatchResult(
            season=2025, round_number=i, game_id=f"e{i}",
            home_team="Panthers", away_team="Eels",
            venue="BlueBet Stadium",
            home_score=20 if i % 2 == 0 else 10,
            away_score=10 if i % 2 == 0 else 20,
            winner="Panthers" if i % 2 == 0 else "Eels",
            margin=10, kickoff_at="2025-03-01T09:00:00Z",
        )
        for i in range(1, 6)  # exactly 5 games
    ]
    rate = compute_venue_specific_win_rate("Panthers", "BlueBet Stadium", history, min_games=5)
    # 2 wins out of 5 (i=2,4 are Panthers wins)
    assert rate == pytest.approx(2 / 5)
