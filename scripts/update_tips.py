"""Pipeline entrypoint for baked tips generation.

Orchestrates the full AI-DLC loop:
1. Load historical data + build/update ELO ratings
2. Run ensemble model on fixtures
3. Serialize and write baked JSON artifacts
4. Optionally evaluate past predictions and run backtests
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.lib.fetch_data import fetch_ladder, fetch_round_fixtures, load_seed_fixtures, load_seed_ladder, scrape_fixtures_html
from scripts.lib.github_commit import GitHubConfig, commit_baked_files
from scripts.lib.model import run_model
from scripts.lib.serialize import build_ladder_payload, build_last_update_payload, build_round_payload


def _write_json(path: Path, payload: dict) -> str:
    content = json.dumps(payload, indent=2) + "\n"
    path.write_text(content, encoding="utf-8")
    return content


def _utc_date_stamp() -> str:
    return datetime.now(tz=timezone.utc).date().isoformat()


def _write_archive_snapshot(round_payload: dict) -> None:
    round_number = int(round_payload.get("round", 0) or 0)
    if round_number <= 0:
        return
    archive_dir = Path("data/archive")
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_date_stamp()
    _write_json(archive_dir / f"{stamp}_round_{round_number}.json", round_payload)
    _write_json(archive_dir / f"round_{round_number}.json", round_payload)


def _determine_current_round(season: int, max_round: int = 30) -> int:
    """Best-effort: find first round with any non-finished game."""
    for candidate in range(1, max_round + 1):
        try:
            fixtures = fetch_round_fixtures(season=season, round_number=candidate)
        except Exception:
            continue
        if not fixtures:
            continue
        if any(f.status != "finished" for f in fixtures):
            return candidate
    return 1


# ---------------------------------------------------------------------------
# ELO / historical data integration
# ---------------------------------------------------------------------------

def _ensure_elo_ratings(force_retrain: bool = False) -> None:
    """Load or build ELO ratings from historical data.

    Saves updated ratings to ``data/elo_ratings.json``.
    Non-fatal: if modules are unavailable the pipeline continues without ELO.
    """
    try:
        from scripts.lib.elo_ratings import EloEngine, build_elo_from_history
        from scripts.lib.historical_data import load_all_history
    except ImportError:
        return

    elo_path = Path("data/elo_ratings.json")

    if not force_retrain and elo_path.is_file():
        # Ratings already exist; model.py will load them at predict time
        return

    history = load_all_history()
    if not history:
        return

    print(f"Building ELO from {len(history)} historical games...")
    engine = build_elo_from_history(history)
    engine.save(elo_path)

    # Print top 5 ratings for verification
    ratings = engine.get_ratings()
    ranked = sorted(ratings.values(), key=lambda r: r.rating, reverse=True)
    for r in ranked[:5]:
        print(f"  {r.team}: {r.rating:.0f} ({r.games_played} games)")


# ---------------------------------------------------------------------------
# Post-round evaluation
# ---------------------------------------------------------------------------

def _run_evaluation(season: int) -> None:
    """Evaluate model performance against completed rounds.

    Non-fatal: logs results but does not block the pipeline.
    """
    try:
        from scripts.lib.historical_data import load_all_history
        from scripts.lib.model_monitor import ModelPerformance
    except ImportError:
        print("Evaluation skipped (modules not available)")
        return

    monitor = ModelPerformance()
    monitor.load()

    history = load_all_history()
    if not history:
        print("Evaluation skipped (no historical data)")
        return

    # Load archive data to find predictions vs results
    archive_dir = Path("data/archive")
    if not archive_dir.is_dir():
        print("Evaluation skipped (no archive directory)")
        return

    evaluated_rounds = 0
    for path in sorted(archive_dir.glob("round_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        rnd = payload.get("round", 0)
        games = payload.get("games", [])

        # Only evaluate rounds with both predictions and results
        has_predictions = any(g.get("tipTeam") not in (None, "N/A") for g in games)
        has_results = any(g.get("actualWinner") for g in games)
        if not has_predictions or not has_results:
            continue

        monitor.record_round(
            season=payload.get("season", season),
            round_number=rnd,
            predictions=games,
            results=games,
        )
        evaluated_rounds += 1

    if evaluated_rounds > 0:
        monitor.save()
        rolling = monitor.get_rolling_accuracy()
        drift = monitor.detect_drift()
        print(f"Evaluated {evaluated_rounds} rounds. Rolling accuracy: {rolling:.1%}")
        if drift:
            print("⚠️  Model drift detected — consider retraining with --retrain")
    else:
        print("No rounds with both predictions and results available for evaluation")


# ---------------------------------------------------------------------------
# Backtesting
# ---------------------------------------------------------------------------

def _run_backtest() -> None:
    """Run walk-forward backtesting and print summary."""
    try:
        from scripts.lib.backtester import compare_to_baselines, run_backtest, summarize_backtest
        from scripts.lib.historical_data import load_all_history
    except ImportError:
        print("Backtesting skipped (modules not available)")
        return

    history = load_all_history()
    if len(history) < 32:
        print(f"Backtesting skipped (only {len(history)} games, need at least 32)")
        return

    print(f"Running walk-forward backtest on {len(history)} games...")
    results = run_backtest(history)
    if not results:
        print("No rounds available for backtesting")
        return

    summary = summarize_backtest(results)
    baselines = compare_to_baselines(history)

    print(f"\n{'='*50}")
    print(f"BACKTEST SUMMARY")
    print(f"{'='*50}")
    print(f"Games evaluated:    {summary.total_games}")
    print(f"Correct:            {summary.correct}")
    print(f"Accuracy:           {summary.accuracy_pct:.1f}%")
    print(f"Brier score:        {summary.brier_score:.4f}")
    print(f"Avg conf (correct): {summary.avg_confidence_when_correct:.3f}")
    print(f"Avg conf (wrong):   {summary.avg_confidence_when_wrong:.3f}")
    print(f"\nBaselines:")
    print(f"  Always home team: {baselines.get('always_home', 0):.1f}%")
    print(f"  Random:           {baselines.get('random', 50):.1f}%")
    print(f"{'='*50}\n")


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def run_pipeline(round_number: int, season: int, model_version: str) -> tuple[dict, dict, dict]:
    try:
        fixtures = fetch_round_fixtures(season=season, round_number=round_number)
        if not fixtures:
            fixtures = scrape_fixtures_html(season=season, round_number=round_number)
    except Exception:
        fixtures = load_seed_fixtures()

    if not fixtures:
        fixtures = load_seed_fixtures()

    tips = run_model(fixtures)
    try:
        seed_ladder = fetch_ladder(season=season)
    except Exception:
        seed_ladder = load_seed_ladder()
    round_payload = build_round_payload(
        tips=tips, round_number=round_number, season=season, model_version=model_version
    )
    ladder_payload = build_ladder_payload(seed_ladder=seed_ladder, season=season, round_number=round_number)
    update_payload = build_last_update_payload(source="github-actions")
    return round_payload, update_payload, ladder_payload


def _commit_if_configured(round_content: str, update_content: str, ladder_content: str) -> str:
    token = os.getenv("GITHUB_BOT_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    branch = os.getenv("GITHUB_BRANCH", "main")
    bot_name = os.getenv("GITHUB_BOT_NAME", "tipping-bot[bot]")
    bot_email = os.getenv("GITHUB_BOT_EMAIL", "tipping-bot@users.noreply.github.com")
    if not token or not repo:
        return "skipped (missing GITHUB_BOT_TOKEN or GITHUB_REPO)"

    config = GitHubConfig(token=token, repo=repo, branch=branch, bot_name=bot_name, bot_email=bot_email)
    return commit_baked_files(
        config=config,
        files={
            "data/current_round_tips.json": round_content,
            "data/last_update.json": update_content,
            "data/ladder.json": ladder_content,
        },
        message="chore(data): refresh baked round tips",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and optionally commit baked tips data.")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads but do not write files.")
    parser.add_argument("--write", action="store_true", help="Write generated JSON files to data/.")
    parser.add_argument("--commit", action="store_true", help="Commit baked files through GitHub API.")
    parser.add_argument("--round", default="current", dest="round_number", help="Round number, or 'current'.")
    parser.add_argument("--season", type=int, default=2026, help="Season year.")
    parser.add_argument("--model-version", default="ensemble-v2", help="Model version tag.")
    parser.add_argument("--future-rounds", type=int, default=5, help="Generate N future rounds into data/archive/.")
    parser.add_argument(
        "--archive-through",
        type=int,
        default=0,
        help="Write and archive every round from 1..N in one run.",
    )
    parser.add_argument("--retrain", action="store_true", help="Force ELO rebuild from historical data.")
    parser.add_argument("--evaluate", action="store_true", help="Run post-round model evaluation.")
    parser.add_argument("--backtest", action="store_true", help="Run walk-forward backtesting.")
    args = parser.parse_args()

    # --- Evaluation-only mode ---
    if args.evaluate and not args.write and not args.dry_run:
        _run_evaluation(season=args.season)
        return

    # --- Backtest-only mode ---
    if args.backtest:
        _ensure_elo_ratings(force_retrain=args.retrain)
        _run_backtest()
        return

    # --- Pre-predict: ensure ELO ratings are available ---
    _ensure_elo_ratings(force_retrain=args.retrain)

    # --- Retrain-only mode ---
    if args.retrain and not args.write and not args.dry_run:
        print("ELO retrain complete.")
        return

    resolved_round: int
    if isinstance(args.round_number, str) and args.round_number.lower().strip() == "current":
        resolved_round = _determine_current_round(season=args.season)
    else:
        resolved_round = int(args.round_number)

    rounds = (
        list(range(1, args.archive_through + 1))
        if args.archive_through > 0
        else [resolved_round]
    )

    last_round_content = ""
    last_update_content = ""
    last_ladder_content = ""
    for round_number in rounds:
        round_payload, update_payload, ladder_payload = run_pipeline(
            round_number=round_number,
            season=args.season,
            model_version=args.model_version,
        )
        round_content = json.dumps(round_payload, indent=2) + "\n"
        update_content = json.dumps(update_payload, indent=2) + "\n"
        ladder_content = json.dumps(ladder_payload, indent=2) + "\n"
        last_round_content = round_content
        last_update_content = update_content
        last_ladder_content = ladder_content

        if args.dry_run:
            print(round_content)
            print(update_content)
            print(ladder_content)
            continue

        if args.write:
            _write_json(Path("data/current_round_tips.json"), round_payload)
            _write_json(Path("data/last_update.json"), update_payload)
            _write_json(Path("data/ladder.json"), ladder_payload)
            _write_archive_snapshot(round_payload)
            if args.archive_through > 0:
                continue

            if args.future_rounds > 0:
                for future_round in range(round_number + 1, round_number + args.future_rounds + 1):
                    try:
                        future_payload, _, _ = run_pipeline(
                            round_number=future_round,
                            season=args.season,
                            model_version=args.model_version,
                        )
                    except Exception:
                        break
                    if not future_payload.get("games"):
                        break
                    _write_archive_snapshot(future_payload)

    if args.dry_run:
        return

    if args.commit:
        result = _commit_if_configured(
            round_content=last_round_content,
            update_content=last_update_content,
            ladder_content=last_ladder_content,
        )
        print(f"commit_result={result}")


if __name__ == "__main__":
    main()
