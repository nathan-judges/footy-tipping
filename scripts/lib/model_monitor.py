"""Continuous model performance monitoring.

Tracks per-round accuracy, detects performance drift, and persists
metrics to ``data/model_performance.json`` for the frontend dashboard.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class PerformanceRecord:
    """Performance metrics for a single round."""

    season: int
    round_number: int
    total_games: int = 0
    correct: int = 0
    accuracy: float = 0.0
    cumulative_accuracy: float = 0.0
    brier_score: float = 0.25
    high_confidence_total: int = 0
    high_confidence_correct: int = 0
    high_confidence_accuracy: float = 0.0


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------

_DEFAULT_PERFORMANCE_PATH = Path("data/model_performance.json")


class ModelPerformance:
    """Track and persist model performance metrics over time."""

    def __init__(self) -> None:
        self.records: list[PerformanceRecord] = []

    def record_round(
        self,
        season: int,
        round_number: int,
        predictions: list[dict],
        results: list[dict],
    ) -> PerformanceRecord:
        """Record performance for a completed round.

        *predictions* and *results* should be lists of dicts with at least
        ``gameId``, ``tipTeam`` (predictions) and ``actualWinner`` (results).
        """
        result_map = {r.get("gameId", ""): r for r in results}

        total = 0
        correct = 0
        brier_total = 0.0
        hc_total = 0
        hc_correct = 0

        for pred in predictions:
            game_id = pred.get("gameId", "")
            actual = result_map.get(game_id, {})
            actual_winner = actual.get("actualWinner")
            if not actual_winner:
                continue

            total += 1
            tip = pred.get("tipTeam", "")
            confidence = float(pred.get("confidence", 0.5))

            is_correct = tip == actual_winner
            if is_correct:
                correct += 1

            # Brier score contribution
            outcome = 1.0 if is_correct else 0.0
            brier_total += (confidence - outcome) ** 2

            # High confidence tracking (> 70%)
            if confidence > 0.70:
                hc_total += 1
                if is_correct:
                    hc_correct += 1

        accuracy = correct / total if total > 0 else 0.0
        brier = brier_total / total if total > 0 else 0.25
        hc_accuracy = hc_correct / hc_total if hc_total > 0 else 0.0

        # Cumulative accuracy across all recorded rounds
        all_total = sum(r.total_games for r in self.records) + total
        all_correct = sum(r.correct for r in self.records) + correct
        cumulative = all_correct / all_total if all_total > 0 else 0.0

        record = PerformanceRecord(
            season=season,
            round_number=round_number,
            total_games=total,
            correct=correct,
            accuracy=round(accuracy, 4),
            cumulative_accuracy=round(cumulative, 4),
            brier_score=round(brier, 4),
            high_confidence_total=hc_total,
            high_confidence_correct=hc_correct,
            high_confidence_accuracy=round(hc_accuracy, 4),
        )

        # Replace existing record for same round if present
        self.records = [
            r for r in self.records
            if not (r.season == season and r.round_number == round_number)
        ]
        self.records.append(record)
        self.records.sort(key=lambda r: (r.season, r.round_number))

        return record

    def get_rolling_accuracy(self, window: int = 5) -> float:
        """Rolling accuracy over the last *window* rounds."""
        recent = self.records[-window:]
        if not recent:
            return 0.0
        total = sum(r.total_games for r in recent)
        correct = sum(r.correct for r in recent)
        return correct / total if total > 0 else 0.0

    def detect_drift(self, threshold: float = 0.45) -> bool:
        """Return ``True`` if rolling accuracy drops below *threshold*.

        This indicates the model may need retraining or investigation.
        """
        rolling = self.get_rolling_accuracy()
        return rolling < threshold and len(self.records) >= 3

    def save(self, path: Path | None = None) -> None:
        """Persist performance records to JSON."""
        path = path or _DEFAULT_PERFORMANCE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(r) for r in self.records]
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def load(self, path: Path | None = None) -> None:
        """Load performance records from JSON."""
        path = path or _DEFAULT_PERFORMANCE_PATH
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, list):
            return
        self.records = []
        for entry in data:
            try:
                self.records.append(PerformanceRecord(**entry))
            except (TypeError, KeyError):
                continue
