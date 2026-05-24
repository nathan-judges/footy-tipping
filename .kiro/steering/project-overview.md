# Footy Tipping — Project Overview

## What this is
A serverless NRL tipping app. Data is baked into committed JSON files (`data/`), served statically via Next.js on Vercel. A Python pipeline (GitHub Actions) refreshes the baked data weekly.

## Stack
- **Frontend**: Next.js 15 (App Router), React 19, TypeScript strict, Tailwind v4, shadcn/ui primitives
- **Backend**: Edge API routes only (`src/app/api/`). No database.
- **Data pipeline**: Python 3.13, pytest, ELO ratings, ensemble model
- **Hosting**: Vercel (frontend) + GitHub Actions (data pipeline)

## Key data files
| File | Purpose |
|------|---------|
| `data/current_round_tips.json` | Current round tips + results when finished |
| `data/archive/round_N.json` | Canonical per-round snapshot |
| `data/archive/YYYY-MM-DD_round_N.json` | Dated snapshot (multiple per round OK) |
| `data/ladder.json` | Current ladder |
| `data/last_update.json` | Freshness metadata |
| `data/season_meta.json` | `totalRegularRounds` for the season |

## Architecture decisions
- No database until: authenticated multi-user picks, intra-day refreshes, or queryable analytics
- Model/data refresh runs in GitHub Actions, never in request paths
- Live override polling only fires within 10 min of kickoff (edge route, fail-soft)
- Results stored inline on game objects (`homeScore`, `awayScore`, `actualWinner`, `actualMargin`)

## Correctness invariants
- `resolveActualWinner` in `src/lib/accuracyHelpers.ts` is the single source of truth for determining a winner
- User picks are stored in `localStorage` per round — no server state
- Archive deduplication: `loadArchiveRounds()` dedupes by `{season}-r{round}` key, latest wins
