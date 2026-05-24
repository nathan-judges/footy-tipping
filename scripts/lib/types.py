"""Typed contracts for the baked data pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GameStatus = Literal["upcoming", "live", "finished"]


@dataclass(frozen=True)
class Fixture:
    game_id: str
    nrl_match_id: int | None
    nrl_slug: str | None
    home_team: str
    away_team: str
    venue: str
    kickoff_at: str
    status: GameStatus
    home_score: int | None = None
    away_score: int | None = None
    actual_winner: str | None = None
    actual_margin: int | None = None


@dataclass(frozen=True)
class OddsSnapshot:
    home: float
    away: float


@dataclass(frozen=True)
class TipResult:
    game_id: str
    nrl_match_id: int | None
    nrl_slug: str | None
    home_team: str
    away_team: str
    venue: str
    kickoff_at: str
    status: GameStatus
    tip_team: str
    confidence: float
    predicted_margin: int
    odds: OddsSnapshot | None = None
    home_score: int | None = None
    away_score: int | None = None
    actual_winner: str | None = None
    actual_margin: int | None = None
    diagnostics: ModelDiagnostics | None = None


# ---------------------------------------------------------------------------
# Ensemble model diagnostics
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EloSnapshot:
    """Point-in-time ELO state for a team."""

    team: str
    rating: float
    rating_change: float  # change from last game


@dataclass(frozen=True)
class SubPrediction:
    """Individual sub-model prediction within the ensemble."""

    model_name: str  # 'elo', 'features', 'market'
    tip_team: str
    confidence: float
    weight: float


@dataclass(frozen=True)
class ModelDiagnostics:
    """Diagnostic data attached to a TipResult for transparency."""

    elo_home: float
    elo_away: float
    sub_predictions: tuple[SubPrediction, ...]
    feature_summary: dict  # key features that influenced the prediction
