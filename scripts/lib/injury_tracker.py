"""Injury and suspension tracking for NRL prediction model.

Tracks player availability and computes team strength adjustments based
on missing key players due to injury or suspension.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Default path for injury data relative to the project root
_DEFAULT_INJURY_PATH = Path("data/injuries/current.json")

# ---------------------------------------------------------------------------
# Injury tracking data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlayerImpact:
    """Impact weighting for a single player.
    
    Attributes:
        player_name: Full name of the player
        position: Playing position (e.g., "Halfback", "Prop")
        impact_score: Normalized impact score from 0.0 to 1.0 based on
            historical contribution (points scored, tackles, etc.)
        status: Current availability status
    """

    player_name: str
    position: str
    impact_score: float  # 0.0-1.0, based on historical contribution
    status: Literal["injured", "suspended", "available"]


@dataclass(frozen=True)
class InjuryStatus:
    """Team injury/suspension status for a fixture.
    
    Attributes:
        team: Team name
        fixture_date: ISO-8601 date of the fixture
        unavailable_players: Tuple of unavailable players with impact scores
        total_impact: Sum of all unavailable players' impact scores
        key_player_out: Whether any player with impact > 0.7 is unavailable
    """

    team: str
    fixture_date: str
    unavailable_players: tuple[PlayerImpact, ...]
    total_impact: float  # sum of impact_scores
    key_player_out: bool  # any player with impact > 0.7


# ---------------------------------------------------------------------------
# Injury data loading
# ---------------------------------------------------------------------------


def load_injury_data(
    data_path: Path | None = None,
) -> dict[str, InjuryStatus]:
    """Load current injury/suspension data from JSON.

    Reads ``data/injuries/current.json`` (or the path supplied via
    *data_path*) and returns a mapping of team name → :class:`InjuryStatus`.

    The JSON schema expected is::

        {
          "lastUpdated": "2026-04-15T10:00:00Z",
          "teams": {
            "Panthers": {
              "unavailablePlayers": [
                {
                  "playerName": "Nathan Cleary",
                  "position": "Halfback",
                  "impactScore": 0.85,
                  "status": "injured"
                }
              ],
              "totalImpact": 0.85,
              "keyPlayerOut": true
            }
          }
        }

    Falls back to an empty dict (no injuries for any team) when the file
    is missing or cannot be parsed, and logs a warning in that case.

    Args:
        data_path: Optional override for the injury data file path.
            Defaults to ``data/injuries/current.json`` relative to the
            current working directory.

    Returns:
        Mapping of team name to :class:`InjuryStatus`.  An empty dict
        means no injury data is available (all teams treated as at full
        strength).
    """
    path = data_path if data_path is not None else _DEFAULT_INJURY_PATH

    if not path.exists():
        logger.warning(
            "Injury data file not found at '%s'; proceeding with zero adjustment.",
            path,
        )
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Failed to read injury data from '%s' (%s); proceeding with zero adjustment.",
            path,
            exc,
        )
        return {}

    teams_raw: dict = raw.get("teams", {})
    result: dict[str, InjuryStatus] = {}

    for team_name, team_data in teams_raw.items():
        try:
            unavailable = tuple(
                PlayerImpact(
                    player_name=p["playerName"],
                    position=p["position"],
                    impact_score=float(p["impactScore"]),
                    status=p["status"],
                )
                for p in team_data.get("unavailablePlayers", [])
            )
            result[team_name] = InjuryStatus(
                team=team_name,
                fixture_date=raw.get("lastUpdated", ""),
                unavailable_players=unavailable,
                total_impact=float(team_data.get("totalImpact", 0.0)),
                key_player_out=bool(team_data.get("keyPlayerOut", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "Skipping malformed injury entry for team '%s': %s",
                team_name,
                exc,
            )

    return result
