"""Property-based tests for NRL-specific feature extraction invariants.

Uses Hypothesis to verify universal properties hold across arbitrary inputs:
- Travel distance is always non-negative (Req 1.2, 17.5)
- Venue win rate is always bounded in [0.0, 1.0] (Req 1.5, 17.5)
- State of Origin round detection is consistent (Req 1.3, 17.5)
- Rivalry detection is symmetric (Req 1.6, 17.5)

**Validates: Requirements 1.2, 1.3, 1.5, 1.6, 17.1, 17.5**
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from scripts.lib.features import (
    RIVALRY_PAIRS,
    TEAM_HOME_VENUES,
    compute_travel_distance,
    compute_venue_specific_win_rate,
    identify_state_of_origin_rounds,
    is_rivalry_game,
    is_state_of_origin_round,
)
from scripts.lib.historical_data import MatchResult
from scripts.lib.weather_api import VENUE_COORDINATES

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# All known NRL team names
_ALL_TEAMS = list(TEAM_HOME_VENUES.keys())

# All known NRL venue names
_ALL_VENUES = list(VENUE_COORDINATES.keys())

# Strategy for a valid NRL team name
nrl_team = st.sampled_from(_ALL_TEAMS)

# Strategy for a valid NRL venue name
nrl_venue = st.sampled_from(_ALL_VENUES)

# Strategy for any string (including unknown teams/venues)
any_team_name = st.text(min_size=1, max_size=50)
any_venue_name = st.text(min_size=1, max_size=80)

# Strategy for a season year (known + unknown)
season_year = st.integers(min_value=2000, max_value=2050)

# Strategy for a round number
round_number = st.integers(min_value=1, max_value=30)

# Strategy for a single MatchResult
def _match_result_strategy(
    team_a: str,
    team_b: str,
    venue: str,
    round_num: int,
    game_id: str,
) -> st.SearchStrategy[MatchResult]:
    """Build a MatchResult strategy for two teams at a venue."""
    winner = st.sampled_from([team_a, team_b])
    home_score = st.integers(min_value=0, max_value=80)
    away_score = st.integers(min_value=0, max_value=80)
    return st.builds(
        MatchResult,
        season=st.just(2025),
        round_number=st.just(round_num),
        game_id=st.just(game_id),
        home_team=st.just(team_a),
        away_team=st.just(team_b),
        venue=st.just(venue),
        home_score=home_score,
        away_score=away_score,
        winner=winner,
        margin=st.integers(min_value=0, max_value=80),
        kickoff_at=st.just("2025-03-01T09:00:00Z"),
    )


# ---------------------------------------------------------------------------
# Property 1: Travel distance is always non-negative
# Validates: Requirements 1.2, 17.5
# ---------------------------------------------------------------------------

@given(away_team=any_team_name, venue=any_venue_name)
@settings(max_examples=200)
def test_travel_distance_is_non_negative_for_any_input(
    away_team: str, venue: str
) -> None:
    """Travel distance must be >= 0 for any team/venue combination.

    **Validates: Requirements 1.2, 17.5**
    """
    distance = compute_travel_distance(away_team, venue)
    assert distance >= 0.0, (
        f"Travel distance must be non-negative, got {distance} "
        f"for team={away_team!r}, venue={venue!r}"
    )


@given(away_team=nrl_team, venue=nrl_venue)
@settings(max_examples=100)
def test_travel_distance_is_non_negative_for_known_teams(
    away_team: str, venue: str
) -> None:
    """Travel distance is non-negative for all known NRL team/venue pairs.

    **Validates: Requirements 1.2, 17.5**
    """
    distance = compute_travel_distance(away_team, venue)
    assert distance >= 0.0


@given(away_team=nrl_team, venue=nrl_venue)
@settings(max_examples=100)
def test_travel_distance_is_finite_for_known_teams(
    away_team: str, venue: str
) -> None:
    """Travel distance is a finite float for all known NRL team/venue pairs.

    **Validates: Requirements 1.2, 17.5**
    """
    import math
    distance = compute_travel_distance(away_team, venue)
    assert math.isfinite(distance), (
        f"Travel distance must be finite, got {distance} "
        f"for team={away_team!r}, venue={venue!r}"
    )


@given(away_team=nrl_team)
@settings(max_examples=17)
def test_travel_distance_to_home_venue_is_zero(away_team: str) -> None:
    """A team playing at their own home venue has zero travel distance.

    **Validates: Requirements 1.2, 17.5**
    """
    home_venue = TEAM_HOME_VENUES[away_team]
    distance = compute_travel_distance(away_team, home_venue)
    assert distance == 0.0, (
        f"{away_team} should have 0 travel to their home venue "
        f"{home_venue!r}, got {distance}"
    )


@given(away_team=nrl_team, venue=nrl_venue)
@settings(max_examples=100)
def test_travel_distance_bounded_by_earth_circumference(
    away_team: str, venue: str
) -> None:
    """Travel distance cannot exceed half the Earth's circumference (~20,015 km).

    **Validates: Requirements 1.2, 17.5**
    """
    distance = compute_travel_distance(away_team, venue)
    assert distance <= 20_015.0, (
        f"Travel distance {distance} km exceeds Earth's half-circumference "
        f"for team={away_team!r}, venue={venue!r}"
    )


# ---------------------------------------------------------------------------
# Property 2: Venue win rate is always bounded in [0.0, 1.0]
# Validates: Requirements 1.5, 17.5
# ---------------------------------------------------------------------------

@given(
    team=nrl_team,
    venue=nrl_venue,
    n_games=st.integers(min_value=0, max_value=20),
    min_games=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=200)
def test_venue_win_rate_bounded_between_zero_and_one(
    team: str, venue: str, n_games: int, min_games: int
) -> None:
    """Venue win rate is always in [0.0, 1.0] regardless of history size.

    **Validates: Requirements 1.5, 17.5**
    """
    # Use a fixed opponent that is never the same as `team`
    opponent = "Storm" if team != "Storm" else "Broncos"
    # Build a history of n_games at the venue, alternating wins/losses
    history = [
        MatchResult(
            season=2025,
            round_number=i + 1,
            game_id=f"g{i}",
            home_team=team,
            away_team=opponent,
            venue=venue,
            home_score=20,
            away_score=10,
            winner=team if i % 2 == 0 else opponent,
            margin=10,
            kickoff_at="2025-03-01T09:00:00Z",
        )
        for i in range(n_games)
    ]
    rate = compute_venue_specific_win_rate(team, venue, history, min_games=min_games)
    assert 0.0 <= rate <= 1.0, (
        f"Venue win rate {rate} is out of [0, 1] bounds for "
        f"team={team!r}, venue={venue!r}, n_games={n_games}, min_games={min_games}"
    )


@given(
    team=nrl_team,
    venue=nrl_venue,
    n_wins=st.integers(min_value=0, max_value=20),
    n_losses=st.integers(min_value=0, max_value=20),
    min_games=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=200)
def test_venue_win_rate_bounded_with_mixed_results(
    team: str, venue: str, n_wins: int, n_losses: int, min_games: int
) -> None:
    """Venue win rate is bounded [0, 1] with arbitrary win/loss combinations.

    **Validates: Requirements 1.5, 17.5**
    """
    # Use a fixed opponent that is never the same as `team`
    opponent = "Storm" if team != "Storm" else "Broncos"
    wins = [
        MatchResult(
            season=2025, round_number=i + 1, game_id=f"w{i}",
            home_team=team, away_team=opponent, venue=venue,
            home_score=20, away_score=10, winner=team,
            margin=10, kickoff_at="2025-03-01T09:00:00Z",
        )
        for i in range(n_wins)
    ]
    losses = [
        MatchResult(
            season=2025, round_number=n_wins + i + 1, game_id=f"l{i}",
            home_team=team, away_team=opponent, venue=venue,
            home_score=10, away_score=20, winner=opponent,
            margin=10, kickoff_at="2025-03-01T09:00:00Z",
        )
        for i in range(n_losses)
    ]
    history = wins + losses
    rate = compute_venue_specific_win_rate(team, venue, history, min_games=min_games)
    assert 0.0 <= rate <= 1.0


@given(
    team=nrl_team,
    venue=nrl_venue,
    min_games=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=50)
def test_venue_win_rate_returns_neutral_when_no_history(
    team: str, venue: str, min_games: int
) -> None:
    """Venue win rate returns 0.5 (neutral) when no history exists.

    **Validates: Requirements 1.5, 17.5**
    """
    rate = compute_venue_specific_win_rate(team, venue, [], min_games=min_games)
    assert rate == 0.5


@given(
    team=nrl_team,
    venue=nrl_venue,
    n_games=st.integers(min_value=5, max_value=20),
)
@settings(max_examples=100)
def test_venue_win_rate_all_wins_returns_one(
    team: str, venue: str, n_games: int
) -> None:
    """Venue win rate is 1.0 when the team has won every game at the venue.

    **Validates: Requirements 1.5, 17.5**
    """
    # Use a fixed opponent that is never the same as `team`
    opponent = "Storm" if team != "Storm" else "Broncos"
    history = [
        MatchResult(
            season=2025, round_number=i + 1, game_id=f"g{i}",
            home_team=team, away_team=opponent, venue=venue,
            home_score=20, away_score=10, winner=team,
            margin=10, kickoff_at="2025-03-01T09:00:00Z",
        )
        for i in range(n_games)
    ]
    rate = compute_venue_specific_win_rate(team, venue, history, min_games=5)
    assert rate == 1.0


@given(
    team=nrl_team,
    venue=nrl_venue,
    n_games=st.integers(min_value=5, max_value=20),
)
@settings(max_examples=100)
def test_venue_win_rate_all_losses_returns_zero(
    team: str, venue: str, n_games: int
) -> None:
    """Venue win rate is 0.0 when the team has lost every game at the venue.

    **Validates: Requirements 1.5, 17.5**
    """
    # Use a fixed opponent that is never the same as `team`
    opponent = "Storm" if team != "Storm" else "Broncos"
    history = [
        MatchResult(
            season=2025, round_number=i + 1, game_id=f"g{i}",
            home_team=team, away_team=opponent, venue=venue,
            home_score=10, away_score=20, winner=opponent,
            margin=10, kickoff_at="2025-03-01T09:00:00Z",
        )
        for i in range(n_games)
    ]
    rate = compute_venue_specific_win_rate(team, venue, history, min_games=5)
    assert rate == 0.0


# ---------------------------------------------------------------------------
# Property 3: State of Origin round detection is consistent
# Validates: Requirements 1.3, 17.5
# ---------------------------------------------------------------------------

@given(season=season_year, round_num=round_number)
@settings(max_examples=200)
def test_state_of_origin_round_consistent_with_identify(
    season: int, round_num: int
) -> None:
    """is_state_of_origin_round is consistent with identify_state_of_origin_rounds.

    **Validates: Requirements 1.3, 17.5**
    """
    rounds_set = identify_state_of_origin_rounds(season)
    expected = round_num in rounds_set
    actual = is_state_of_origin_round(season, round_num)
    assert actual == expected, (
        f"is_state_of_origin_round({season}, {round_num}) = {actual} "
        f"but round_num {'in' if expected else 'not in'} "
        f"identify_state_of_origin_rounds({season}) = {rounds_set}"
    )


@given(season=season_year)
@settings(max_examples=100)
def test_state_of_origin_rounds_returns_non_empty_set(season: int) -> None:
    """identify_state_of_origin_rounds always returns a non-empty set.

    **Validates: Requirements 1.3, 17.5**
    """
    rounds = identify_state_of_origin_rounds(season)
    assert isinstance(rounds, set)
    assert len(rounds) > 0, f"Expected non-empty set for season {season}"


@given(season=season_year)
@settings(max_examples=100)
def test_state_of_origin_rounds_are_valid_round_numbers(season: int) -> None:
    """All State of Origin rounds are valid NRL round numbers (1-27).

    **Validates: Requirements 1.3, 17.5**
    """
    rounds = identify_state_of_origin_rounds(season)
    for r in rounds:
        assert isinstance(r, int)
        assert 1 <= r <= 27, (
            f"State of Origin round {r} is outside valid range [1, 27] "
            f"for season {season}"
        )


@given(season=season_year)
@settings(max_examples=100)
def test_state_of_origin_rounds_returns_copy(season: int) -> None:
    """identify_state_of_origin_rounds returns an independent copy each call.

    Mutating the returned set must not affect subsequent calls.

    **Validates: Requirements 1.3, 17.5**
    """
    rounds1 = identify_state_of_origin_rounds(season)
    rounds1.add(99)  # mutate the returned set
    rounds2 = identify_state_of_origin_rounds(season)
    assert 99 not in rounds2, (
        "identify_state_of_origin_rounds returned a mutable reference "
        "to internal state — it should return a copy"
    )


# ---------------------------------------------------------------------------
# Property 4: Rivalry detection is symmetric
# Validates: Requirements 1.6, 17.5
# ---------------------------------------------------------------------------

@given(team_a=any_team_name, team_b=any_team_name)
@settings(max_examples=300)
def test_rivalry_detection_is_symmetric(team_a: str, team_b: str) -> None:
    """is_rivalry_game(a, b) == is_rivalry_game(b, a) for any team names.

    **Validates: Requirements 1.6, 17.5**
    """
    assert is_rivalry_game(team_a, team_b) == is_rivalry_game(team_b, team_a), (
        f"Rivalry detection is not symmetric: "
        f"is_rivalry_game({team_a!r}, {team_b!r}) != "
        f"is_rivalry_game({team_b!r}, {team_a!r})"
    )


@given(team=any_team_name)
@settings(max_examples=100)
def test_rivalry_detection_no_self_rivalry(team: str) -> None:
    """A team is never a rival of itself.

    **Validates: Requirements 1.6, 17.5**
    """
    assert is_rivalry_game(team, team) is False, (
        f"is_rivalry_game({team!r}, {team!r}) should be False — "
        "a team cannot be its own rival"
    )


@given(team_a=nrl_team, team_b=nrl_team)
@settings(max_examples=100)
def test_rivalry_detection_returns_bool(team_a: str, team_b: str) -> None:
    """is_rivalry_game always returns a bool.

    **Validates: Requirements 1.6, 17.5**
    """
    result = is_rivalry_game(team_a, team_b)
    assert isinstance(result, bool), (
        f"is_rivalry_game({team_a!r}, {team_b!r}) returned {type(result).__name__}, "
        "expected bool"
    )


@given(team_a=any_team_name, team_b=any_team_name)
@settings(max_examples=200)
def test_rivalry_detection_returns_bool_for_any_input(
    team_a: str, team_b: str
) -> None:
    """is_rivalry_game returns a bool for any string inputs (no exceptions).

    **Validates: Requirements 1.6, 17.5**
    """
    result = is_rivalry_game(team_a, team_b)
    assert isinstance(result, bool)
