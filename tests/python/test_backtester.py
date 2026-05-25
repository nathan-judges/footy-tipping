"""Tests for the walk-forward backtester."""

import json
import math
from pathlib import Path

import pytest

from scripts.lib.backtester import (
    BacktestResult,
    BacktestSummary,
    GamePrediction,
    _safe_log_loss,
    compare_to_baselines,
    print_backtest_summary,
    run_backtest,
    summarize_backtest,
)
from scripts.lib.historical_data import MatchResult, load_from_archive


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_results(
    seasons: list[int] | None = None,
    rounds_per_season: int = 5,
    games_per_round: int = 4,
) -> list[MatchResult]:
    """Generate a minimal synthetic dataset for backtesting."""
    if seasons is None:
        seasons = [2026]

    teams = [
        ("Panthers", "Dragons"),
        ("Storm", "Eels"),
        ("Broncos", "Sharks"),
        ("Warriors", "Knights"),
    ][:games_per_round]

    results = []
    for season in seasons:
        for rnd in range(1, rounds_per_season + 1):
            for i, (home, away) in enumerate(teams):
                if rnd % 2 == 0:
                    h_score, a_score = 12, 20
                    winner = away
                else:
                    h_score, a_score = 24, 10
                    winner = home
                results.append(MatchResult(
                    season=season,
                    round_number=rnd,
                    game_id=f"{season}-r{rnd:02d}-g{i+1:02d}",
                    home_team=home,
                    away_team=away,
                    venue="Test Stadium",
                    home_score=h_score,
                    away_score=a_score,
                    winner=winner,
                    margin=abs(h_score - a_score),
                    kickoff_at=f"{season}-03-{rnd*7:02d}T09:00:00Z",
                ))
    return results


def _make_game_prediction(
    *,
    home_team: str = "Panthers",
    away_team: str = "Storm",
    correct: bool = True,
    confidence: float = 0.7,
    season: int = 2026,
    round_number: int = 5,
    game_id: str | None = None,
) -> tuple[GamePrediction, int, int]:
    """Build a (GamePrediction, season, round) tuple for direct testing."""
    gid = game_id or f"{season}-r{round_number:02d}-g01"
    winner = home_team if correct else away_team
    pred = GamePrediction(
        game_id=gid,
        home_team=home_team,
        away_team=away_team,
        predicted_winner=winner,
        actual_winner=winner,
        confidence=confidence,
        correct=correct,
    )
    return pred, season, round_number


def _make_backtest_result(
    season: int,
    round_number: int,
    predictions: list[GamePrediction],
) -> BacktestResult:
    correct = sum(1 for p in predictions if p.correct)
    return BacktestResult(
        season=season,
        round_number=round_number,
        total_games=len(predictions),
        correct_predictions=correct,
        accuracy=correct / len(predictions) if predictions else 0.0,
        predictions=predictions,
    )


# ---------------------------------------------------------------------------
# run_backtest
# ---------------------------------------------------------------------------

def test_run_backtest_produces_results() -> None:
    results = _make_results()
    bt = run_backtest(results, start_season=2026, start_round=3)
    assert len(bt) > 0
    for r in bt:
        assert isinstance(r, BacktestResult)
        assert 0.0 <= r.accuracy <= 1.0


# ---------------------------------------------------------------------------
# BacktestSummary dataclass fields
# ---------------------------------------------------------------------------

def test_backtest_summary_has_required_fields() -> None:
    """BacktestSummary must expose all fields required by Requirement 6."""
    summary = BacktestSummary(
        overall_accuracy=0.65,
        brier_score=0.22,
        log_loss=0.55,
        per_season={2026: 0.65},
        per_team={"Panthers": 0.70},
        regular_season_accuracy=0.66,
        finals_accuracy=0.60,
        total_games=100,
    )
    assert summary.overall_accuracy == 0.65
    assert summary.brier_score == 0.22
    assert summary.log_loss == 0.55
    assert summary.per_season == {2026: 0.65}
    assert summary.per_team == {"Panthers": 0.70}
    assert summary.regular_season_accuracy == 0.66
    assert summary.finals_accuracy == 0.60
    assert summary.total_games == 100


# ---------------------------------------------------------------------------
# summarize_backtest — metric calculations with known outcomes
# ---------------------------------------------------------------------------

def test_summarize_empty_results() -> None:
    """Empty results should return a zero-game summary without crashing."""
    summary = summarize_backtest([])
    assert summary.total_games == 0
    assert summary.overall_accuracy == 0.0
    assert summary.brier_score == 0.25  # random baseline
    assert summary.per_season == {}
    assert summary.per_team == {}
    assert summary.regular_season_accuracy == 0.0
    assert summary.finals_accuracy == 0.0


def test_summarize_perfect_accuracy() -> None:
    """All-correct predictions → accuracy=1.0, brier_score=0.0."""
    preds = [
        GamePrediction("g1", "Panthers", "Storm", "Panthers", "Panthers", 0.8, True),
        GamePrediction("g2", "Broncos", "Eels", "Broncos", "Broncos", 0.75, True),
    ]
    result = _make_backtest_result(2026, 5, preds)
    summary = summarize_backtest([result])

    assert summary.total_games == 2
    assert summary.overall_accuracy == 1.0
    assert summary.brier_score == pytest.approx(
        ((0.8 - 1.0) ** 2 + (0.75 - 1.0) ** 2) / 2, abs=1e-3
    )
    assert summary.correct == 2
    assert summary.accuracy_pct == 100.0


def test_summarize_zero_accuracy() -> None:
    """All-wrong predictions → accuracy=0.0."""
    preds = [
        GamePrediction("g1", "Panthers", "Storm", "Panthers", "Storm", 0.6, False),
        GamePrediction("g2", "Broncos", "Eels", "Broncos", "Eels", 0.55, False),
    ]
    result = _make_backtest_result(2026, 5, preds)
    summary = summarize_backtest([result])

    assert summary.overall_accuracy == 0.0
    assert summary.correct == 0


def test_summarize_brier_score_known_values() -> None:
    """Brier score = mean((confidence - outcome)^2) with known inputs."""
    # 1 correct at 0.8, 1 wrong at 0.6
    # Brier = ((0.8-1)^2 + (0.6-0)^2) / 2 = (0.04 + 0.36) / 2 = 0.20
    preds = [
        GamePrediction("g1", "A", "B", "A", "A", 0.8, True),
        GamePrediction("g2", "C", "D", "C", "D", 0.6, False),
    ]
    result = _make_backtest_result(2026, 5, preds)
    summary = summarize_backtest([result])

    assert summary.brier_score == pytest.approx(0.20, abs=1e-6)


def test_summarize_log_loss_known_values() -> None:
    """Log-loss = -mean(y*log(p) + (1-y)*log(1-p)) with known inputs."""
    p1, p2 = 0.8, 0.6
    expected_ll = -(math.log(p1) + math.log(1.0 - p2)) / 2
    preds = [
        GamePrediction("g1", "A", "B", "A", "A", p1, True),
        GamePrediction("g2", "C", "D", "C", "D", p2, False),
    ]
    result = _make_backtest_result(2026, 5, preds)
    summary = summarize_backtest([result])

    assert summary.log_loss == pytest.approx(expected_ll, abs=1e-4)


def test_summarize_overall_accuracy_range() -> None:
    """overall_accuracy must be in [0.0, 1.0]."""
    results = _make_results()
    bt = run_backtest(results, start_season=2026, start_round=3)
    summary = summarize_backtest(bt)
    assert 0.0 <= summary.overall_accuracy <= 1.0


def test_summarize_legacy_accuracy_pct_consistent() -> None:
    """accuracy_pct should equal overall_accuracy * 100."""
    preds = [
        GamePrediction("g1", "A", "B", "A", "A", 0.7, True),
        GamePrediction("g2", "C", "D", "C", "D", 0.6, False),
        GamePrediction("g3", "E", "F", "E", "E", 0.65, True),
    ]
    result = _make_backtest_result(2026, 5, preds)
    summary = summarize_backtest([result])

    assert summary.accuracy_pct == pytest.approx(summary.overall_accuracy * 100, abs=0.01)


# ---------------------------------------------------------------------------
# Per-season breakdown (Requirement 6.2)
# ---------------------------------------------------------------------------

def test_per_season_keys_match_input_seasons() -> None:
    """per_season dict must contain exactly the seasons present in results."""
    preds_2025 = [GamePrediction("g1", "A", "B", "A", "A", 0.7, True)]
    preds_2026 = [GamePrediction("g2", "C", "D", "C", "D", 0.6, False)]

    results = [
        _make_backtest_result(2025, 5, preds_2025),
        _make_backtest_result(2026, 5, preds_2026),
    ]
    summary = summarize_backtest(results)

    assert set(summary.per_season.keys()) == {2025, 2026}


def test_per_season_accuracy_values_in_range() -> None:
    """All per-season accuracy values must be in [0.0, 1.0]."""
    results = _make_results(seasons=[2024, 2025, 2026])
    bt = run_backtest(results, start_season=2024, start_round=3)
    summary = summarize_backtest(bt)

    for season, acc in summary.per_season.items():
        assert 0.0 <= acc <= 1.0, f"Season {season} accuracy {acc} out of range"


def test_per_season_correct_calculation() -> None:
    """Per-season accuracy should match manual calculation."""
    # Season 2025: 2 correct out of 2 → 1.0
    preds_2025 = [
        GamePrediction("g1", "A", "B", "A", "A", 0.7, True),
        GamePrediction("g2", "C", "D", "C", "C", 0.65, True),
    ]
    # Season 2026: 1 correct out of 2 → 0.5
    preds_2026 = [
        GamePrediction("g3", "E", "F", "E", "E", 0.7, True),
        GamePrediction("g4", "G", "H", "G", "H", 0.6, False),
    ]
    results = [
        _make_backtest_result(2025, 5, preds_2025),
        _make_backtest_result(2026, 5, preds_2026),
    ]
    summary = summarize_backtest(results)

    assert summary.per_season[2025] == pytest.approx(1.0, abs=1e-4)
    assert summary.per_season[2026] == pytest.approx(0.5, abs=1e-4)


# ---------------------------------------------------------------------------
# Per-team breakdown (Requirement 6.3)
# ---------------------------------------------------------------------------

def test_per_team_keys_include_all_teams() -> None:
    """per_team must include every team that appeared in any game."""
    preds = [
        GamePrediction("g1", "Panthers", "Storm", "Panthers", "Panthers", 0.7, True),
        GamePrediction("g2", "Broncos", "Eels", "Broncos", "Eels", 0.6, False),
    ]
    result = _make_backtest_result(2026, 5, preds)
    summary = summarize_backtest([result])

    assert "Panthers" in summary.per_team
    assert "Storm" in summary.per_team
    assert "Broncos" in summary.per_team
    assert "Eels" in summary.per_team


def test_per_team_accuracy_values_in_range() -> None:
    """All per-team accuracy values must be in [0.0, 1.0]."""
    results = _make_results()
    bt = run_backtest(results, start_season=2026, start_round=3)
    summary = summarize_backtest(bt)

    for team, acc in summary.per_team.items():
        assert 0.0 <= acc <= 1.0, f"Team {team} accuracy {acc} out of range"


def test_per_team_counts_both_home_and_away() -> None:
    """A team's accuracy should count games as both home and away."""
    # Panthers plays home in g1 (correct) and away in g2 (wrong)
    # → Panthers accuracy = 1/2 = 0.5
    preds = [
        GamePrediction("g1", "Panthers", "Storm", "Panthers", "Panthers", 0.7, True),
        GamePrediction("g2", "Broncos", "Panthers", "Broncos", "Panthers", 0.6, False),
    ]
    result = _make_backtest_result(2026, 5, preds)
    summary = summarize_backtest([result])

    assert summary.per_team["Panthers"] == pytest.approx(0.5, abs=1e-4)


def test_per_team_sorted_by_accuracy_descending() -> None:
    """per_team should be sorted from highest to lowest accuracy."""
    preds = [
        # TeamA: 2/2 = 1.0
        GamePrediction("g1", "TeamA", "TeamB", "TeamA", "TeamA", 0.8, True),
        GamePrediction("g2", "TeamA", "TeamC", "TeamA", "TeamA", 0.75, True),
        # TeamD: 0/2 = 0.0
        GamePrediction("g3", "TeamD", "TeamE", "TeamD", "TeamE", 0.6, False),
        GamePrediction("g4", "TeamD", "TeamF", "TeamD", "TeamF", 0.55, False),
    ]
    result = _make_backtest_result(2026, 5, preds)
    summary = summarize_backtest([result])

    accuracies = list(summary.per_team.values())
    assert accuracies == sorted(accuracies, reverse=True)


# ---------------------------------------------------------------------------
# Finals vs regular season split (Requirement 6.4)
# ---------------------------------------------------------------------------

def test_regular_season_accuracy_uses_rounds_1_to_27() -> None:
    """regular_season_accuracy should only count rounds < 28."""
    reg_preds = [GamePrediction("g1", "A", "B", "A", "A", 0.7, True)]
    fin_preds = [GamePrediction("g2", "C", "D", "C", "D", 0.6, False)]

    results = [
        _make_backtest_result(2026, 10, reg_preds),   # regular season
        _make_backtest_result(2026, 28, fin_preds),   # finals
    ]
    summary = summarize_backtest(results)

    assert summary.regular_season_accuracy == pytest.approx(1.0, abs=1e-4)
    assert summary.finals_accuracy == pytest.approx(0.0, abs=1e-4)


def test_finals_accuracy_uses_rounds_28_plus() -> None:
    """finals_accuracy should only count rounds >= 28."""
    reg_preds = [GamePrediction("g1", "A", "B", "A", "B", 0.6, False)]
    fin_preds = [
        GamePrediction("g2", "C", "D", "C", "C", 0.75, True),
        GamePrediction("g3", "E", "F", "E", "E", 0.8, True),
    ]
    results = [
        _make_backtest_result(2026, 15, reg_preds),   # regular season
        _make_backtest_result(2026, 29, fin_preds),   # finals
    ]
    summary = summarize_backtest(results)

    assert summary.regular_season_accuracy == pytest.approx(0.0, abs=1e-4)
    assert summary.finals_accuracy == pytest.approx(1.0, abs=1e-4)


def test_finals_accuracy_zero_when_no_finals_data() -> None:
    """finals_accuracy should be 0.0 when no finals rounds are present."""
    preds = [GamePrediction("g1", "A", "B", "A", "A", 0.7, True)]
    result = _make_backtest_result(2026, 5, preds)
    summary = summarize_backtest([result])

    assert summary.finals_accuracy == 0.0


def test_regular_season_accuracy_zero_when_only_finals() -> None:
    """regular_season_accuracy should be 0.0 when only finals rounds present."""
    preds = [GamePrediction("g1", "A", "B", "A", "A", 0.7, True)]
    result = _make_backtest_result(2026, 28, preds)
    summary = summarize_backtest([result])

    assert summary.regular_season_accuracy == 0.0
    assert summary.finals_accuracy == pytest.approx(1.0, abs=1e-4)


# ---------------------------------------------------------------------------
# JSON output (Requirement 6.5)
# ---------------------------------------------------------------------------

def test_summarize_writes_json_when_output_path_given(tmp_path: Path) -> None:
    """summarize_backtest should write a valid JSON file when output_path is set."""
    preds = [
        GamePrediction("g1", "Panthers", "Storm", "Panthers", "Panthers", 0.7, True),
        GamePrediction("g2", "Broncos", "Eels", "Broncos", "Eels", 0.6, False),
    ]
    result = _make_backtest_result(2026, 5, preds)
    output_file = tmp_path / "backtest_results.json"

    summarize_backtest([result], output_path=output_file)

    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert "overall_accuracy" in data
    assert "brier_score" in data
    assert "log_loss" in data
    assert "per_season" in data
    assert "per_team" in data
    assert "regular_season_accuracy" in data
    assert "finals_accuracy" in data
    assert "total_games" in data


def test_summarize_json_values_match_summary(tmp_path: Path) -> None:
    """JSON output values should match the returned BacktestSummary."""
    preds = [
        GamePrediction("g1", "A", "B", "A", "A", 0.8, True),
        GamePrediction("g2", "C", "D", "C", "D", 0.55, False),
    ]
    result = _make_backtest_result(2026, 5, preds)
    output_file = tmp_path / "results.json"

    summary = summarize_backtest([result], output_path=output_file)
    data = json.loads(output_file.read_text())

    assert data["overall_accuracy"] == pytest.approx(summary.overall_accuracy, abs=1e-6)
    assert data["brier_score"] == pytest.approx(summary.brier_score, abs=1e-6)
    assert data["total_games"] == summary.total_games


def test_summarize_creates_parent_dirs(tmp_path: Path) -> None:
    """summarize_backtest should create parent directories for output_path."""
    preds = [GamePrediction("g1", "A", "B", "A", "A", 0.7, True)]
    result = _make_backtest_result(2026, 5, preds)
    nested_path = tmp_path / "data" / "results" / "backtest.json"

    summarize_backtest([result], output_path=nested_path)

    assert nested_path.exists()


def test_summarize_no_output_when_path_is_none(tmp_path: Path) -> None:
    """No file should be written when output_path is None."""
    preds = [GamePrediction("g1", "A", "B", "A", "A", 0.7, True)]
    result = _make_backtest_result(2026, 5, preds)

    summarize_backtest([result], output_path=None)

    # Confirm nothing was written to tmp_path
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Console output (Requirement 6.5)
# ---------------------------------------------------------------------------

def test_print_backtest_summary_outputs_to_stdout(capsys: pytest.CaptureFixture) -> None:
    """print_backtest_summary should write a non-empty table to stdout."""
    summary = BacktestSummary(
        overall_accuracy=0.65,
        brier_score=0.22,
        log_loss=0.55,
        per_season={2026: 0.65},
        per_team={"Panthers": 0.70, "Storm": 0.60},
        regular_season_accuracy=0.66,
        finals_accuracy=0.60,
        total_games=100,
    )
    print_backtest_summary(summary)
    captured = capsys.readouterr()

    assert "BACKTEST SUMMARY" in captured.out
    assert "65.0%" in captured.out
    assert "Panthers" in captured.out
    assert "2026" in captured.out


def test_summarize_prints_to_stdout(capsys: pytest.CaptureFixture) -> None:
    """summarize_backtest should print the summary table automatically."""
    preds = [GamePrediction("g1", "A", "B", "A", "A", 0.7, True)]
    result = _make_backtest_result(2026, 5, preds)

    summarize_backtest([result])
    captured = capsys.readouterr()

    assert "BACKTEST SUMMARY" in captured.out


# ---------------------------------------------------------------------------
# _safe_log_loss helper
# ---------------------------------------------------------------------------

def test_safe_log_loss_correct_prediction() -> None:
    """Log-loss for a correct prediction at p=0.8 should be -log(0.8)."""
    expected = -math.log(0.8)
    assert _safe_log_loss(0.8, True) == pytest.approx(expected, abs=1e-10)


def test_safe_log_loss_wrong_prediction() -> None:
    """Log-loss for a wrong prediction at p=0.6 should be -log(1-0.6)."""
    expected = -math.log(0.4)
    assert _safe_log_loss(0.6, False) == pytest.approx(expected, abs=1e-10)


def test_safe_log_loss_clips_extreme_probabilities() -> None:
    """_safe_log_loss should not raise for p=0.0 or p=1.0."""
    # Should not raise
    _safe_log_loss(0.0, True)
    _safe_log_loss(1.0, False)
    _safe_log_loss(0.0, False)
    _safe_log_loss(1.0, True)


# ---------------------------------------------------------------------------
# compare_to_baselines (existing, kept for regression)
# ---------------------------------------------------------------------------

def test_compare_to_baselines() -> None:
    results = _make_results()
    baselines = compare_to_baselines(results)
    assert "always_home" in baselines
    assert "random" in baselines
    assert baselines["random"] == 50.0
    assert 0 <= baselines["always_home"] <= 100


# ---------------------------------------------------------------------------
# Integration: run_backtest + summarize_backtest
# ---------------------------------------------------------------------------

def test_run_and_summarize_integration() -> None:
    """Full pipeline: run_backtest → summarize_backtest should produce valid output."""
    results = _make_results()
    bt = run_backtest(results, start_season=2026, start_round=3)
    summary = summarize_backtest(bt)

    assert isinstance(summary, BacktestSummary)
    assert summary.total_games > 0
    assert 0.0 <= summary.overall_accuracy <= 1.0
    assert summary.brier_score >= 0.0
    assert summary.log_loss >= 0.0
    assert isinstance(summary.per_season, dict)
    assert isinstance(summary.per_team, dict)
    assert 0.0 <= summary.regular_season_accuracy <= 1.0
    assert 0.0 <= summary.finals_accuracy <= 1.0


def test_run_backtest_on_archive_data() -> None:
    """Run backtest against actual archive rounds if available."""
    archive_dir = Path("data/archive")
    if not archive_dir.is_dir():
        return  # Skip if no archive data

    history = load_from_archive(archive_dir)
    if len(history) < 32:
        return  # Not enough data

    bt = run_backtest(history, start_season=2026, start_round=4)
    if bt:
        summary = summarize_backtest(bt)
        assert summary.total_games > 0
        assert 0.0 <= summary.overall_accuracy <= 1.0
        assert summary.brier_score >= 0.0
        assert summary.log_loss >= 0.0
