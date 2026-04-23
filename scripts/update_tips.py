"""Pipeline entrypoint for baked tips generation."""

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
    parser.add_argument("--model-version", default="elo-odds-v1", help="Model version tag.")
    parser.add_argument("--future-rounds", type=int, default=5, help="Generate N future rounds into data/archive/.")
    parser.add_argument(
        "--archive-through",
        type=int,
        default=0,
        help="Write and archive every round from 1..N in one run.",
    )
    args = parser.parse_args()

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
