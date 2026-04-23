"""Pipeline entrypoint for baked tips generation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.lib.fetch_data import load_seed_fixtures, load_seed_ladder
from scripts.lib.github_commit import GitHubConfig, commit_baked_files
from scripts.lib.model import run_model
from scripts.lib.serialize import build_ladder_payload, build_last_update_payload, build_round_payload


def _write_json(path: Path, payload: dict) -> str:
    content = json.dumps(payload, indent=2) + "\n"
    path.write_text(content, encoding="utf-8")
    return content


def run_pipeline(round_number: int, season: int, model_version: str) -> tuple[dict, dict, dict]:
    fixtures = load_seed_fixtures()
    tips = run_model(fixtures)
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
    parser.add_argument("--round", type=int, default=1, dest="round_number", help="Round number.")
    parser.add_argument("--season", type=int, default=2026, help="Season year.")
    parser.add_argument("--model-version", default="elo-odds-v1", help="Model version tag.")
    args = parser.parse_args()

    round_payload, update_payload, ladder_payload = run_pipeline(
        round_number=args.round_number, season=args.season, model_version=args.model_version
    )

    round_content = json.dumps(round_payload, indent=2) + "\n"
    update_content = json.dumps(update_payload, indent=2) + "\n"
    ladder_content = json.dumps(ladder_payload, indent=2) + "\n"

    if args.dry_run:
        print(round_content)
        print(update_content)
        print(ladder_content)
        return

    if args.write:
        _write_json(Path("data/current_round_tips.json"), round_payload)
        _write_json(Path("data/last_update.json"), update_payload)
        _write_json(Path("data/ladder.json"), ladder_payload)

    if args.commit:
        result = _commit_if_configured(
            round_content=round_content, update_content=update_content, ladder_content=ladder_content
        )
        print(f"commit_result={result}")


if __name__ == "__main__":
    main()
