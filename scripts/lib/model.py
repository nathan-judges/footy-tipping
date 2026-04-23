"""Prediction model and odds calibration."""

from __future__ import annotations

from .fetch_data import fetch_odds_for_fixture
from .types import Fixture, OddsSnapshot, TipResult


def _team_strength(team_name: str) -> float:
    """Deterministic baseline strength from team name hash."""
    return (sum(ord(ch) for ch in team_name) % 100) / 100.0


def _elo_tip(fixture: Fixture) -> tuple[str, float, int]:
    home_strength = _team_strength(fixture.home_team)
    away_strength = _team_strength(fixture.away_team)
    diff = away_strength - home_strength
    away_prob = 1 / (1 + 10 ** (-diff))
    tip = fixture.away_team if away_prob >= 0.5 else fixture.home_team
    confidence = away_prob if tip == fixture.away_team else (1 - away_prob)
    margin = int(round(abs(diff) * 18))
    return tip, confidence, margin


def _market_tip(fixture: Fixture, odds: OddsSnapshot | None) -> str | None:
    if odds is None:
        return None
    return fixture.home_team if odds.home < odds.away else fixture.away_team


def _calibrate_tip(fixture: Fixture, base_tip: str, base_confidence: float, odds: OddsSnapshot | None) -> str:
    market_tip = _market_tip(fixture, odds)
    if market_tip is None:
        return base_tip
    # Override when model is low confidence and market disagrees.
    if market_tip != base_tip and base_confidence < 0.62:
        return market_tip
    return base_tip


def predict_fixture(fixture: Fixture) -> TipResult:
    if fixture.status != "upcoming":
        return TipResult(
            game_id=fixture.game_id,
            nrl_match_id=fixture.nrl_match_id,
            nrl_slug=fixture.nrl_slug,
            home_team=fixture.home_team,
            away_team=fixture.away_team,
            venue=fixture.venue,
            kickoff_at=fixture.kickoff_at,
            status=fixture.status,
            tip_team="N/A",
            confidence=0.0,
            predicted_margin=0,
            odds=None,
            home_score=fixture.home_score,
            away_score=fixture.away_score,
            actual_winner=fixture.actual_winner,
            actual_margin=fixture.actual_margin,
        )

    base_tip, confidence, margin = _elo_tip(fixture)
    odds = fetch_odds_for_fixture(fixture)
    final_tip = _calibrate_tip(fixture, base_tip, confidence, odds)
    return TipResult(
        game_id=fixture.game_id,
        nrl_match_id=fixture.nrl_match_id,
        nrl_slug=fixture.nrl_slug,
        home_team=fixture.home_team,
        away_team=fixture.away_team,
        venue=fixture.venue,
        kickoff_at=fixture.kickoff_at,
        status=fixture.status,
        tip_team=final_tip,
        confidence=round(confidence, 4),
        predicted_margin=margin,
        odds=odds,
    )


def run_model(fixtures: list[Fixture]) -> list[TipResult]:
    return [predict_fixture(fixture) for fixture in fixtures]
