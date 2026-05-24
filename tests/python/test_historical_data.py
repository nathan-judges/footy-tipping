"""Tests for the historical data module."""

import json
import tempfile
from pathlib import Path

from scripts.lib.historical_data import (
    MatchResult,
    load_from_archive,
    load_all_history,
    normalize_team,
)


def test_normalize_team_canonical() -> None:
    assert normalize_team("Bulldogs") == "Bulldogs"
    assert normalize_team("Panthers") == "Panthers"
    assert normalize_team("Sea Eagles") == "Sea Eagles"


def test_normalize_team_aliases() -> None:
    assert normalize_team("Canterbury-Bankstown Bulldogs") == "Bulldogs"
    assert normalize_team("Manly-Warringah Sea Eagles") == "Sea Eagles"
    assert normalize_team("Melbourne Storm") == "Storm"
    assert normalize_team("Cronulla-Sutherland Sharks") == "Sharks"


def test_normalize_team_unknown() -> None:
    assert normalize_team("Unknown Team") == "Unknown Team"


def test_load_from_archive() -> None:
    """Load from the actual project archive data."""
    archive_dir = Path("data/archive")
    if not archive_dir.is_dir():
        return  # Skip if no archive data

    results = load_from_archive(archive_dir)
    # Rounds 1-7 all have finished games in the archive
    assert len(results) > 0

    for r in results:
        assert isinstance(r, MatchResult)
        assert r.home_score >= 0
        assert r.away_score >= 0
        assert r.winner in (r.home_team, r.away_team, "draw")
        assert r.margin >= 0


def test_load_from_archive_with_temp_dir() -> None:
    """Test loading from a synthetic archive directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        round_data = {
            "round": 1,
            "season": 2026,
            "games": [
                {
                    "gameId": "g1",
                    "homeTeam": "Panthers",
                    "awayTeam": "Dragons",
                    "venue": "Test",
                    "kickoffAt": "2026-03-06T09:00:00Z",
                    "status": "finished",
                    "tipTeam": "Panthers",
                    "confidence": 0.7,
                    "predictedMargin": 10,
                    "homeScore": 24,
                    "awayScore": 12,
                    "actualWinner": "Panthers",
                    "actualMargin": 12,
                }
            ],
        }
        path = Path(tmpdir) / "round_1.json"
        path.write_text(json.dumps(round_data))

        results = load_from_archive(Path(tmpdir))
        assert len(results) == 1
        assert results[0].winner == "Panthers"
        assert results[0].margin == 12


def test_load_all_history_deduplicates() -> None:
    """Ensure load_all_history doesn't return duplicate game IDs."""
    results = load_all_history()
    game_ids = [r.game_id for r in results]
    assert len(game_ids) == len(set(game_ids)), "Duplicate game IDs found"
