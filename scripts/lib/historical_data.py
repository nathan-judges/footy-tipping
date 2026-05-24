"""Historical match results database for model training.

Provides utilities to load, store, and manage historical NRL match results
from both the local archive and the NRL draw API.  These results feed the
ELO rating engine and feature extraction pipeline.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .types import Fixture

# ---------------------------------------------------------------------------
# Team name normalisation
# ---------------------------------------------------------------------------

TEAM_ALIASES: dict[str, str] = {
    # Full names → canonical nicknames
    "Canterbury-Bankstown Bulldogs": "Bulldogs",
    "Canterbury Bulldogs": "Bulldogs",
    "Canberra Raiders": "Raiders",
    "Cronulla-Sutherland Sharks": "Sharks",
    "Cronulla Sharks": "Sharks",
    "Gold Coast Titans": "Titans",
    "Manly-Warringah Sea Eagles": "Sea Eagles",
    "Manly Sea Eagles": "Sea Eagles",
    "Melbourne Storm": "Storm",
    "Newcastle Knights": "Knights",
    "New Zealand Warriors": "Warriors",
    "NZ Warriors": "Warriors",
    "North Queensland Cowboys": "Cowboys",
    "Parramatta Eels": "Eels",
    "Penrith Panthers": "Panthers",
    "South Sydney Rabbitohs": "Rabbitohs",
    "St George Illawarra Dragons": "Dragons",
    "Sydney Roosters": "Roosters",
    "Brisbane Broncos": "Broncos",
    "The Dolphins": "Dolphins",
    "Redcliffe Dolphins": "Dolphins",
    "Wests Tigers": "Wests Tigers",
    "Western Suburbs Magpies": "Wests Tigers",
    # Already canonical
    "Bulldogs": "Bulldogs",
    "Raiders": "Raiders",
    "Sharks": "Sharks",
    "Titans": "Titans",
    "Sea Eagles": "Sea Eagles",
    "Storm": "Storm",
    "Knights": "Knights",
    "Warriors": "Warriors",
    "Cowboys": "Cowboys",
    "Eels": "Eels",
    "Panthers": "Panthers",
    "Rabbitohs": "Rabbitohs",
    "Dragons": "Dragons",
    "Roosters": "Roosters",
    "Broncos": "Broncos",
    "Dolphins": "Dolphins",
}


def normalize_team(name: str) -> str:
    """Return canonical team nickname, falling back to the input if unknown."""
    return TEAM_ALIASES.get(name.strip(), name.strip())


# ---------------------------------------------------------------------------
# MatchResult dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MatchResult:
    """A single completed NRL match result."""

    season: int
    round_number: int
    game_id: str
    home_team: str
    away_team: str
    venue: str
    home_score: int
    away_score: int
    winner: str
    margin: int
    kickoff_at: str


# ---------------------------------------------------------------------------
# Loading from archive (local baked JSON snapshots)
# ---------------------------------------------------------------------------

def load_from_archive(archive_dir: Path | None = None) -> list[MatchResult]:
    """Load historical match results from ``data/archive/round_*.json``.

    Only games with ``status == "finished"`` and valid scores are included.
    """
    if archive_dir is None:
        archive_dir = Path("data/archive")
    if not archive_dir.is_dir():
        return []

    results: list[MatchResult] = []
    for path in sorted(archive_dir.glob("round_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        results.extend(_parse_round_payload(payload))
    return results


def _parse_round_payload(payload: dict) -> list[MatchResult]:
    """Extract ``MatchResult`` entries from a baked round JSON payload."""
    season = int(payload.get("season", 0))
    round_number = int(payload.get("round", 0))
    results: list[MatchResult] = []
    for game in payload.get("games", []):
        if game.get("status") != "finished":
            continue
        home_score = game.get("homeScore")
        away_score = game.get("awayScore")
        if not isinstance(home_score, int) or not isinstance(away_score, int):
            continue

        home_team = normalize_team(game.get("homeTeam", ""))
        away_team = normalize_team(game.get("awayTeam", ""))
        if home_score == away_score:
            winner = "draw"
            margin = 0
        else:
            winner = home_team if home_score > away_score else away_team
            margin = abs(home_score - away_score)

        results.append(
            MatchResult(
                season=season,
                round_number=round_number,
                game_id=game.get("gameId", ""),
                home_team=home_team,
                away_team=away_team,
                venue=game.get("venue", ""),
                home_score=home_score,
                away_score=away_score,
                winner=winner,
                margin=margin,
                kickoff_at=game.get("kickoffAt", ""),
            )
        )
    return results


# ---------------------------------------------------------------------------
# Loading / saving season files  (data/historical/<season>.json)
# ---------------------------------------------------------------------------

_DEFAULT_HISTORY_DIR = Path("data/historical")


def load_historical_data(data_dir: Path | None = None) -> list[MatchResult]:
    """Load all historical data from ``data/historical/*.json``."""
    data_dir = data_dir or _DEFAULT_HISTORY_DIR
    if not data_dir.is_dir():
        return []

    results: list[MatchResult] = []
    for path in sorted(data_dir.glob("*.json")):
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            try:
                results.append(MatchResult(**entry))
            except (TypeError, KeyError):
                continue
    return results


def save_season_data(
    season: int,
    results: list[MatchResult],
    data_dir: Path | None = None,
) -> Path:
    """Persist results for *season* to ``data/historical/<season>.json``."""
    data_dir = data_dir or _DEFAULT_HISTORY_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{season}.json"
    serialized = [asdict(r) for r in results if r.season == season]
    path.write_text(json.dumps(serialized, indent=2) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Fetching from NRL API (uses existing fetch_data helpers)
# ---------------------------------------------------------------------------

def fetch_season_results(season: int, max_rounds: int = 30) -> list[MatchResult]:
    """Fetch all completed match results for *season* from the NRL draw API.

    Uses :func:`scripts.lib.fetch_data.fetch_round_fixtures` under the hood.
    Stops early when a round returns no finished fixtures.
    """
    from .fetch_data import fetch_round_fixtures

    all_results: list[MatchResult] = []
    consecutive_empty = 0
    for rnd in range(1, max_rounds + 1):
        try:
            fixtures = fetch_round_fixtures(season=season, round_number=rnd)
        except Exception:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                break
            continue

        finished = [f for f in fixtures if f.status == "finished"]
        if not finished:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                break
            continue

        consecutive_empty = 0
        for f in finished:
            if f.home_score is None or f.away_score is None:
                continue
            home_team = normalize_team(f.home_team)
            away_team = normalize_team(f.away_team)
            if f.home_score == f.away_score:
                winner = "draw"
                margin = 0
            else:
                winner = home_team if f.home_score > f.away_score else away_team
                margin = abs(f.home_score - f.away_score)

            all_results.append(
                MatchResult(
                    season=season,
                    round_number=rnd,
                    game_id=f.game_id,
                    home_team=home_team,
                    away_team=away_team,
                    venue=f.venue,
                    home_score=f.home_score,
                    away_score=f.away_score,
                    winner=winner,
                    margin=margin,
                    kickoff_at=f.kickoff_at,
                )
            )
    return all_results


# ---------------------------------------------------------------------------
# Convenience: load everything available
# ---------------------------------------------------------------------------

def load_all_history() -> list[MatchResult]:
    """Load history from both ``data/historical/`` and ``data/archive/``."""
    seen_ids: set[str] = set()
    combined: list[MatchResult] = []

    for result in load_historical_data():
        if result.game_id not in seen_ids:
            seen_ids.add(result.game_id)
            combined.append(result)

    for result in load_from_archive():
        if result.game_id not in seen_ids:
            seen_ids.add(result.game_id)
            combined.append(result)

    combined.sort(key=lambda r: (r.season, r.round_number, r.kickoff_at))
    return combined
