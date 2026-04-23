# footy-tipping

Serverless-first NRL tipping app using baked JSON data, Next.js, GitHub, and Vercel.

Current features:
- Model tips with round-level `marginGameId` suggestion.
- Ladder view from baked `data/ladder.json`.
- Local picks stored in browser `localStorage` (winner picks + margin game/value).
- Past rounds: completed rounds show final scores and accuracy for model + your picks (when results are present in baked data).
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

### Fetching live NRL data

The Python pipeline now attempts to pull fixtures and ladder data directly from `nrl.com`:

- `python scripts/update_tips.py --write --round 8 --season 2026`
- `npm run archive:snapshot`

To backfill multiple rounds in one command:

- `python scripts/update_tips.py --write --season 2026 --archive-through 8`

If the NRL API is temporarily unavailable, the pipeline falls back to checked-in seed data.

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

## Past rounds & accuracy

- Use the round selector to navigate to any archived round.
- For completed rounds (where baked snapshots include results), you will see:
  - final scores on each game
  - a ✓/✕ indicator for whether the model tip was correct
  - your saved picks and whether you were correct
  - a summary card at the top showing model and personal accuracy percentages
- Picks are saved locally per round (no login required).

## Docs

- Data freshness & confidence: `docs/data-freshness.md`
- 2026 season settings: `docs/season-2026.md`

### Tracking accuracy

- For completed rounds, the app displays:
  - model accuracy (how many winners the algorithm predicted correctly)
  - your accuracy (how many of your saved picks were correct)
- Game cards show a correctness indicator for model and your picks.
- All picks are saved locally in your browser.
