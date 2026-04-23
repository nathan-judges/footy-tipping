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
