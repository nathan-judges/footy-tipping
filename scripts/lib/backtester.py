"""Walk-forward backtesting engine for model validation.

Replays historical data round-by-round, building ELO ratings from all
prior data at each step, making predictions, and comparing to actuals.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .elo_ratings import EloEngine, build_elo_from_history
from .features import FeatureSet, extract_features, feature_vector
from .historical_data import MatchResult
from .types import Fixture

# NRL finals begin at round 28 (rounds 1-27 are regular season)
_FINALS_START_ROUND: int = 28


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
    """Aggregate backtesting statistics with detailed breakdowns.

    Attributes:
        overall_accuracy: Fraction of games predicted correctly (0.0–1.0).
        brier_score: Mean squared error of probability forecasts (lower is
            better; 0.25 is random).
        log_loss: Mean log-loss of probability forecasts (lower is better).
        per_season: Mapping of season year → accuracy fraction.
        per_team: Mapping of team name → accuracy fraction (games involving
            that team as home or away).
        regular_season_accuracy: Accuracy on rounds 1–27 only.
        finals_accuracy: Accuracy on rounds 28+ only.
        total_games: Total number of non-draw games evaluated.

    .. note::
        The legacy fields ``correct``, ``accuracy_pct``,
        ``avg_confidence_when_correct``, and ``avg_confidence_when_wrong``
        are retained for backward compatibility.
    """

    # --- Primary fields (Requirement 6.1–6.4) ---
    overall_accuracy: float
    brier_score: float
    log_loss: float
    per_season: dict[int, float]
    per_team: dict[str, float]
    regular_season_accuracy: float
    finals_accuracy: float
    total_games: int

    # --- Legacy fields (backward compatibility) ---
    correct: int = 0
    accuracy_pct: float = 0.0
    avg_confidence_when_correct: float = 0.0
    avg_confidence_when_wrong: float = 0.0


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

def _safe_log_loss(confidence: float, correct: bool) -> float:
    """Compute per-prediction log-loss, clipping probability to avoid log(0)."""
    eps = 1e-15
    p = max(eps, min(1.0 - eps, confidence))
    outcome = 1.0 if correct else 0.0
    return -(outcome * math.log(p) + (1.0 - outcome) * math.log(1.0 - p))


def summarize_backtest(
    results: list[BacktestResult],
    output_path: Path | None = None,
) -> BacktestSummary:
    """Compute aggregate statistics from backtest results.

    Produces overall accuracy, Brier score, log-loss, per-season accuracy,
    per-team accuracy, and a regular-season vs finals split.

    Optionally writes the summary to *output_path* as JSON when provided.

    Args:
        results: Per-round :class:`BacktestResult` objects from
            :func:`run_backtest`.
        output_path: Optional file path to write the JSON summary.  The
            parent directory is created if it does not exist.  Pass ``None``
            (the default) to skip file output.

    Returns:
        A :class:`BacktestSummary` with all breakdown fields populated.
    """
    # Flatten all predictions, keeping track of season and round
    all_preds: list[tuple[GamePrediction, int, int]] = []  # (pred, season, round)
    for r in results:
        for p in r.predictions:
            all_preds.append((p, r.season, r.round_number))

    total = len(all_preds)
    if total == 0:
        empty = BacktestSummary(
            overall_accuracy=0.0,
            brier_score=0.25,
            log_loss=1.0,
            per_season={},
            per_team={},
            regular_season_accuracy=0.0,
            finals_accuracy=0.0,
            total_games=0,
            correct=0,
            accuracy_pct=0.0,
            avg_confidence_when_correct=0.0,
            avg_confidence_when_wrong=0.0,
        )
        if output_path is not None:
            _write_summary_json(empty, output_path)
        return empty

    # --- Overall metrics ---
    correct_count = sum(1 for p, _, _ in all_preds if p.correct)
    overall_accuracy = correct_count / total

    brier_total = 0.0
    log_loss_total = 0.0
    correct_confs: list[float] = []
    wrong_confs: list[float] = []

    for p, _, _ in all_preds:
        outcome = 1.0 if p.correct else 0.0
        brier_total += (p.confidence - outcome) ** 2
        log_loss_total += _safe_log_loss(p.confidence, p.correct)
        if p.correct:
            correct_confs.append(p.confidence)
        else:
            wrong_confs.append(p.confidence)

    brier_score = brier_total / total
    log_loss_val = log_loss_total / total

    # --- Per-season accuracy (Requirement 6.2) ---
    season_correct: dict[int, int] = {}
    season_total: dict[int, int] = {}
    for p, season, _ in all_preds:
        season_total[season] = season_total.get(season, 0) + 1
        if p.correct:
            season_correct[season] = season_correct.get(season, 0) + 1

    per_season: dict[int, float] = {
        s: round(season_correct.get(s, 0) / season_total[s], 4)
        for s in sorted(season_total)
    }

    # --- Per-team accuracy (Requirement 6.3) ---
    # A game counts for both the home team and the away team
    team_correct: dict[str, int] = {}
    team_total: dict[str, int] = {}
    for p, _, _ in all_preds:
        for team in (p.home_team, p.away_team):
            team_total[team] = team_total.get(team, 0) + 1
            if p.correct:
                team_correct[team] = team_correct.get(team, 0) + 1

    per_team: dict[str, float] = {
        t: round(team_correct.get(t, 0) / team_total[t], 4)
        for t in sorted(team_total, key=lambda t: team_correct.get(t, 0) / team_total[t], reverse=True)
    }

    # --- Regular season vs finals split (Requirement 6.4) ---
    reg_preds = [(p, s, r) for p, s, r in all_preds if r < _FINALS_START_ROUND]
    fin_preds = [(p, s, r) for p, s, r in all_preds if r >= _FINALS_START_ROUND]

    regular_season_accuracy = (
        sum(1 for p, _, _ in reg_preds if p.correct) / len(reg_preds)
        if reg_preds else 0.0
    )
    finals_accuracy = (
        sum(1 for p, _, _ in fin_preds if p.correct) / len(fin_preds)
        if fin_preds else 0.0
    )

    summary = BacktestSummary(
        overall_accuracy=round(overall_accuracy, 4),
        brier_score=round(brier_score, 4),
        log_loss=round(log_loss_val, 4),
        per_season=per_season,
        per_team=per_team,
        regular_season_accuracy=round(regular_season_accuracy, 4),
        finals_accuracy=round(finals_accuracy, 4),
        total_games=total,
        # Legacy fields
        correct=correct_count,
        accuracy_pct=round(100.0 * overall_accuracy, 2),
        avg_confidence_when_correct=round(
            sum(correct_confs) / len(correct_confs), 4
        ) if correct_confs else 0.0,
        avg_confidence_when_wrong=round(
            sum(wrong_confs) / len(wrong_confs), 4
        ) if wrong_confs else 0.0,
    )

    print_backtest_summary(summary)

    if output_path is not None:
        _write_summary_json(summary, output_path)

    return summary


def print_backtest_summary(summary: BacktestSummary) -> None:
    """Print a formatted summary table to the console (Requirement 6.5)."""
    sep = "=" * 52
    print(sep)
    print("  BACKTEST SUMMARY")
    print(sep)
    print(f"  Total games evaluated : {summary.total_games}")
    print(f"  Overall accuracy      : {summary.overall_accuracy:.1%}")
    print(f"  Brier score           : {summary.brier_score:.4f}  (random=0.25)")
    print(f"  Log-loss              : {summary.log_loss:.4f}")
    print(f"  Regular season acc.   : {summary.regular_season_accuracy:.1%}")
    finals_str = (
        f"{summary.finals_accuracy:.1%}"
        if summary.finals_accuracy > 0.0
        else "n/a (no finals data)"
    )
    print(f"  Finals accuracy       : {finals_str}")

    if summary.per_season:
        print()
        print("  Per-season accuracy:")
        for season, acc in sorted(summary.per_season.items()):
            print(f"    {season}: {acc:.1%}")

    if summary.per_team:
        print()
        print("  Per-team accuracy (sorted by accuracy):")
        for team, acc in summary.per_team.items():
            print(f"    {team:<22} {acc:.1%}")

    print(sep)


def _write_summary_json(summary: BacktestSummary, path: Path) -> None:
    """Serialise *summary* to JSON at *path*, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "overall_accuracy": summary.overall_accuracy,
        "brier_score": summary.brier_score,
        "log_loss": summary.log_loss,
        "regular_season_accuracy": summary.regular_season_accuracy,
        "finals_accuracy": summary.finals_accuracy,
        "total_games": summary.total_games,
        "correct": summary.correct,
        "accuracy_pct": summary.accuracy_pct,
        "per_season": {str(k): v for k, v in summary.per_season.items()},
        "per_team": summary.per_team,
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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
