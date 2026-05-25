"""Feature extraction engine for NRL match prediction.

Computes a rich feature set for each fixture by combining ELO ratings,
recent form, ladder position, rest days, head-to-head record, scoring /
defensive trends, NRL-specific contextual factors (travel distance, State
of Origin, venue win rates, rivalry, finals), weather conditions, and
injury/suspension impacts.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .elo_ratings import EloEngine
from .historical_data import MatchResult
from .injury_tracker import InjuryStatus
from .types import Fixture
from .weather_api import VENUE_COORDINATES, WeatherData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature set dataclass
# ---------------------------------------------------------------------------

@dataclass
class FeatureSet:
    """All computed features for a single fixture."""

    # ELO-derived
    elo_diff: float = 0.0        # home ELO - away ELO (including HGA)
    elo_home: float = 1500.0
    elo_away: float = 1500.0
    home_advantage: float = 1.0  # 1.0 for home, 0.0 for neutral

    # Recent form (win ratio over last N games)
    form_home_5: float = 0.5
    form_away_5: float = 0.5

    # Points differential per game (from ladder or computed)
    pd_per_game_home: float = 0.0
    pd_per_game_away: float = 0.0

    # Ladder position differential (home - away; negative = home higher)
    ladder_pos_diff: int = 0

    # Rest days since last game (capped at 14)
    rest_days_home: int = 7
    rest_days_away: int = 7

    # Head-to-head: home team wins in last N meetings
    h2h_home_wins_recent: int = 0

    # Scoring trends (average points scored/conceded in last 5)
    scoring_trend_home: float = 20.0
    scoring_trend_away: float = 20.0
    defensive_trend_home: float = 20.0
    defensive_trend_away: float = 20.0

    # NRL-specific contextual features
    travel_distance_km: float = 0.0       # away team travel distance in km
    short_turnaround_home: bool = False    # home team has < 6 days rest
    short_turnaround_away: bool = False    # away team has < 6 days rest
    state_of_origin_round: bool = False    # round is affected by State of Origin
    origin_affected_home: int = 0          # count of missing rep players (home)
    origin_affected_away: int = 0          # count of missing rep players (away)
    venue_win_rate_home: float = 0.5       # home team's win rate at this venue
    venue_win_rate_away: float = 0.5       # away team's win rate at this venue
    rivalry_game: bool = False             # traditional rivalry matchup
    finals_match: bool = False             # finals series fixture

    # Weather features
    temperature_c: float = 20.0           # air temperature in Celsius
    precipitation_mm: float = 0.0         # rainfall in millimetres
    wind_speed_kmh: float = 10.0          # wind speed in km/h
    wet_weather: bool = False             # True when precipitation > 5 mm

    # Injury / suspension features
    injury_impact_home: float = 0.0       # total impact score of unavailable home players
    injury_impact_away: float = 0.0       # total impact score of unavailable away players
    key_player_out_home: bool = False      # True when a home player with impact > 0.7 is out
    key_player_out_away: bool = False      # True when an away player with impact > 0.7 is out


def feature_vector(fs: FeatureSet) -> list[float]:
    """Convert a :class:`FeatureSet` to a flat numeric vector."""
    return [
        # Existing features
        fs.elo_diff,
        fs.home_advantage,
        fs.form_home_5 - fs.form_away_5,
        fs.pd_per_game_home - fs.pd_per_game_away,
        float(fs.ladder_pos_diff),
        float(fs.rest_days_home - fs.rest_days_away),
        float(fs.h2h_home_wins_recent),
        fs.scoring_trend_home - fs.scoring_trend_away,
        fs.defensive_trend_away - fs.defensive_trend_home,  # positive = home defends better
        # NRL-specific contextual features
        fs.travel_distance_km,
        float(fs.short_turnaround_home),
        float(fs.short_turnaround_away),
        float(fs.state_of_origin_round),
        float(fs.origin_affected_home),
        float(fs.origin_affected_away),
        fs.venue_win_rate_home,
        fs.venue_win_rate_away,
        float(fs.rivalry_game),
        float(fs.finals_match),
        # Weather features
        fs.temperature_c,
        fs.precipitation_mm,
        fs.wind_speed_kmh,
        float(fs.wet_weather),
        # Injury / suspension features
        fs.injury_impact_home,
        fs.injury_impact_away,
        float(fs.key_player_out_home),
        float(fs.key_player_out_away),
    ]


# Feature names corresponding to feature_vector output order
FEATURE_NAMES: list[str] = [
    # Existing features
    "elo_diff",
    "home_advantage",
    "form_diff",
    "pd_per_game_diff",
    "ladder_pos_diff",
    "rest_days_diff",
    "h2h_advantage",
    "scoring_diff",
    "defensive_diff",
    # NRL-specific contextual features
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
    # Weather features
    "temperature_c",
    "precipitation_mm",
    "wind_speed_kmh",
    "wet_weather",
    # Injury / suspension features
    "injury_impact_home",
    "injury_impact_away",
    "key_player_out_home",
    "key_player_out_away",
]


# ---------------------------------------------------------------------------
# Feature validation
# ---------------------------------------------------------------------------

#: Default weather values used when no real weather data has been fetched.
#: All three fields at their defaults simultaneously indicates missing weather.
_DEFAULT_TEMPERATURE_C: float = 20.0
_DEFAULT_PRECIPITATION_MM: float = 0.0
_DEFAULT_WIND_SPEED_KMH: float = 10.0


@dataclass
class ValidationResult:
    """Result of validating a :class:`FeatureSet` for completeness.

    Attributes:
        is_complete: ``True`` when no required data is missing.
        missing_fields: Names of feature groups that are absent or at
            placeholder defaults (e.g. ``"weather"``, ``"injury"``).
        warnings: Human-readable warning messages suitable for logging.
    """

    is_complete: bool
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_features(
    features: FeatureSet,
    game_id: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
) -> ValidationResult:
    """Validate a :class:`FeatureSet` for completeness and flag missing data.

    Checks whether weather and injury data appear to be real values or
    placeholder defaults.  Emits ``logging.WARNING`` messages for each
    missing data group so that operators can identify gaps in the pipeline.

    Weather is considered missing when *all three* of ``temperature_c``,
    ``precipitation_mm``, and ``wind_speed_kmh`` are simultaneously at their
    default values (20.0 °C, 0.0 mm, 10.0 km/h), which indicates that no
    real weather fetch occurred.

    Injury data is considered missing when *both* ``injury_impact_home`` and
    ``injury_impact_away`` are 0.0, which is the default when no injury file
    was loaded.  (A genuine zero-impact state is indistinguishable from a
    missing-data state, so this is a conservative heuristic.)

    Args:
        features: The :class:`FeatureSet` to validate.
        game_id: Optional game identifier included in log messages for
            traceability.
        home_team: Optional home team name included in log messages.
        away_team: Optional away team name included in log messages.

    Returns:
        A :class:`ValidationResult` describing completeness and any warnings.
    """
    context_parts: list[str] = []
    if game_id is not None:
        context_parts.append(f"game_id={game_id!r}")
    if home_team is not None and away_team is not None:
        context_parts.append(f"{home_team} vs {away_team}")
    context = f" [{', '.join(context_parts)}]" if context_parts else ""

    missing_fields: list[str] = []
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Weather data check
    # ------------------------------------------------------------------
    weather_at_defaults = (
        features.temperature_c == _DEFAULT_TEMPERATURE_C
        and features.precipitation_mm == _DEFAULT_PRECIPITATION_MM
        and features.wind_speed_kmh == _DEFAULT_WIND_SPEED_KMH
    )
    if weather_at_defaults:
        missing_fields.append("weather")
        msg = (
            f"Missing weather data{context}: all weather fields are at default "
            f"values (temperature_c={_DEFAULT_TEMPERATURE_C}, "
            f"precipitation_mm={_DEFAULT_PRECIPITATION_MM}, "
            f"wind_speed_kmh={_DEFAULT_WIND_SPEED_KMH}). "
            "Predictions will use placeholder weather features."
        )
        warnings.append(msg)
        logger.warning(msg)

    # ------------------------------------------------------------------
    # Injury data check
    # ------------------------------------------------------------------
    injury_at_defaults = (
        features.injury_impact_home == 0.0
        and features.injury_impact_away == 0.0
    )
    if injury_at_defaults:
        missing_fields.append("injury")
        msg = (
            f"Missing injury data{context}: injury_impact_home and "
            "injury_impact_away are both 0.0. "
            "Predictions will use zero injury adjustment."
        )
        warnings.append(msg)
        logger.warning(msg)

    is_complete = len(missing_fields) == 0
    return ValidationResult(
        is_complete=is_complete,
        missing_fields=missing_fields,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# State of Origin detection
# ---------------------------------------------------------------------------

#: Mapping of NRL season year to the set of round numbers affected by
#: State of Origin.  Typically rounds 13, 15, and 17, but the exact
#: schedule varies year to year.
STATE_OF_ORIGIN_ROUNDS: dict[int, set[int]] = {
    2023: {13, 15, 17},
    2024: {13, 15, 17},
    2025: {13, 15, 17},
    2026: {13, 15, 17},
}

#: Default rounds used when a season is not found in STATE_OF_ORIGIN_ROUNDS.
_DEFAULT_ORIGIN_ROUNDS: set[int] = {13, 15, 17}


def identify_state_of_origin_rounds(season: int) -> set[int]:
    """Return the set of round numbers affected by State of Origin for *season*.

    Looks up the season in :data:`STATE_OF_ORIGIN_ROUNDS`.  If the season is
    not found, falls back to the default ``{13, 15, 17}`` and logs a warning.

    Args:
        season: The NRL season year (e.g. ``2026``).

    Returns:
        A set of round numbers (e.g. ``{13, 15, 17}``) during which State of
        Origin matches are played and NRL clubs lose representative players.
    """
    if season in STATE_OF_ORIGIN_ROUNDS:
        return set(STATE_OF_ORIGIN_ROUNDS[season])

    logger.warning(
        "State of Origin rounds not configured for season %d; "
        "falling back to default %s",
        season,
        _DEFAULT_ORIGIN_ROUNDS,
    )
    return set(_DEFAULT_ORIGIN_ROUNDS)


def is_state_of_origin_round(season: int, round_number: int) -> bool:
    """Return ``True`` if *round_number* is a State of Origin round in *season*.

    Args:
        season: The NRL season year (e.g. ``2026``).
        round_number: The round number to check (e.g. ``13``).

    Returns:
        ``True`` when the round falls during a State of Origin game week.
    """
    return round_number in identify_state_of_origin_rounds(season)


# ---------------------------------------------------------------------------
# Rivalry detection
# ---------------------------------------------------------------------------

#: Traditional NRL rivalry matchups (symmetric — order of teams doesn't matter).
#:
#: Each entry is a frozenset of exactly two team names so that the check is
#: order-independent (home vs away doesn't matter).
RIVALRY_PAIRS: set[frozenset[str]] = {
    frozenset({"Broncos", "Cowboys"}),       # QLD derby — State of Origin-adjacent
    frozenset({"Roosters", "Rabbitohs"}),    # Sydney derby — fierce cross-town rivalry
    frozenset({"Storm", "Broncos"}),          # Historical finals rivalry
    frozenset({"Panthers", "Eels"}),          # Western Sydney derby
    frozenset({"Sharks", "Dragons"}),         # St George Illawarra vs Cronulla
    frozenset({"Raiders", "Bulldogs"}),       # Historical rivalry
    frozenset({"Knights", "Cowboys"}),        # Regional QLD/NSW rivalry
    frozenset({"Broncos", "Rabbitohs"}),      # Historical finals rivalry
    frozenset({"Storm", "Raiders"}),          # Historical finals rivalry
    frozenset({"Sea Eagles", "Roosters"}),    # Northern Beaches vs Eastern Suburbs
    frozenset({"Tigers", "Bulldogs"}),        # Western Sydney rivalry
    frozenset({"Dragons", "Rabbitohs"}),      # South Sydney rivalry
}


def is_rivalry_game(home_team: str, away_team: str) -> bool:
    """Return ``True`` if the fixture is a traditional NRL rivalry.

    The check is symmetric — the order of *home_team* and *away_team*
    does not affect the result.

    Args:
        home_team: Name of the home team (e.g. ``"Broncos"``).
        away_team: Name of the away team (e.g. ``"Cowboys"``).

    Returns:
        ``True`` when the pair appears in :data:`RIVALRY_PAIRS`.
    """
    return frozenset({home_team, away_team}) in RIVALRY_PAIRS


# ---------------------------------------------------------------------------
# Travel distance: team home venue mapping + Haversine calculation
# ---------------------------------------------------------------------------

TEAM_HOME_VENUES: dict[str, str] = {
    "Broncos": "Suncorp Stadium",
    "Roosters": "Allianz Stadium",
    "Storm": "AAMI Park",
    "Panthers": "CommBank Stadium",
    "Rabbitohs": "Accor Stadium",
    "Raiders": "GIO Stadium",
    "Cowboys": "Queensland Country Bank Stadium",
    "Knights": "McDonald Jones Stadium",
    "Sharks": "PointsBet Stadium",
    "Sea Eagles": "Brookvale Oval",
    "Eels": "CommBank Stadium",       # share with Panthers
    "Tigers": "Leichhardt Oval",
    "Dragons": "WIN Stadium",
    "Bulldogs": "Accor Stadium",      # share with Rabbitohs
    "Dolphins": "Suncorp Stadium",    # share with Broncos
    "Titans": "Cbus Super Stadium",
    "Warriors": "Mt Smart Stadium",
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two lat/lon points."""
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def compute_travel_distance(away_team: str, venue: str) -> float:
    """Compute great-circle distance from the away team's home venue to the match venue.

    Uses the Haversine formula to calculate the distance in kilometres.

    Args:
        away_team: NRL team name (e.g. "Storm").
        venue: Match venue name (e.g. "Suncorp Stadium").

    Returns:
        Distance in kilometres, or 0.0 if either venue is unknown.
    """
    home_venue = TEAM_HOME_VENUES.get(away_team)
    if home_venue is None:
        return 0.0

    home_coords = VENUE_COORDINATES.get(home_venue)
    match_coords = VENUE_COORDINATES.get(venue)

    if home_coords is None or match_coords is None:
        return 0.0

    return _haversine(home_coords[0], home_coords[1], match_coords[0], match_coords[1])


# ---------------------------------------------------------------------------
# Helper: filter history to games *before* a fixture's kickoff
# ---------------------------------------------------------------------------

def _parse_kickoff(kickoff_at: str) -> datetime | None:
    """Parse an ISO-8601 kickoff timestamp, tolerating several formats."""
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(kickoff_at, fmt)
        except ValueError:
            continue
    # Fallback: strip trailing 'Z' and try again
    try:
        return datetime.fromisoformat(kickoff_at.replace("Z", "+00:00"))
    except Exception:
        return None


def _history_before(
    fixture: Fixture, history: list[MatchResult]
) -> list[MatchResult]:
    """Return history entries with kickoff strictly before *fixture*."""
    fixture_dt = _parse_kickoff(fixture.kickoff_at)
    if fixture_dt is None:
        return history  # can't filter, use all

    filtered: list[MatchResult] = []
    for m in history:
        m_dt = _parse_kickoff(m.kickoff_at)
        if m_dt is None or m_dt < fixture_dt:
            filtered.append(m)
    return filtered


# ---------------------------------------------------------------------------
# Individual feature helpers
# ---------------------------------------------------------------------------

def _recent_form(team: str, history: list[MatchResult], n: int = 5) -> float:
    """Win ratio of *team* in their last *n* games."""
    team_games = [m for m in history if m.home_team == team or m.away_team == team]
    recent = team_games[-n:] if team_games else []
    if not recent:
        return 0.5
    wins = sum(1 for m in recent if m.winner == team)
    return wins / len(recent)


def _head_to_head(
    team_a: str, team_b: str, history: list[MatchResult], n: int = 4
) -> int:
    """Count of *team_a* wins in the last *n* H2H meetings."""
    h2h = [
        m
        for m in history
        if {m.home_team, m.away_team} == {team_a, team_b}
    ]
    recent = h2h[-n:] if h2h else []
    return sum(1 for m in recent if m.winner == team_a)


def _days_since_last_game(
    team: str, fixture: Fixture, history: list[MatchResult]
) -> int:
    """Days since *team*'s most recent game before *fixture*, capped at 14."""
    fixture_dt = _parse_kickoff(fixture.kickoff_at)
    if fixture_dt is None:
        return 7  # default

    team_games = [m for m in history if m.home_team == team or m.away_team == team]
    if not team_games:
        return 7

    last_game = team_games[-1]
    last_dt = _parse_kickoff(last_game.kickoff_at)
    if last_dt is None:
        return 7

    delta = (fixture_dt - last_dt).days
    return min(max(delta, 0), 14)


def _scoring_trend(team: str, history: list[MatchResult], n: int = 5) -> float:
    """Average points scored by *team* in their last *n* games."""
    team_games = [m for m in history if m.home_team == team or m.away_team == team]
    recent = team_games[-n:] if team_games else []
    if not recent:
        return 20.0  # league-average default
    total = sum(
        m.home_score if m.home_team == team else m.away_score for m in recent
    )
    return total / len(recent)


def _defensive_trend(team: str, history: list[MatchResult], n: int = 5) -> float:
    """Average points conceded by *team* in their last *n* games."""
    team_games = [m for m in history if m.home_team == team or m.away_team == team]
    recent = team_games[-n:] if team_games else []
    if not recent:
        return 20.0
    total = sum(
        m.away_score if m.home_team == team else m.home_score for m in recent
    )
    return total / len(recent)


def compute_venue_specific_win_rate(
    team: str,
    venue: str,
    history: list[MatchResult],
    min_games: int = 5,
) -> float:
    """Return *team*'s historical win rate at *venue*.

    Considers both home and away games played at the specified venue.
    Returns 0.5 (neutral) when fewer than *min_games* have been played
    at that venue, to avoid unreliable estimates from small samples.

    Args:
        team: Canonical team name (e.g. ``"Panthers"``).
        venue: Venue name as stored in :class:`MatchResult`.
        history: Chronologically sorted list of completed match results.
        min_games: Minimum number of games required for a valid estimate.

    Returns:
        Win rate in ``[0.0, 1.0]``, or ``0.5`` if insufficient data.
    """
    venue_games = [
        m for m in history
        if m.venue == venue and (m.home_team == team or m.away_team == team)
    ]
    total_games = len(venue_games)
    if total_games < min_games:
        return 0.5
    wins = sum(1 for m in venue_games if m.winner == team)
    return wins / total_games


def _ladder_position(team: str, ladder: dict) -> int:
    """Return *team*'s ladder position (1-indexed).  Defaults to 9 (mid-table)."""
    for row in ladder.get("rows", []):
        if row.get("team") == team:
            return int(row.get("rank", 9))
    return 9


def _pd_per_game(team: str, ladder: dict) -> float:
    """Points differential per game from the ladder."""
    for row in ladder.get("rows", []):
        if row.get("team") == team:
            played = int(row.get("played", 1)) or 1
            return int(row.get("pointsDiff", 0)) / played
    return 0.0


# ---------------------------------------------------------------------------
# Game ID parsing helpers
# ---------------------------------------------------------------------------

#: Regex to extract season and round from game IDs like "2026-r01-g01".
_GAME_ID_RE = re.compile(r"^(\d{4})-r(\d+)-", re.IGNORECASE)


def _parse_season_round(game_id: str) -> tuple[int | None, int | None]:
    """Extract (season, round_number) from a game ID string.

    Supports the canonical format ``"YYYY-rNN-gNN"`` (e.g. ``"2026-r01-g01"``).
    Returns ``(None, None)`` when the format is not recognised.

    Args:
        game_id: Game identifier string.

    Returns:
        A ``(season, round_number)`` tuple of integers, or ``(None, None)``.
    """
    m = _GAME_ID_RE.match(game_id)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_features(
    fixture: Fixture,
    elo_engine: EloEngine,
    history: list[MatchResult],
    ladder: dict,
    weather_data: WeatherData | None = None,
    injury_data: dict[str, InjuryStatus] | None = None,
) -> FeatureSet:
    """Compute the full feature set for *fixture*.

    All history entries should be sorted chronologically.  Features are
    computed using only data available *before* the fixture's kickoff.

    When *weather_data* is ``None`` the weather fields in the returned
    :class:`FeatureSet` will be left at their defaults (temperature_c=20.0,
    precipitation_mm=0.0, wind_speed_kmh=10.0, wet_weather=False).

    When *injury_data* is ``None`` (or a team is absent from the mapping)
    the injury fields default to zero adjustments and ``False`` flags.

    Args:
        fixture: The upcoming or historical fixture to compute features for.
        elo_engine: Trained :class:`EloEngine` instance with current ratings.
        history: Chronologically sorted list of completed :class:`MatchResult`
            objects.  Only entries *before* the fixture's kickoff are used.
        ladder: Current ladder dict (``{"rows": [{"team": ..., "rank": ...,
            "played": ..., "pointsDiff": ...}, ...]}``) used for ladder
            position and points-differential features.
        weather_data: Optional :class:`WeatherData` for the fixture's venue
            and kickoff time.  Pass ``None`` to use default weather values.
        injury_data: Optional mapping of team name → :class:`InjuryStatus`.
            Pass ``None`` or omit to use zero injury adjustments.

    Returns:
        A fully populated :class:`FeatureSet` for the fixture.
    """
    prior = _history_before(fixture, history)

    # ------------------------------------------------------------------
    # ELO features
    # ------------------------------------------------------------------
    elo_home = elo_engine.get_rating(fixture.home_team)
    elo_away = elo_engine.get_rating(fixture.away_team)
    # Include home advantage in the diff (matches how EloEngine.predict works)
    elo_diff = (elo_home + elo_engine.home_advantage) - elo_away

    # ------------------------------------------------------------------
    # Ladder features
    # ------------------------------------------------------------------
    home_ladder = _ladder_position(fixture.home_team, ladder)
    away_ladder = _ladder_position(fixture.away_team, ladder)

    # ------------------------------------------------------------------
    # Rest days and short turnaround
    # ------------------------------------------------------------------
    rest_days_home = _days_since_last_game(fixture.home_team, fixture, prior)
    rest_days_away = _days_since_last_game(fixture.away_team, fixture, prior)
    # Short turnaround: fewer than 6 days rest (Requirement 1.4)
    short_turnaround_home = rest_days_home < 6
    short_turnaround_away = rest_days_away < 6

    # ------------------------------------------------------------------
    # Season and round number (parsed from game_id)
    # ------------------------------------------------------------------
    season, round_number = _parse_season_round(fixture.game_id)

    # ------------------------------------------------------------------
    # State of Origin features (Requirement 1.3)
    # ------------------------------------------------------------------
    if season is not None and round_number is not None:
        soo_round = is_state_of_origin_round(season, round_number)
    else:
        soo_round = False
    # origin_affected counts are not automatically computable without a
    # representative player roster; default to 0 (populated externally if needed)
    origin_affected_home = 0
    origin_affected_away = 0

    # ------------------------------------------------------------------
    # Finals match flag (Requirement 1.7)
    # NRL finals begin at round 28 (rounds 1-27 are regular season)
    # ------------------------------------------------------------------
    finals_match = round_number is not None and round_number > 27

    # ------------------------------------------------------------------
    # Travel distance (Requirement 1.2)
    # ------------------------------------------------------------------
    travel_distance_km = compute_travel_distance(fixture.away_team, fixture.venue)

    # ------------------------------------------------------------------
    # Venue-specific win rates (Requirement 1.5)
    # ------------------------------------------------------------------
    venue_win_rate_home = compute_venue_specific_win_rate(
        fixture.home_team, fixture.venue, prior
    )
    venue_win_rate_away = compute_venue_specific_win_rate(
        fixture.away_team, fixture.venue, prior
    )

    # ------------------------------------------------------------------
    # Rivalry detection (Requirement 1.6)
    # ------------------------------------------------------------------
    rivalry = is_rivalry_game(fixture.home_team, fixture.away_team)

    # ------------------------------------------------------------------
    # Weather features (Requirement 2.1, 2.3, 2.4)
    # Use FeatureSet defaults when weather_data is None.
    # ------------------------------------------------------------------
    if weather_data is not None:
        temperature_c = weather_data.temperature_c
        precipitation_mm = weather_data.precipitation_mm
        wind_speed_kmh = weather_data.wind_speed_kmh
        wet_weather = precipitation_mm > 5.0
    else:
        temperature_c = 20.0
        precipitation_mm = 0.0
        wind_speed_kmh = 10.0
        wet_weather = False

    # ------------------------------------------------------------------
    # Injury / suspension features (Requirement 3.1, 3.3)
    # Use zero adjustments when injury_data is None or team not present.
    # ------------------------------------------------------------------
    injury_map: dict[str, InjuryStatus] = injury_data if injury_data is not None else {}

    home_injury = injury_map.get(fixture.home_team)
    if home_injury is not None:
        injury_impact_home = home_injury.total_impact
        key_player_out_home = home_injury.key_player_out
    else:
        injury_impact_home = 0.0
        key_player_out_home = False

    away_injury = injury_map.get(fixture.away_team)
    if away_injury is not None:
        injury_impact_away = away_injury.total_impact
        key_player_out_away = away_injury.key_player_out
    else:
        injury_impact_away = 0.0
        key_player_out_away = False

    # ------------------------------------------------------------------
    # Assemble and return the full feature set
    # ------------------------------------------------------------------
    return FeatureSet(
        # ELO-derived
        elo_diff=round(elo_diff, 2),
        elo_home=round(elo_home, 2),
        elo_away=round(elo_away, 2),
        home_advantage=1.0,
        # Recent form
        form_home_5=round(_recent_form(fixture.home_team, prior, 5), 4),
        form_away_5=round(_recent_form(fixture.away_team, prior, 5), 4),
        # Points differential
        pd_per_game_home=round(_pd_per_game(fixture.home_team, ladder), 2),
        pd_per_game_away=round(_pd_per_game(fixture.away_team, ladder), 2),
        # Ladder
        ladder_pos_diff=home_ladder - away_ladder,
        # Rest days
        rest_days_home=rest_days_home,
        rest_days_away=rest_days_away,
        # Head-to-head
        h2h_home_wins_recent=_head_to_head(fixture.home_team, fixture.away_team, prior, 4),
        # Scoring / defensive trends
        scoring_trend_home=round(_scoring_trend(fixture.home_team, prior, 5), 2),
        scoring_trend_away=round(_scoring_trend(fixture.away_team, prior, 5), 2),
        defensive_trend_home=round(_defensive_trend(fixture.home_team, prior, 5), 2),
        defensive_trend_away=round(_defensive_trend(fixture.away_team, prior, 5), 2),
        # NRL-specific contextual features
        travel_distance_km=round(travel_distance_km, 2),
        short_turnaround_home=short_turnaround_home,
        short_turnaround_away=short_turnaround_away,
        state_of_origin_round=soo_round,
        origin_affected_home=origin_affected_home,
        origin_affected_away=origin_affected_away,
        venue_win_rate_home=round(venue_win_rate_home, 4),
        venue_win_rate_away=round(venue_win_rate_away, 4),
        rivalry_game=rivalry,
        finals_match=finals_match,
        # Weather
        temperature_c=round(temperature_c, 2),
        precipitation_mm=round(precipitation_mm, 2),
        wind_speed_kmh=round(wind_speed_kmh, 2),
        wet_weather=wet_weather,
        # Injury / suspension
        injury_impact_home=round(injury_impact_home, 4),
        injury_impact_away=round(injury_impact_away, 4),
        key_player_out_home=key_player_out_home,
        key_player_out_away=key_player_out_away,
    )
