"""ELO rating engine for NRL match prediction.

Implements a proper ELO system calibrated for the NRL with:
- Margin-of-victory adjustment (log-based with autocorrelation prevention)
- Home ground advantage (+40 ELO ≈ 57% implied win rate)
- Season-to-season regression toward the mean
- Persistence to/from JSON
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .historical_data import MatchResult

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class EloRating:
    """Current ELO state for a single team."""

    team: str
    rating: float = 1500.0
    last_updated: str = ""
    games_played: int = 0


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class EloEngine:
    """ELO rating engine with NRL-specific calibration.

    Parameters
    ----------
    k_factor:
        Base K-factor controlling update magnitude.  20 is standard for
        established leagues.
    home_advantage:
        ELO points added to the home team's effective rating when computing
        expected scores and predictions.  40 ≈ 57% implied home-win rate.
    initial_rating:
        Starting rating for teams seen for the first time.
    """

    def __init__(
        self,
        k_factor: float = 20.0,
        home_advantage: float = 40.0,
        initial_rating: float = 1500.0,
    ) -> None:
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.initial_rating = initial_rating
        self._ratings: dict[str, EloRating] = {}

    # -- helpers ----------------------------------------------------------

    def _ensure_team(self, team: str) -> None:
        if team not in self._ratings:
            self._ratings[team] = EloRating(team=team, rating=self.initial_rating)

    @staticmethod
    def _expected_score(rating_a: float, rating_b: float) -> float:
        """Standard ELO expected score for player A vs player B."""
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    @staticmethod
    def _margin_multiplier(margin: int, elo_diff: float) -> float:
        """Margin-of-victory multiplier.

        Uses ``ln(|margin| + 1)`` scaled by an autocorrelation-prevention
        factor so that blowout wins by favourites produce smaller rating
        swings than blowout wins by underdogs.
        """
        return math.log(abs(margin) + 1) * (2.2 / (0.001 * abs(elo_diff) + 2.2))

    # -- core API ---------------------------------------------------------

    def update(
        self,
        home_team: str,
        away_team: str,
        home_score: int,
        away_score: int,
    ) -> tuple[float, float]:
        """Update ratings after a completed game.

        Returns the rating change ``(home_delta, away_delta)``.
        """
        self._ensure_team(home_team)
        self._ensure_team(away_team)

        home_rating = self._ratings[home_team].rating + self.home_advantage
        away_rating = self._ratings[away_team].rating

        expected_home = self._expected_score(home_rating, away_rating)

        if home_score > away_score:
            actual_home = 1.0
        elif home_score < away_score:
            actual_home = 0.0
        else:
            actual_home = 0.5

        margin = abs(home_score - away_score)
        elo_diff = home_rating - away_rating
        mov = self._margin_multiplier(margin, elo_diff)

        delta = self.k_factor * mov * (actual_home - expected_home)

        self._ratings[home_team].rating += delta
        self._ratings[away_team].rating -= delta
        self._ratings[home_team].games_played += 1
        self._ratings[away_team].games_played += 1

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        self._ratings[home_team].last_updated = now_iso
        self._ratings[away_team].last_updated = now_iso

        return delta, -delta

    def predict(
        self, home_team: str, away_team: str
    ) -> tuple[str, float, int]:
        """Predict the winner, win probability, and expected margin.

        Returns ``(predicted_winner, win_probability, predicted_margin)``
        where *win_probability* is the confidence in the predicted winner.
        """
        self._ensure_team(home_team)
        self._ensure_team(away_team)

        home_eff = self._ratings[home_team].rating + self.home_advantage
        away_eff = self._ratings[away_team].rating

        home_prob = self._expected_score(home_eff, away_eff)

        if home_prob >= 0.5:
            winner = home_team
            prob = home_prob
        else:
            winner = away_team
            prob = 1.0 - home_prob

        # Rough margin estimate: scale ELO diff linearly
        # ~25 ELO points ≈ 1 point of expected margin (NRL-calibrated)
        elo_diff = home_eff - away_eff
        raw_margin = elo_diff / 25.0
        predicted_margin = max(0, int(round(abs(raw_margin))))

        return winner, round(prob, 4), predicted_margin

    def regress_to_mean(self, factor: float = 1.0 / 3.0) -> None:
        """Regress all ratings toward ``initial_rating`` by *factor*.

        Called between seasons to account for roster changes and
        mean-reversion.
        """
        for rating in self._ratings.values():
            rating.rating = (
                rating.rating * (1 - factor) + self.initial_rating * factor
            )

    # -- accessors --------------------------------------------------------

    def get_rating(self, team: str) -> float:
        """Return the current ELO rating for *team*."""
        self._ensure_team(team)
        return self._ratings[team].rating

    def get_ratings(self) -> dict[str, EloRating]:
        """Return a copy of all current ratings."""
        return dict(self._ratings)

    # -- persistence ------------------------------------------------------

    def save(self, path: Path | None = None) -> None:
        """Persist current ratings to a JSON file."""
        path = path or Path("data/elo_ratings.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "k_factor": self.k_factor,
            "home_advantage": self.home_advantage,
            "initial_rating": self.initial_rating,
            "ratings": {
                team: asdict(rating) for team, rating in self._ratings.items()
            },
        }
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def load(self, path: Path | None = None) -> None:
        """Load ratings from a JSON file.  Overwrites current state."""
        path = path or Path("data/elo_ratings.json")
        if not path.is_file():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.k_factor = data.get("k_factor", self.k_factor)
        self.home_advantage = data.get("home_advantage", self.home_advantage)
        self.initial_rating = data.get("initial_rating", self.initial_rating)
        self._ratings = {}
        for team, info in data.get("ratings", {}).items():
            self._ratings[team] = EloRating(
                team=info.get("team", team),
                rating=float(info.get("rating", self.initial_rating)),
                last_updated=info.get("last_updated", ""),
                games_played=int(info.get("games_played", 0)),
            )


# ---------------------------------------------------------------------------
# Builder: train ELO from historical results
# ---------------------------------------------------------------------------

def build_elo_from_history(
    results: list[MatchResult],
    *,
    k_factor: float = 20.0,
    home_advantage: float = 40.0,
    regress_between_seasons: bool = True,
) -> EloEngine:
    """Build an ELO engine by replaying historical match results.

    Results must be sorted chronologically (season, round, kickoff).
    Season regression is applied at each season boundary when
    *regress_between_seasons* is ``True``.
    """
    engine = EloEngine(
        k_factor=k_factor,
        home_advantage=home_advantage,
    )

    sorted_results = sorted(
        results, key=lambda r: (r.season, r.round_number, r.kickoff_at)
    )

    prev_season: int | None = None
    for result in sorted_results:
        if prev_season is not None and result.season != prev_season and regress_between_seasons:
            engine.regress_to_mean()
        prev_season = result.season

        engine.update(
            home_team=result.home_team,
            away_team=result.away_team,
            home_score=result.home_score,
            away_score=result.away_score,
        )

    return engine
