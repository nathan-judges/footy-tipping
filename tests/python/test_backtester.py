"""Tests for the walk-forward backtester."""

from scripts.lib.backtester import (
    BacktestResult,
    BacktestSummary,
    compare_to_baselines,
    run_backtest,
    summarize_backtest,
)
from scripts.lib.historical_data import MatchResult, load_from_archive


def _make_results() -> list[MatchResult]:
    """Generate a minimal synthetic dataset for backtesting."""
    results = []
    teams = [
        ("Panthers", "Dragons"), ("Storm", "Eels"),
        ("Broncos", "Sharks"), ("Warriors", "Knights"),
    ]
    for rnd in range(1, 6):
        for i, (home, away) in enumerate(teams):
            # Alternate winners for variety
            if rnd % 2 == 0:
                h_score, a_score = 12, 20
                winner = away
            else:
                h_score, a_score = 24, 10
                winner = home
            results.append(MatchResult(
                season=2026,
                round_number=rnd,
                game_id=f"2026-r{rnd:02d}-g{i+1:02d}",
                home_team=home,
                away_team=away,
                venue="Test Stadium",
                home_score=h_score,
                away_score=a_score,
                winner=winner,
                margin=abs(h_score - a_score),
                kickoff_at=f"2026-03-{rnd*7:02d}T09:00:00Z",
            ))
    return results


def test_run_backtest_produces_results() -> None:
    results = _make_results()
    bt = run_backtest(results, start_season=2026, start_round=3)
    assert len(bt) > 0
    for r in bt:
        assert isinstance(r, BacktestResult)
        assert 0.0 <= r.accuracy <= 1.0


def test_summarize_backtest_accuracy_range() -> None:
    results = _make_results()
    bt = run_backtest(results, start_season=2026, start_round=3)
    summary = summarize_backtest(bt)
    assert isinstance(summary, BacktestSummary)
    assert 0.0 <= summary.accuracy_pct <= 100.0
    assert summary.total_games > 0


def test_compare_to_baselines() -> None:
    results = _make_results()
    baselines = compare_to_baselines(results)
    assert "always_home" in baselines
    assert "random" in baselines
    assert baselines["random"] == 50.0
    assert 0 <= baselines["always_home"] <= 100


def test_run_backtest_on_archive_data() -> None:
    """Run backtest against actual archive rounds if available."""
    from pathlib import Path
    archive_dir = Path("data/archive")
    if not archive_dir.is_dir():
        return  # Skip if no archive data

    history = load_from_archive(archive_dir)
    if len(history) < 32:
        return  # Not enough data

    bt = run_backtest(history, start_season=2026, start_round=4)
    # We should get at least some results
    if bt:
        summary = summarize_backtest(bt)
        assert summary.total_games > 0
        assert 0.0 <= summary.accuracy_pct <= 100.0
