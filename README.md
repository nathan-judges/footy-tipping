# footy-tipping

Serverless-first NRL tipping app using baked JSON data, Next.js, GitHub, and Vercel.

Current features:
- Model tips with round-level `marginGameId` suggestion.
- Ladder view from baked `data/ladder.json`.
- Optional local "My Picks" state stored in browser `localStorage`.
- Edge endpoints for health, ladder, and live tip checks.

## Local development

1. Install dependencies:
   - `npm install`
2. Start the app:
   - `npm run dev`
3. Run checks:
   - `npm run lint`
   - `npm run typecheck`
   - `npm test`
   - `npm run check`
   - `npm run check:all`

## Consistency commands

For CI-aligned local checks:

- `npm run check` (lint + typecheck + frontend tests)
- `npm run check:all` (everything in `check` plus Python tests)

Equivalent Make targets:

- `make check`
- `make check-all`

## Environment variables

Copy `.env.example` to `.env.local` and fill values:

- `GITHUB_BOT_TOKEN`
- `GITHUB_REPO`
- `GITHUB_BRANCH`
- `ODDS_API_KEY` (optional)

## Pipeline local dry-run

The data pipeline entrypoint will support dry-run mode:

- `python scripts/update_tips.py --dry-run`

This command should validate and print baked output locally without committing.

To regenerate local baked files:

- `python scripts/update_tips.py --write`

To run commit flow (requires bot env vars):

- `python scripts/update_tips.py --write --commit`

## Python tests

- `pip install -r requirements.txt`
- `pytest tests/python/`

## Scheduled updates

- GitHub Actions workflow: `.github/workflows/update-tips.yml`
- Weekly schedule generates `data/current_round_tips.json` and `data/last_update.json`.
- Manual `workflow_dispatch` supports `dry_run=true` for safe verification.
- PR checks run via `.github/workflows/ci.yml`.

## Archive page

- Route: `/archive`
- Data source: committed JSON snapshots in `data/archive/*.json` plus current round fallback from `data/current_round_tips.json`.
- Snapshot format should match `current_round_tips.json`.
