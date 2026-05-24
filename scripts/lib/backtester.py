"""Walk-forward backtesting engine for model validation.

Replays historical data round-by-round, building ELO ratings from all
prior data at each step, making predictions, and comparing to actuals.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .elo_ratings import EloEngine, build_elo_from_history
from .features import FeatureSet, extract_features, feature_vector
from .historical_data import MatchResult
from .types import Fixture


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class GamePrediction:
    """Prediction vs actual for a single game."""

    game_id: str
    home_team: str
    away_team: str
    predicted_winner: str
    actual_winner: str
    confidence: float
    correct: bool


@dataclass
class BacktestResult:
    """Backtesting results for a single round."""

    season: int
    round_number: int
    total_games: int
    correct_predictions: int
    accuracy: float
    predictions: list[GamePrediction] = field(default_factory=list)


@dataclass
class BacktestSummary:
    """Aggregate backtesting statistics."""

    total_games: int
    correct: int
    accuracy_pct: float
    brier_score: float
    avg_confidence_when_correct: float
    avg_confidence_when_wrong: float


# ---------------------------------------------------------------------------
# Core backtest engine
# ---------------------------------------------------------------------------

def run_backtest(
    history: list[MatchResult],
    start_season: int = 2025,
    start_round: int = 1,
) -> list[BacktestResult]:
    """Walk-forward backtesting.

    For each round from *start_season*/*start_round* onward:
    1. Build ELO from all prior data
    2. Make predictions for that round's games
    3. Compare to actual outcomes
    4. Record accuracy

    Returns a list of per-round :class:`BacktestResult` objects.
    """
    # Sort chronologically
    sorted_history = sorted(
        history, key=lambda r: (r.season, r.round_number, r.kickoff_at)
    )

    # Group into (season, round) buckets
    rounds: dict[tuple[int, int], list[MatchResult]] = {}
    for result in sorted_history:
        key = (result.season, result.round_number)
        rounds.setdefault(key, []).append(result)

    results: list[BacktestResult] = []

    for (season, rnd), round_games in sorted(rounds.items()):
        if season < start_season:
            continue
        if season == start_season and rnd < start_round:
            continue

        # Build ELO from everything *before* this round
        prior = [
            r for r in sorted_history
            if (r.season, r.round_number) < (season, rnd)
        ]

        if len(prior) < 16:
            # Not enough data to form meaningful ELO ratings
            continue

        engine = build_elo_from_history(prior)

        predictions: list[GamePrediction] = []
        for game in round_games:
            winner, prob, _ = engine.predict(game.home_team, game.away_team)

            if game.winner == "draw":
                # Skip draws for accuracy tracking
                continue

            correct = winner == game.winner
            predictions.append(
                GamePrediction(
                    game_id=game.game_id,
                    home_team=game.home_team,
                    away_team=game.away_team,
                    predicted_winner=winner,
                    actual_winner=game.winner,
                    confidence=prob,
                    correct=correct,
                )
            )

        if not predictions:
            continue

        correct_count = sum(1 for p in predictions if p.correct)
        accuracy = correct_count / len(predictions) if predictions else 0.0

        results.append(
            BacktestResult(
                season=season,
                round_number=rnd,
                total_games=len(predictions),
                correct_predictions=correct_count,
                accuracy=round(accuracy, 4),
                predictions=predictions,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarize_backtest(results: list[BacktestResult]) -> BacktestSummary:
    """Compute aggregate statistics from backtest results."""
    all_preds: list[GamePrediction] = []
    for r in results:
        all_preds.extend(r.predictions)

    total = len(all_preds)
    if total == 0:
        return BacktestSummary(
            total_games=0,
            correct=0,
            accuracy_pct=0.0,
            brier_score=0.25,
            avg_confidence_when_correct=0.0,
            avg_confidence_when_wrong=0.0,
        )

    correct = sum(1 for p in all_preds if p.correct)

    # Brier score: mean squared error of probability forecasts
    brier_total = 0.0
    correct_confs: list[float] = []
    wrong_confs: list[float] = []

    for p in all_preds:
        outcome = 1.0 if p.correct else 0.0
        brier_total += (p.confidence - outcome) ** 2
        if p.correct:
            correct_confs.append(p.confidence)
        else:
            wrong_confs.append(p.confidence)

    return BacktestSummary(
        total_games=total,
        correct=correct,
        accuracy_pct=round(100.0 * correct / total, 2),
        brier_score=round(brier_total / total, 4),
        avg_confidence_when_correct=round(
            sum(correct_confs) / len(correct_confs), 4
        ) if correct_confs else 0.0,
        avg_confidence_when_wrong=round(
            sum(wrong_confs) / len(wrong_confs), 4
        ) if wrong_confs else 0.0,
    )


# ---------------------------------------------------------------------------
# Baseline comparisons
# ---------------------------------------------------------------------------

def compare_to_baselines(history: list[MatchResult]) -> dict[str, float]:
    """Compare model accuracy to simple baselines.

    Returns a dict mapping baseline name to accuracy percentage.
    """
    non_draws = [r for r in history if r.winner != "draw"]
    if not non_draws:
        return {"always_home": 0.0, "random": 50.0}

    total = len(non_draws)

    # Baseline 1: always tip the home team
    home_wins = sum(1 for r in non_draws if r.winner == r.home_team)
    home_pct = round(100.0 * home_wins / total, 2)

    # Baseline 2: random (50/50)
    random_pct = 50.0

    return {
        "always_home": home_pct,
        "random": random_pct,
        "total_games": float(total),
    }
