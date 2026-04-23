## Data freshness & update confidence

This app serves **baked JSON** (checked into the repo) so users get fast, stable pages.

### What "Fresh" means

The header badge is computed from `data/last_update.json.lastSuccessfulUpdateAt`.

- **Fresh**: updated within the last **6 hours**
- **Stale**: older than 6 hours

The badge tooltip shows the last successful update timestamp and its source (eg `github-actions`).

### Future rounds

Future rounds are shown in the round selector, but may not have baked snapshots yet.
When a round is not baked you may still navigate to it, but the page will show a message indicating that no snapshot exists.

