# Architecture Decisions

## Baked Data vs Database

- We serve core round tips and ladder data from committed JSON artifacts in `data/`.
- This keeps runtime simple, fast, and cheap on Vercel because read paths are static.
- We defer database adoption until one of these triggers appears:
  - authenticated multi-user picks
  - multiple intra-day model refreshes
  - historical analytics and queryable trend reporting

## Split Compute and Serve

- Model/data refresh runs in GitHub Actions (`update-tips.yml`).
- User-facing API and UI run in Vercel with edge-safe routes.
- This avoids heavy compute in request paths and keeps production failure domains narrow.

## Live Override Polling

- `src/app/api/live-tips/route.ts` is JSON-first against NRL match-centre APIs.
- If API discovery fails, it falls back to HTML/embedded payload parsing.
- Failures are soft: users still see baked tips when live scraping is unavailable.
