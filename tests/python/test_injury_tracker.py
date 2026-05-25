"""Tests for scripts/lib/injury_tracker.py.

Covers:
- load_injury_data: valid JSON, missing file fallback, malformed entries
- compute_injury_impact: known team, missing team, zero impact
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from scripts.lib.injury_tracker import (
    InjuryStatus,
    PlayerImpact,
    compute_injury_impact,
    load_injury_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_injury_json(tmp_path: Path, payload: dict) -> Path:
    """Write *payload* as JSON to a temp file and return the path."""
    p = tmp_path / "current.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_injury_data — valid JSON
# ---------------------------------------------------------------------------

class TestLoadInjuryDataValid:
    """load_injury_data correctly parses well-formed JSON."""

    def test_returns_dict_keyed_by_team(self, tmp_path: Path) -> None:
        payload = {
            "lastUpdated": "2026-05-01T10:00:00Z",
            "teams": {
                "Panthers": {
                    "unavailablePlayers": [
                        {
                            "playerName": "Nathan Cleary",
                            "position": "Halfback",
                            "impactScore": 0.85,
                            "status": "injured",
                        }
                    ],
                    "totalImpact": 0.85,
                    "keyPlayerOut": True,
                }
            },
        }
        path = _write_injury_json(tmp_path, payload)
        result = load_injury_data(path)

        assert "Panthers" in result
        assert isinstance(result["Panthers"], InjuryStatus)

    def test_total_impact_is_loaded(self, tmp_path: Path) -> None:
        payload = {
            "lastUpdated": "2026-05-01T10:00:00Z",
            "teams": {
                "Storm": {
                    "unavailablePlayers": [
                        {
                            "playerName": "Ryan Papenhuyzen",
                            "position": "Fullback",
                            "impactScore": 0.75,
                            "status": "injured",
                        }
                    ],
                    "totalImpact": 0.75,
                    "keyPlayerOut": True,
                }
            },
        }
        path = _write_injury_json(tmp_path, payload)
        result = load_injury_data(path)

        assert result["Storm"].total_impact == pytest.approx(0.75)

    def test_key_player_out_flag(self, tmp_path: Path) -> None:
        payload = {
            "lastUpdated": "2026-05-01T10:00:00Z",
            "teams": {
                "Broncos": {
                    "unavailablePlayers": [
                        {
                            "playerName": "Payne Haas",
                            "position": "Prop",
                            "impactScore": 0.8,
                            "status": "suspended",
                        }
                    ],
                    "totalImpact": 0.8,
                    "keyPlayerOut": True,
                }
            },
        }
        path = _write_injury_json(tmp_path, payload)
        result = load_injury_data(path)

        assert result["Broncos"].key_player_out is True

    def test_unavailable_players_are_player_impact_instances(self, tmp_path: Path) -> None:
        payload = {
            "lastUpdated": "2026-05-01T10:00:00Z",
            "teams": {
                "Raiders": {
                    "unavailablePlayers": [
                        {
                            "playerName": "Jack Wighton",
                            "position": "Five-eighth",
                            "impactScore": 0.6,
                            "status": "injured",
                        }
                    ],
                    "totalImpact": 0.6,
                    "keyPlayerOut": False,
                }
            },
        }
        path = _write_injury_json(tmp_path, payload)
        result = load_injury_data(path)

        players = result["Raiders"].unavailable_players
        assert len(players) == 1
        assert isinstance(players[0], PlayerImpact)
        assert players[0].player_name == "Jack Wighton"
        assert players[0].impact_score == pytest.approx(0.6)

    def test_multiple_teams_loaded(self, tmp_path: Path) -> None:
        payload = {
            "lastUpdated": "2026-05-01T10:00:00Z",
            "teams": {
                "Panthers": {
                    "unavailablePlayers": [],
                    "totalImpact": 0.0,
                    "keyPlayerOut": False,
                },
                "Storm": {
                    "unavailablePlayers": [],
                    "totalImpact": 0.0,
                    "keyPlayerOut": False,
                },
            },
        }
        path = _write_injury_json(tmp_path, payload)
        result = load_injury_data(path)

        assert set(result.keys()) == {"Panthers", "Storm"}

    def test_empty_teams_dict_returns_empty_result(self, tmp_path: Path) -> None:
        payload = {"lastUpdated": "2026-05-01T10:00:00Z", "teams": {}}
        path = _write_injury_json(tmp_path, payload)
        result = load_injury_data(path)

        assert result == {}

    def test_team_with_no_unavailable_players(self, tmp_path: Path) -> None:
        payload = {
            "lastUpdated": "2026-05-01T10:00:00Z",
            "teams": {
                "Cowboys": {
                    "unavailablePlayers": [],
                    "totalImpact": 0.0,
                    "keyPlayerOut": False,
                }
            },
        }
        path = _write_injury_json(tmp_path, payload)
        result = load_injury_data(path)

        assert result["Cowboys"].total_impact == 0.0
        assert result["Cowboys"].unavailable_players == ()


# ---------------------------------------------------------------------------
# load_injury_data — missing file fallback
# ---------------------------------------------------------------------------

class TestLoadInjuryDataMissingFile:
    """load_injury_data returns empty dict and logs a warning when file is absent."""

    def test_returns_empty_dict_when_file_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.json"
        result = load_injury_data(missing)

        assert result == {}

    def test_logs_warning_when_file_missing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        missing = tmp_path / "nonexistent.json"
        with caplog.at_level(logging.WARNING, logger="scripts.lib.injury_tracker"):
            load_injury_data(missing)

        assert any("not found" in msg.lower() or "zero adjustment" in msg.lower()
                   for msg in caplog.messages)

    def test_returns_empty_dict_on_invalid_json(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ not valid json }", encoding="utf-8")
        result = load_injury_data(bad_file)

        assert result == {}

    def test_logs_warning_on_invalid_json(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ not valid json }", encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="scripts.lib.injury_tracker"):
            load_injury_data(bad_file)

        assert len(caplog.messages) >= 1

    def test_uses_default_path_when_none_given(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When path=None and the default file is missing, returns empty dict."""
        # Patch the default path to a nonexistent location
        import scripts.lib.injury_tracker as tracker_mod
        monkeypatch.setattr(
            tracker_mod,
            "_DEFAULT_INJURY_PATH",
            Path("/tmp/definitely_does_not_exist_injury.json"),
        )
        result = load_injury_data(None)
        assert result == {}


# ---------------------------------------------------------------------------
# load_injury_data — malformed entries are skipped gracefully
# ---------------------------------------------------------------------------

class TestLoadInjuryDataMalformed:
    """Malformed team entries are skipped; valid entries are still returned."""

    def test_malformed_team_skipped_valid_team_returned(self, tmp_path: Path) -> None:
        payload = {
            "lastUpdated": "2026-05-01T10:00:00Z",
            "teams": {
                # Missing required fields — should be skipped
                "BadTeam": {"unavailablePlayers": [{"broken": True}]},
                # Valid entry
                "Panthers": {
                    "unavailablePlayers": [],
                    "totalImpact": 0.0,
                    "keyPlayerOut": False,
                },
            },
        }
        path = _write_injury_json(tmp_path, payload)
        result = load_injury_data(path)

        assert "Panthers" in result
        assert "BadTeam" not in result


# ---------------------------------------------------------------------------
# compute_injury_impact
# ---------------------------------------------------------------------------

class TestComputeInjuryImpact:
    """compute_injury_impact returns correct scores from an InjuryStatus mapping."""

    def _make_status(self, team: str, total_impact: float, key_player_out: bool = False) -> InjuryStatus:
        return InjuryStatus(
            team=team,
            fixture_date="2026-05-01T10:00:00Z",
            unavailable_players=(),
            total_impact=total_impact,
            key_player_out=key_player_out,
        )

    def test_returns_total_impact_for_known_team(self) -> None:
        injury_data = {"Panthers": self._make_status("Panthers", 0.85)}
        assert compute_injury_impact("Panthers", injury_data) == pytest.approx(0.85)

    def test_returns_zero_for_unknown_team(self) -> None:
        injury_data = {"Panthers": self._make_status("Panthers", 0.85)}
        assert compute_injury_impact("Storm", injury_data) == 0.0

    def test_returns_zero_for_empty_dict(self) -> None:
        assert compute_injury_impact("Broncos", {}) == 0.0

    def test_returns_zero_impact_when_team_has_no_injuries(self) -> None:
        injury_data = {"Cowboys": self._make_status("Cowboys", 0.0)}
        assert compute_injury_impact("Cowboys", injury_data) == 0.0

    def test_multiple_teams_independent(self) -> None:
        injury_data = {
            "Panthers": self._make_status("Panthers", 0.85),
            "Storm": self._make_status("Storm", 0.3),
            "Raiders": self._make_status("Raiders", 0.0),
        }
        assert compute_injury_impact("Panthers", injury_data) == pytest.approx(0.85)
        assert compute_injury_impact("Storm", injury_data) == pytest.approx(0.3)
        assert compute_injury_impact("Raiders", injury_data) == 0.0
        assert compute_injury_impact("Broncos", injury_data) == 0.0

    def test_high_impact_score(self) -> None:
        """Impact scores can be > 1.0 when multiple key players are out."""
        injury_data = {"Roosters": self._make_status("Roosters", 1.65)}
        assert compute_injury_impact("Roosters", injury_data) == pytest.approx(1.65)

    def test_round_trip_from_load_injury_data(self, tmp_path: Path) -> None:
        """compute_injury_impact works correctly with data loaded from JSON."""
        payload = {
            "lastUpdated": "2026-05-01T10:00:00Z",
            "teams": {
                "Panthers": {
                    "unavailablePlayers": [
                        {
                            "playerName": "Nathan Cleary",
                            "position": "Halfback",
                            "impactScore": 0.85,
                            "status": "injured",
                        }
                    ],
                    "totalImpact": 0.85,
                    "keyPlayerOut": True,
                }
            },
        }
        path = tmp_path / "current.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        injury_data = load_injury_data(path)
        assert compute_injury_impact("Panthers", injury_data) == pytest.approx(0.85)
        assert compute_injury_impact("Storm", injury_data) == 0.0
