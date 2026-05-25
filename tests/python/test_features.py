"""Tests for the feature extraction engine."""

import pytest

from scripts.lib.elo_ratings import EloEngine
from scripts.lib.features import (
    FeatureSet,
    RIVALRY_PAIRS,
    compute_travel_distance,
    compute_venue_specific_win_rate,
    extract_features,
    feature_vector,
    identify_state_of_origin_rounds,
    is_rivalry_game,
    is_state_of_origin_round,
    FEATURE_NAMES,
    TEAM_HOME_VENUES,
)
from scripts.lib.historical_data import MatchResult
from scripts.lib.types import Fixture
from scripts.lib.weather_api import VENUE_COORDINATES


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


# ---------------------------------------------------------------------------
# is_rivalry_game / RIVALRY_PAIRS tests  (task 7.4)
# ---------------------------------------------------------------------------

def test_rivalry_game_known_pair_home_away() -> None:
    """Broncos vs Cowboys is a known QLD derby rivalry."""
    assert is_rivalry_game("Broncos", "Cowboys") is True


def test_rivalry_game_known_pair_reversed() -> None:
    """Rivalry detection is symmetric — order of teams doesn't matter."""
    assert is_rivalry_game("Cowboys", "Broncos") is True


def test_rivalry_game_sydney_derby() -> None:
    """Roosters vs Rabbitohs is the classic Sydney derby."""
    assert is_rivalry_game("Roosters", "Rabbitohs") is True
    assert is_rivalry_game("Rabbitohs", "Roosters") is True


def test_rivalry_game_western_sydney_derby() -> None:
    """Panthers vs Eels is the Western Sydney derby."""
    assert is_rivalry_game("Panthers", "Eels") is True
    assert is_rivalry_game("Eels", "Panthers") is True


def test_rivalry_game_storm_broncos() -> None:
    """Storm vs Broncos is a historical finals rivalry."""
    assert is_rivalry_game("Storm", "Broncos") is True


def test_rivalry_game_non_rivalry_returns_false() -> None:
    """Two teams with no defined rivalry return False."""
    assert is_rivalry_game("Panthers", "Warriors") is False


def test_rivalry_game_same_team_returns_false() -> None:
    """A team cannot be a rival of itself."""
    assert is_rivalry_game("Broncos", "Broncos") is False


def test_rivalry_game_unknown_team_returns_false() -> None:
    """Unknown team names that don't appear in any rivalry pair return False."""
    assert is_rivalry_game("UnknownFC", "Broncos") is False
    assert is_rivalry_game("Broncos", "UnknownFC") is False


def test_rivalry_game_all_pairs_are_symmetric() -> None:
    """Every pair in RIVALRY_PAIRS is detected regardless of argument order."""
    for pair in RIVALRY_PAIRS:
        teams = list(pair)
        assert is_rivalry_game(teams[0], teams[1]) is True
        assert is_rivalry_game(teams[1], teams[0]) is True


def test_rivalry_pairs_are_frozensets_of_two() -> None:
    """Each entry in RIVALRY_PAIRS is a frozenset containing exactly two teams."""
    for pair in RIVALRY_PAIRS:
        assert isinstance(pair, frozenset)
        assert len(pair) == 2


def test_rivalry_pairs_no_self_rivalry() -> None:
    """No rivalry pair contains the same team twice."""
    for pair in RIVALRY_PAIRS:
        teams = list(pair)
        assert teams[0] != teams[1]


def test_rivalry_game_sharks_dragons() -> None:
    """Sharks vs Dragons is a recognised rivalry."""
    assert is_rivalry_game("Sharks", "Dragons") is True
    assert is_rivalry_game("Dragons", "Sharks") is True


def test_rivalry_game_feature_set_field() -> None:
    """FeatureSet.rivalry_game defaults to False and can be set to True."""
    fs_default = FeatureSet()
    assert fs_default.rivalry_game is False

    fs_rivalry = FeatureSet(rivalry_game=True)
    fv = feature_vector(fs_rivalry)
    # rivalry_game is at index 17 in FEATURE_NAMES
    rivalry_idx = FEATURE_NAMES.index("rivalry_game")
    assert fv[rivalry_idx] == 1.0


def test_rivalry_game_encodes_as_zero_when_false() -> None:
    """rivalry_game=False encodes as 0.0 in the feature vector."""
    fs = FeatureSet(rivalry_game=False)
    fv = feature_vector(fs)
    rivalry_idx = FEATURE_NAMES.index("rivalry_game")
    assert fv[rivalry_idx] == 0.0


# ---------------------------------------------------------------------------
# compute_travel_distance tests (task 7.5)
# ---------------------------------------------------------------------------

def test_travel_distance_brisbane_to_sydney() -> None:
    """Broncos traveling from Brisbane (Suncorp) to Sydney (Allianz) is ~730km."""
    distance = compute_travel_distance("Broncos", "Allianz Stadium")
    # Approximate distance Brisbane to Sydney is ~730km
    assert 700 <= distance <= 760


def test_travel_distance_melbourne_to_brisbane() -> None:
    """Storm traveling from Melbourne (AAMI Park) to Brisbane (Suncorp) is ~1370km."""
    distance = compute_travel_distance("Storm", "Suncorp Stadium")
    # Approximate distance Melbourne to Brisbane is ~1370km
    assert 1300 <= distance <= 1400


def test_travel_distance_sydney_to_canberra() -> None:
    """Roosters traveling from Sydney (Allianz) to Canberra (GIO Stadium) is ~250km."""
    distance = compute_travel_distance("Roosters", "GIO Stadium")
    # Approximate distance Sydney to Canberra is ~250km
    assert 240 <= distance <= 280


def test_travel_distance_auckland_to_sydney() -> None:
    """Warriors traveling from Auckland (Mt Smart) to Sydney (Allianz) is ~2150km."""
    distance = compute_travel_distance("Warriors", "Allianz Stadium")
    # Approximate distance Auckland to Sydney is ~2150km
    assert 2100 <= distance <= 2200


def test_travel_distance_townsville_to_melbourne() -> None:
    """Cowboys traveling from Townsville to Melbourne is ~2070km."""
    distance = compute_travel_distance("Cowboys", "AAMI Park")
    # Approximate distance Townsville to Melbourne is ~2070km
    assert 2000 <= distance <= 2150


def test_travel_distance_same_city_is_small() -> None:
    """Teams playing in their home city have minimal travel distance."""
    # Broncos playing at Suncorp (their home venue)
    distance = compute_travel_distance("Broncos", "Suncorp Stadium")
    assert distance == 0.0


def test_travel_distance_shared_venue_is_zero() -> None:
    """Teams that share a home venue have zero travel distance to that venue."""
    # Eels and Panthers both play at CommBank Stadium
    distance_eels = compute_travel_distance("Eels", "CommBank Stadium")
    distance_panthers = compute_travel_distance("Panthers", "CommBank Stadium")
    assert distance_eels == 0.0
    assert distance_panthers == 0.0


def test_travel_distance_unknown_team_returns_zero() -> None:
    """Unknown team names return 0.0 distance."""
    distance = compute_travel_distance("UnknownFC", "Suncorp Stadium")
    assert distance == 0.0


def test_travel_distance_unknown_venue_returns_zero() -> None:
    """Unknown venue names return 0.0 distance."""
    distance = compute_travel_distance("Broncos", "Unknown Stadium")
    assert distance == 0.0


def test_travel_distance_both_unknown_returns_zero() -> None:
    """Both unknown team and venue return 0.0 distance."""
    distance = compute_travel_distance("UnknownFC", "Unknown Stadium")
    assert distance == 0.0


def test_travel_distance_gold_coast_to_sydney() -> None:
    """Titans traveling from Gold Coast (Cbus Super Stadium) to Sydney is ~680km."""
    distance = compute_travel_distance("Titans", "Allianz Stadium")
    # Approximate distance Gold Coast to Sydney is ~680km
    assert 670 <= distance <= 690


def test_travel_distance_newcastle_to_brisbane() -> None:
    """Knights traveling from Newcastle to Brisbane is ~620km."""
    distance = compute_travel_distance("Knights", "Suncorp Stadium")
    # Approximate distance Newcastle to Brisbane is ~620km
    assert 600 <= distance <= 650


def test_travel_distance_wollongong_to_sydney() -> None:
    """Dragons traveling from Wollongong (WIN Stadium) to Sydney is ~67km."""
    distance = compute_travel_distance("Dragons", "Allianz Stadium")
    # Approximate distance Wollongong to Sydney is ~67km
    assert 60 <= distance <= 75


def test_travel_distance_feature_set_field() -> None:
    """FeatureSet.travel_distance_km defaults to 0.0 and can be set."""
    fs_default = FeatureSet()
    assert fs_default.travel_distance_km == 0.0

    fs_travel = FeatureSet(travel_distance_km=1234.5)
    fv = feature_vector(fs_travel)
    # travel_distance_km is at index 9 in FEATURE_NAMES
    travel_idx = FEATURE_NAMES.index("travel_distance_km")
    assert fv[travel_idx] == 1234.5


def test_travel_distance_all_teams_have_home_venue() -> None:
    """Every NRL team has a defined home venue."""
    expected_teams = {
        "Broncos", "Roosters", "Storm", "Panthers", "Rabbitohs",
        "Raiders", "Cowboys", "Knights", "Sharks", "Sea Eagles",
        "Eels", "Tigers", "Dragons", "Bulldogs", "Dolphins", "Titans", "Warriors"
    }
    assert set(TEAM_HOME_VENUES.keys()) == expected_teams


def test_travel_distance_all_home_venues_have_coordinates() -> None:
    """Every home venue has coordinates defined in VENUE_COORDINATES."""
    for venue in TEAM_HOME_VENUES.values():
        assert venue in VENUE_COORDINATES, f"Missing coordinates for {venue}"


def test_travel_distance_coordinates_are_valid() -> None:
    """All venue coordinates are valid lat/lon pairs."""
    for venue, (lat, lon) in VENUE_COORDINATES.items():
        assert -90 <= lat <= 90, f"Invalid latitude for {venue}: {lat}"
        assert -180 <= lon <= 180, f"Invalid longitude for {venue}: {lon}"


# ---------------------------------------------------------------------------
# State of Origin detection tests (task 7.5)
# ---------------------------------------------------------------------------

def test_identify_state_of_origin_rounds_2026() -> None:
    """2026 State of Origin rounds are 13, 15, 17."""
    rounds = identify_state_of_origin_rounds(2026)
    assert rounds == {13, 15, 17}


def test_identify_state_of_origin_rounds_2025() -> None:
    """2025 State of Origin rounds are 13, 15, 17."""
    rounds = identify_state_of_origin_rounds(2025)
    assert rounds == {13, 15, 17}


def test_identify_state_of_origin_rounds_2024() -> None:
    """2024 State of Origin rounds are 13, 15, 17."""
    rounds = identify_state_of_origin_rounds(2024)
    assert rounds == {13, 15, 17}


def test_identify_state_of_origin_rounds_2023() -> None:
    """2023 State of Origin rounds are 13, 15, 17."""
    rounds = identify_state_of_origin_rounds(2023)
    assert rounds == {13, 15, 17}


def test_identify_state_of_origin_rounds_unknown_year_uses_default() -> None:
    """Unknown years fall back to default rounds {13, 15, 17}."""
    rounds = identify_state_of_origin_rounds(2030)
    assert rounds == {13, 15, 17}


def test_identify_state_of_origin_rounds_returns_set() -> None:
    """identify_state_of_origin_rounds returns a set of integers."""
    rounds = identify_state_of_origin_rounds(2026)
    assert isinstance(rounds, set)
    assert all(isinstance(r, int) for r in rounds)


def test_is_state_of_origin_round_true_for_round_13() -> None:
    """Round 13 is a State of Origin round in 2026."""
    assert is_state_of_origin_round(2026, 13) is True


def test_is_state_of_origin_round_true_for_round_15() -> None:
    """Round 15 is a State of Origin round in 2026."""
    assert is_state_of_origin_round(2026, 15) is True


def test_is_state_of_origin_round_true_for_round_17() -> None:
    """Round 17 is a State of Origin round in 2026."""
    assert is_state_of_origin_round(2026, 17) is True


def test_is_state_of_origin_round_false_for_round_1() -> None:
    """Round 1 is not a State of Origin round."""
    assert is_state_of_origin_round(2026, 1) is False


def test_is_state_of_origin_round_false_for_round_10() -> None:
    """Round 10 is not a State of Origin round."""
    assert is_state_of_origin_round(2026, 10) is False


def test_is_state_of_origin_round_false_for_round_27() -> None:
    """Round 27 (finals) is not a State of Origin round."""
    assert is_state_of_origin_round(2026, 27) is False


def test_is_state_of_origin_round_works_across_seasons() -> None:
    """State of Origin detection works for multiple seasons."""
    assert is_state_of_origin_round(2023, 13) is True
    assert is_state_of_origin_round(2024, 15) is True
    assert is_state_of_origin_round(2025, 17) is True


def test_state_of_origin_round_feature_set_field() -> None:
    """FeatureSet.state_of_origin_round defaults to False and can be set."""
    fs_default = FeatureSet()
    assert fs_default.state_of_origin_round is False

    fs_origin = FeatureSet(state_of_origin_round=True)
    fv = feature_vector(fs_origin)
    # state_of_origin_round is at index 12 in FEATURE_NAMES
    origin_idx = FEATURE_NAMES.index("state_of_origin_round")
    assert fv[origin_idx] == 1.0


def test_state_of_origin_round_encodes_as_zero_when_false() -> None:
    """state_of_origin_round=False encodes as 0.0 in the feature vector."""
    fs = FeatureSet(state_of_origin_round=False)
    fv = feature_vector(fs)
    origin_idx = FEATURE_NAMES.index("state_of_origin_round")
    assert fv[origin_idx] == 0.0


def test_origin_affected_players_feature_set_fields() -> None:
    """FeatureSet has origin_affected_home and origin_affected_away fields."""
    fs = FeatureSet(origin_affected_home=3, origin_affected_away=2)
    fv = feature_vector(fs)
    
    home_idx = FEATURE_NAMES.index("origin_affected_home")
    away_idx = FEATURE_NAMES.index("origin_affected_away")
    
    assert fv[home_idx] == 3.0
    assert fv[away_idx] == 2.0


def test_origin_affected_players_defaults_to_zero() -> None:
    """origin_affected fields default to 0."""
    fs = FeatureSet()
    assert fs.origin_affected_home == 0
    assert fs.origin_affected_away == 0


# ---------------------------------------------------------------------------
# Short turnaround tests (task 7.5)
# ---------------------------------------------------------------------------

def test_short_turnaround_feature_set_fields() -> None:
    """FeatureSet has short_turnaround_home and short_turnaround_away fields."""
    fs = FeatureSet(short_turnaround_home=True, short_turnaround_away=False)
    fv = feature_vector(fs)
    
    home_idx = FEATURE_NAMES.index("short_turnaround_home")
    away_idx = FEATURE_NAMES.index("short_turnaround_away")
    
    assert fv[home_idx] == 1.0
    assert fv[away_idx] == 0.0


def test_short_turnaround_defaults_to_false() -> None:
    """short_turnaround fields default to False."""
    fs = FeatureSet()
    assert fs.short_turnaround_home is False
    assert fs.short_turnaround_away is False


# ---------------------------------------------------------------------------
# Finals match tests (task 7.5)
# ---------------------------------------------------------------------------

def test_finals_match_feature_set_field() -> None:
    """FeatureSet.finals_match defaults to False and can be set."""
    fs_default = FeatureSet()
    assert fs_default.finals_match is False

    fs_finals = FeatureSet(finals_match=True)
    fv = feature_vector(fs_finals)
    finals_idx = FEATURE_NAMES.index("finals_match")
    assert fv[finals_idx] == 1.0


def test_finals_match_encodes_as_zero_when_false() -> None:
    """finals_match=False encodes as 0.0 in the feature vector."""
    fs = FeatureSet(finals_match=False)
    fv = feature_vector(fs)
    finals_idx = FEATURE_NAMES.index("finals_match")
    assert fv[finals_idx] == 0.0


# ---------------------------------------------------------------------------
# Integration tests for NRL-specific features (task 7.5)
# ---------------------------------------------------------------------------

def test_nrl_features_all_present_in_feature_names() -> None:
    """All NRL-specific feature names are present in FEATURE_NAMES."""
    nrl_features = [
        "travel_distance_km",
        "short_turnaround_home",
        "short_turnaround_away",
        "state_of_origin_round",
        "origin_affected_home",
        "origin_affected_away",
        "venue_win_rate_home",
        "venue_win_rate_away",
        "rivalry_game",
        "finals_match",
    ]
    for feature in nrl_features:
        assert feature in FEATURE_NAMES, f"Missing NRL feature: {feature}"


def test_nrl_features_produce_numeric_values() -> None:
    """All NRL-specific features produce numeric values in feature vector."""
    fs = FeatureSet(
        travel_distance_km=1234.5,
        short_turnaround_home=True,
        short_turnaround_away=False,
        state_of_origin_round=True,
        origin_affected_home=3,
        origin_affected_away=2,
        venue_win_rate_home=0.75,
        venue_win_rate_away=0.45,
        rivalry_game=True,
        finals_match=False,
    )
    fv = feature_vector(fs)
    
    # All values should be floats
    assert all(isinstance(v, float) for v in fv)
    
    # Check specific NRL feature values
    assert fv[FEATURE_NAMES.index("travel_distance_km")] == 1234.5
    assert fv[FEATURE_NAMES.index("short_turnaround_home")] == 1.0
    assert fv[FEATURE_NAMES.index("short_turnaround_away")] == 0.0
    assert fv[FEATURE_NAMES.index("state_of_origin_round")] == 1.0
    assert fv[FEATURE_NAMES.index("origin_affected_home")] == 3.0
    assert fv[FEATURE_NAMES.index("origin_affected_away")] == 2.0
    assert fv[FEATURE_NAMES.index("venue_win_rate_home")] == 0.75
    assert fv[FEATURE_NAMES.index("venue_win_rate_away")] == 0.45
    assert fv[FEATURE_NAMES.index("rivalry_game")] == 1.0
    assert fv[FEATURE_NAMES.index("finals_match")] == 0.0


def test_feature_vector_length_includes_all_nrl_features() -> None:
    """Feature vector length accounts for all NRL-specific features."""
    fs = FeatureSet()
    fv = feature_vector(fs)
    # Should have 9 existing + 10 NRL + 4 weather + 4 injury = 27 features
    assert len(fv) == 27
    assert len(FEATURE_NAMES) == 27


# ---------------------------------------------------------------------------
# validate_features tests (task 8.2)
# ---------------------------------------------------------------------------

from scripts.lib.features import ValidationResult, validate_features


def _complete_features() -> FeatureSet:
    """Return a FeatureSet with non-default weather and injury data."""
    return FeatureSet(
        temperature_c=25.0,
        precipitation_mm=3.0,
        wind_speed_kmh=20.0,
        injury_impact_home=0.5,
        injury_impact_away=0.3,
    )


def _default_weather_features() -> FeatureSet:
    """Return a FeatureSet where weather fields are all at defaults."""
    return FeatureSet(
        temperature_c=20.0,
        precipitation_mm=0.0,
        wind_speed_kmh=10.0,
        injury_impact_home=0.5,
        injury_impact_away=0.3,
    )


def _default_injury_features() -> FeatureSet:
    """Return a FeatureSet where injury fields are both 0.0 (defaults)."""
    return FeatureSet(
        temperature_c=25.0,
        precipitation_mm=3.0,
        wind_speed_kmh=20.0,
        injury_impact_home=0.0,
        injury_impact_away=0.0,
    )


# --- Return type ---

def test_validate_features_returns_validation_result() -> None:
    """validate_features returns a ValidationResult instance."""
    result = validate_features(FeatureSet())
    assert isinstance(result, ValidationResult)


def test_validation_result_has_required_fields() -> None:
    """ValidationResult has is_complete, missing_fields, and warnings."""
    result = validate_features(FeatureSet())
    assert hasattr(result, "is_complete")
    assert hasattr(result, "missing_fields")
    assert hasattr(result, "warnings")


# --- Complete features ---

def test_complete_features_is_complete_true() -> None:
    """is_complete is True when weather and injury data are non-default."""
    result = validate_features(_complete_features())
    assert result.is_complete is True


def test_complete_features_no_missing_fields() -> None:
    """missing_fields is empty when all data is present."""
    result = validate_features(_complete_features())
    assert result.missing_fields == []


def test_complete_features_no_warnings() -> None:
    """warnings list is empty when all data is present."""
    result = validate_features(_complete_features())
    assert result.warnings == []


# --- Missing weather ---

def test_missing_weather_is_complete_false() -> None:
    """is_complete is False when weather fields are all at defaults."""
    result = validate_features(_default_weather_features())
    assert result.is_complete is False


def test_missing_weather_in_missing_fields() -> None:
    """'weather' appears in missing_fields when weather is at defaults."""
    result = validate_features(_default_weather_features())
    assert "weather" in result.missing_fields


def test_missing_weather_has_warning() -> None:
    """A warning is emitted when weather data is missing."""
    result = validate_features(_default_weather_features())
    assert len(result.warnings) >= 1
    assert any("weather" in w.lower() for w in result.warnings)


def test_partial_weather_not_flagged_as_missing() -> None:
    """Only all-default weather triggers the missing flag; partial non-defaults are OK."""
    # temperature differs from default — weather is considered present
    fs = FeatureSet(temperature_c=22.0, precipitation_mm=0.0, wind_speed_kmh=10.0,
                    injury_impact_home=0.5, injury_impact_away=0.3)
    result = validate_features(fs)
    assert "weather" not in result.missing_fields


def test_partial_weather_precipitation_differs() -> None:
    """Non-default precipitation means weather is not flagged as missing."""
    fs = FeatureSet(temperature_c=20.0, precipitation_mm=1.0, wind_speed_kmh=10.0,
                    injury_impact_home=0.5, injury_impact_away=0.3)
    result = validate_features(fs)
    assert "weather" not in result.missing_fields


def test_partial_weather_wind_differs() -> None:
    """Non-default wind speed means weather is not flagged as missing."""
    fs = FeatureSet(temperature_c=20.0, precipitation_mm=0.0, wind_speed_kmh=15.0,
                    injury_impact_home=0.5, injury_impact_away=0.3)
    result = validate_features(fs)
    assert "weather" not in result.missing_fields


# --- Missing injury ---

def test_missing_injury_is_complete_false() -> None:
    """is_complete is False when both injury fields are 0.0."""
    result = validate_features(_default_injury_features())
    assert result.is_complete is False


def test_missing_injury_in_missing_fields() -> None:
    """'injury' appears in missing_fields when both impact scores are 0.0."""
    result = validate_features(_default_injury_features())
    assert "injury" in result.missing_fields


def test_missing_injury_has_warning() -> None:
    """A warning is emitted when injury data is missing."""
    result = validate_features(_default_injury_features())
    assert len(result.warnings) >= 1
    assert any("injury" in w.lower() for w in result.warnings)


def test_nonzero_home_injury_not_flagged() -> None:
    """Non-zero injury_impact_home means injury is not flagged as missing."""
    fs = FeatureSet(
        temperature_c=25.0, precipitation_mm=3.0, wind_speed_kmh=20.0,
        injury_impact_home=0.1, injury_impact_away=0.0,
    )
    result = validate_features(fs)
    assert "injury" not in result.missing_fields


def test_nonzero_away_injury_not_flagged() -> None:
    """Non-zero injury_impact_away means injury is not flagged as missing."""
    fs = FeatureSet(
        temperature_c=25.0, precipitation_mm=3.0, wind_speed_kmh=20.0,
        injury_impact_home=0.0, injury_impact_away=0.2,
    )
    result = validate_features(fs)
    assert "injury" not in result.missing_fields


# --- Both missing ---

def test_both_missing_is_complete_false() -> None:
    """is_complete is False when both weather and injury are at defaults."""
    result = validate_features(FeatureSet())
    assert result.is_complete is False


def test_both_missing_fields_listed() -> None:
    """Both 'weather' and 'injury' appear in missing_fields for a default FeatureSet."""
    result = validate_features(FeatureSet())
    assert "weather" in result.missing_fields
    assert "injury" in result.missing_fields


def test_both_missing_two_warnings() -> None:
    """Two warnings are emitted when both weather and injury are missing."""
    result = validate_features(FeatureSet())
    assert len(result.warnings) == 2


# --- Context parameters ---

def test_context_game_id_included_in_warning() -> None:
    """game_id appears in warning messages when provided."""
    result = validate_features(FeatureSet(), game_id="game-42")
    assert any("game-42" in w for w in result.warnings)


def test_context_teams_included_in_warning() -> None:
    """Team names appear in warning messages when provided."""
    result = validate_features(
        FeatureSet(), home_team="Panthers", away_team="Storm"
    )
    assert any("Panthers" in w and "Storm" in w for w in result.warnings)


def test_context_no_context_still_works() -> None:
    """validate_features works correctly with no context arguments."""
    result = validate_features(FeatureSet())
    assert isinstance(result, ValidationResult)
    assert len(result.warnings) == 2


def test_context_partial_context_game_id_only() -> None:
    """validate_features works with only game_id provided."""
    result = validate_features(FeatureSet(), game_id="g-99")
    assert any("g-99" in w for w in result.warnings)


# --- Logging (integration check) ---

def test_validate_features_emits_warnings_to_logger(caplog) -> None:
    """validate_features emits WARNING-level log records for missing data."""
    import logging
    with caplog.at_level(logging.WARNING, logger="scripts.lib.features"):
        validate_features(FeatureSet())
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 2


def test_validate_features_no_log_when_complete(caplog) -> None:
    """No WARNING log records are emitted when features are complete."""
    import logging
    with caplog.at_level(logging.WARNING, logger="scripts.lib.features"):
        validate_features(_complete_features())
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 0


# ---------------------------------------------------------------------------
# extract_features() integration tests for task 8.1
# Tests for weather_data and injury_data parameters, NRL-specific features,
# short_turnaround, finals_match, and backward compatibility.
# ---------------------------------------------------------------------------

from scripts.lib.features import _parse_season_round
from scripts.lib.injury_tracker import InjuryStatus, PlayerImpact
from scripts.lib.weather_api import WeatherData


def _make_canonical_fixture(**overrides) -> Fixture:
    """Fixture with a canonical game_id for season/round parsing."""
    defaults = dict(
        game_id="2026-r01-g01",
        nrl_match_id=None,
        nrl_slug=None,
        home_team="Broncos",
        away_team="Storm",
        venue="Suncorp Stadium",
        kickoff_at="2026-03-07T09:50:00Z",
        status="upcoming",
    )
    defaults.update(overrides)
    return Fixture(**defaults)


def _make_weather(
    temperature_c: float = 25.0,
    precipitation_mm: float = 8.0,
    wind_speed_kmh: float = 30.0,
) -> WeatherData:
    return WeatherData(
        venue="Suncorp Stadium",
        timestamp="2026-03-07T09:50:00Z",
        temperature_c=temperature_c,
        precipitation_mm=precipitation_mm,
        wind_speed_kmh=wind_speed_kmh,
        conditions="rain",
        source="open-meteo",
    )


def _make_injury_data(
    team: str,
    total_impact: float = 0.85,
    key_player_out: bool = True,
) -> dict[str, InjuryStatus]:
    player = PlayerImpact(
        player_name="Test Player",
        position="Halfback",
        impact_score=total_impact,
        status="injured",
    )
    return {
        team: InjuryStatus(
            team=team,
            fixture_date="2026-03-07",
            unavailable_players=(player,),
            total_impact=total_impact,
            key_player_out=key_player_out,
        )
    }


# --- Backward compatibility: old 4-arg call still works ---

def test_extract_features_backward_compatible_no_weather_no_injury() -> None:
    """extract_features() with only 4 args still works (backward compat)."""
    engine = EloEngine()
    fixture = _make_canonical_fixture()
    features = extract_features(fixture, engine, [], {})
    assert isinstance(features, FeatureSet)
    # Weather defaults
    assert features.temperature_c == 20.0
    assert features.precipitation_mm == 0.0
    assert features.wind_speed_kmh == 10.0
    assert features.wet_weather is False
    # Injury defaults
    assert features.injury_impact_home == 0.0
    assert features.injury_impact_away == 0.0
    assert features.key_player_out_home is False
    assert features.key_player_out_away is False


# --- Weather data integration ---

def test_extract_features_uses_weather_data_when_provided() -> None:
    """Weather fields are populated from WeatherData when provided."""
    engine = EloEngine()
    fixture = _make_canonical_fixture()
    weather = _make_weather(temperature_c=28.5, precipitation_mm=12.0, wind_speed_kmh=35.0)
    features = extract_features(fixture, engine, [], {}, weather_data=weather)

    assert features.temperature_c == 28.5
    assert features.precipitation_mm == 12.0
    assert features.wind_speed_kmh == 35.0
    assert features.wet_weather is True  # 12.0 > 5.0


def test_extract_features_wet_weather_false_below_threshold() -> None:
    """wet_weather is False when precipitation <= 5mm."""
    engine = EloEngine()
    fixture = _make_canonical_fixture()
    weather = _make_weather(precipitation_mm=4.9)
    features = extract_features(fixture, engine, [], {}, weather_data=weather)
    assert features.wet_weather is False


def test_extract_features_wet_weather_true_above_threshold() -> None:
    """wet_weather is True when precipitation > 5mm."""
    engine = EloEngine()
    fixture = _make_canonical_fixture()
    weather = _make_weather(precipitation_mm=5.1)
    features = extract_features(fixture, engine, [], {}, weather_data=weather)
    assert features.wet_weather is True


def test_extract_features_weather_none_uses_defaults() -> None:
    """Passing weather_data=None uses FeatureSet default weather values."""
    engine = EloEngine()
    fixture = _make_canonical_fixture()
    features = extract_features(fixture, engine, [], {}, weather_data=None)
    assert features.temperature_c == 20.0
    assert features.precipitation_mm == 0.0
    assert features.wind_speed_kmh == 10.0
    assert features.wet_weather is False


# --- Injury data integration ---

def test_extract_features_uses_home_injury_data() -> None:
    """Home team injury fields are populated from injury_data."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(home_team="Broncos", away_team="Storm")
    injury_data = _make_injury_data("Broncos", total_impact=0.85, key_player_out=True)
    features = extract_features(fixture, engine, [], {}, injury_data=injury_data)

    assert features.injury_impact_home == pytest.approx(0.85)
    assert features.key_player_out_home is True
    # Away team has no injury data
    assert features.injury_impact_away == 0.0
    assert features.key_player_out_away is False


def test_extract_features_uses_away_injury_data() -> None:
    """Away team injury fields are populated from injury_data."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(home_team="Broncos", away_team="Storm")
    injury_data = _make_injury_data("Storm", total_impact=0.5, key_player_out=False)
    features = extract_features(fixture, engine, [], {}, injury_data=injury_data)

    assert features.injury_impact_away == pytest.approx(0.5)
    assert features.key_player_out_away is False
    # Home team has no injury data
    assert features.injury_impact_home == 0.0
    assert features.key_player_out_home is False


def test_extract_features_injury_none_uses_zero_adjustments() -> None:
    """Passing injury_data=None uses zero injury adjustments."""
    engine = EloEngine()
    fixture = _make_canonical_fixture()
    features = extract_features(fixture, engine, [], {}, injury_data=None)
    assert features.injury_impact_home == 0.0
    assert features.injury_impact_away == 0.0
    assert features.key_player_out_home is False
    assert features.key_player_out_away is False


def test_extract_features_injury_team_not_in_data_uses_zero() -> None:
    """Teams absent from injury_data get zero adjustments."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(home_team="Broncos", away_team="Storm")
    # Only Raiders in injury data — neither team in fixture
    injury_data = _make_injury_data("Raiders", total_impact=0.9)
    features = extract_features(fixture, engine, [], {}, injury_data=injury_data)
    assert features.injury_impact_home == 0.0
    assert features.injury_impact_away == 0.0


# --- Short turnaround ---

def test_extract_features_short_turnaround_detected() -> None:
    """short_turnaround is True when rest days < 6."""
    engine = EloEngine()
    # Fixture on 2026-03-07; last game on 2026-03-04 → 3 days rest
    history = [
        MatchResult(
            season=2026, round_number=1, game_id="prev",
            home_team="Broncos", away_team="Raiders",
            venue="Suncorp Stadium",
            home_score=20, away_score=10, winner="Broncos",
            margin=10, kickoff_at="2026-03-04T09:00:00Z",
        )
    ]
    fixture = _make_canonical_fixture(
        home_team="Broncos", away_team="Storm",
        kickoff_at="2026-03-07T09:50:00Z",
    )
    features = extract_features(fixture, engine, history, {})
    assert features.short_turnaround_home is True
    assert features.rest_days_home == 3


def test_extract_features_no_short_turnaround_with_full_rest() -> None:
    """short_turnaround is False when rest days >= 6."""
    engine = EloEngine()
    history = [
        MatchResult(
            season=2026, round_number=1, game_id="prev",
            home_team="Broncos", away_team="Raiders",
            venue="Suncorp Stadium",
            home_score=20, away_score=10, winner="Broncos",
            margin=10, kickoff_at="2026-02-28T09:00:00Z",
        )
    ]
    fixture = _make_canonical_fixture(
        home_team="Broncos", away_team="Storm",
        kickoff_at="2026-03-07T09:50:00Z",
    )
    features = extract_features(fixture, engine, history, {})
    assert features.short_turnaround_home is False
    assert features.rest_days_home == 7


# --- Finals match ---

def test_extract_features_finals_match_round_28() -> None:
    """finals_match is True for round 28 (first finals round)."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(game_id="2026-r28-g01")
    features = extract_features(fixture, engine, [], {})
    assert features.finals_match is True


def test_extract_features_finals_match_round_27_is_false() -> None:
    """finals_match is False for round 27 (last regular season round)."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(game_id="2026-r27-g01")
    features = extract_features(fixture, engine, [], {})
    assert features.finals_match is False


def test_extract_features_finals_match_round_1_is_false() -> None:
    """finals_match is False for round 1."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(game_id="2026-r01-g01")
    features = extract_features(fixture, engine, [], {})
    assert features.finals_match is False


# --- State of Origin ---

def test_extract_features_state_of_origin_round_13() -> None:
    """state_of_origin_round is True for round 13 in 2026."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(game_id="2026-r13-g01")
    features = extract_features(fixture, engine, [], {})
    assert features.state_of_origin_round is True


def test_extract_features_state_of_origin_round_1_is_false() -> None:
    """state_of_origin_round is False for round 1."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(game_id="2026-r01-g01")
    features = extract_features(fixture, engine, [], {})
    assert features.state_of_origin_round is False


# --- Travel distance ---

def test_extract_features_travel_distance_populated() -> None:
    """travel_distance_km is computed for the away team."""
    engine = EloEngine()
    # Storm (Melbourne) traveling to Suncorp (Brisbane) ~1370km
    fixture = _make_canonical_fixture(
        home_team="Broncos", away_team="Storm", venue="Suncorp Stadium"
    )
    features = extract_features(fixture, engine, [], {})
    assert features.travel_distance_km > 1000.0


def test_extract_features_travel_distance_zero_for_home_venue() -> None:
    """travel_distance_km is 0.0 when away team plays at their own home venue."""
    engine = EloEngine()
    # Broncos playing at Suncorp (their home venue) as "away" team
    fixture = _make_canonical_fixture(
        home_team="Storm", away_team="Broncos", venue="Suncorp Stadium"
    )
    features = extract_features(fixture, engine, [], {})
    assert features.travel_distance_km == 0.0


# --- Rivalry game ---

def test_extract_features_rivalry_game_detected() -> None:
    """rivalry_game is True for known rivalry matchups."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(home_team="Roosters", away_team="Rabbitohs")
    features = extract_features(fixture, engine, [], {})
    assert features.rivalry_game is True


def test_extract_features_rivalry_game_false_for_non_rivals() -> None:
    """rivalry_game is False for non-rivalry matchups."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(home_team="Panthers", away_team="Warriors")
    features = extract_features(fixture, engine, [], {})
    assert features.rivalry_game is False


# --- _parse_season_round helper ---

def test_parse_season_round_canonical_format() -> None:
    """Parses season and round from canonical game_id format."""
    assert _parse_season_round("2026-r01-g01") == (2026, 1)
    assert _parse_season_round("2026-r13-g05") == (2026, 13)
    assert _parse_season_round("2025-r28-g02") == (2025, 28)


def test_parse_season_round_unknown_format_returns_none() -> None:
    """Returns (None, None) for unrecognised game_id formats."""
    assert _parse_season_round("test-g01") == (None, None)
    assert _parse_season_round("") == (None, None)
    assert _parse_season_round("abc") == (None, None)


def test_extract_features_unknown_game_id_no_crash() -> None:
    """extract_features handles unrecognised game_id gracefully (no crash)."""
    engine = EloEngine()
    fixture = _make_canonical_fixture(game_id="test-g01")
    features = extract_features(fixture, engine, [], {})
    assert isinstance(features, FeatureSet)
    # With unknown game_id, finals_match and state_of_origin_round default to False
    assert features.finals_match is False
    assert features.state_of_origin_round is False
