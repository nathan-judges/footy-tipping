# Operations Runbook

## Scheduled update fails

1. Open GitHub Actions for `Update Baked Tips`.
2. Inspect workflow logs for API/auth failures.
3. Re-run with `workflow_dispatch` and `dry_run=true` first.
4. If dry-run succeeds, re-run without dry-run to publish.

## Data stale before game day

1. Ensure local env contains bot credentials.
2. Run:
   - `python3 scripts/update_tips.py --write --commit`
3. Confirm commit lands in default branch and Vercel deploys.

## Manually populate a new round

1. Generate a specific round and write baked files:
   - `python3 scripts/update_tips.py --write --round 8 --season 2026`
2. Snapshot the round into archive files:
   - `npm run archive:snapshot`
3. For initial backfill (for example rounds 1 through 8):
   - `python3 scripts/update_tips.py --write --season 2026 --archive-through 8`
4. Verify:
   - `data/current_round_tips.json` has multiple games for the target round
   - `data/archive/round_<N>.json` exists for each backfilled round

## NRL HTML/API shape changes

1. Check Vercel logs for `live-tips` error reasons.
2. Update selectors/parsing in `src/app/api/live-tips/route.ts`.
3. Test with:
   - `npm run dev`
   - `curl "http://localhost:3000/api/live-tips?gameId=<game-id>"`
4. Deploy and re-check edge logs.

## Bot commit conflict

1. Trigger workflow again; commit helper retries once automatically.
2. If repeated conflicts persist, run update on a clean latest `main`.
3. Confirm no branch protection rule blocks bot credentials.

## Adding final scores to an archived round

If the baked pipeline cannot fetch results reliably yet, you can add them manually for a completed round.

1. Locate the snapshot in `data/archive/`:
   - canonical: `data/archive/round_<N>.json`
   - dated: `data/archive/<YYYY-MM-DD>_round_<N>.json`
2. For each finished game, add:
   - `homeScore`
   - `awayScore`
   - optionally `actualWinner` and `actualMargin` (UI can derive these from scores if omitted)
3. Ensure the game `status` is `"finished"` for completed games.
4. Commit and push; Vercel will redeploy.
5. Verify the round page shows the summary card and per-game ✓/✕ indicators.

## Accuracy not showing for a completed round

1. Ensure the round's baked data includes `homeScore`, `awayScore`, and `actualWinner` fields.
2. If those fields are missing, re-run the pipeline for that round after scores are available:
   - `python scripts/update_tips.py --write --round 8 --season 2026`
   - `npm run archive:snapshot`
3. Commit and push the updated archive files.
