# Implementation Plan — Outstanding Work

This file tracks improvements identified after the initial build. Update it as items are completed.

**Note**: All work should follow the branching strategy documented in `git-workflow.md`. Create feature branches (`feat/`, `fix/`, `chore/`) and open PRs to main.

## Priority 1 — UI completeness (high value, low risk)

### ~~1.1 Extract shared page utilities~~ ✅
Moved `computeFreshness()` and `formatRoundUpdatedLabel()` to `src/lib/utils.ts`. Both pages now import from there.

### ~~1.2 Wire `RoundSummary` into the round page~~ ✅
Created `src/components/RoundSummaryWrapper.tsx` (client component that hydrates localStorage picks) and rendered it above `<RoundView>` on the round page. Only renders when at least one finished game has a result.

### ~~1.3 Link archive entries to round detail pages~~ ✅
Each archive card is now wrapped in `<Link href={/round/${entry.round}}>` with a hover state.

### ~~1.4 Show accuracy on archive listing~~ ✅
Extended `ArchiveRoundEntry` with `modelAccuracy?: { correct: number; total: number }`. Computed in `loadArchiveRounds()` via `resolveActualWinner`. Displayed as a badge on each archive card.

## Priority 2 — Component wiring

### ~~2.1 `MyPicks` component~~ ✅ (removed)
`MyPicks` was a simpler duplicate of `RoundView` + `useRoundPicks`. Deleted — `RoundView` already handles localStorage picks with a richer UI.

### ~~2.2 `MarginSelector` component~~ ✅ (removed)
`MarginSelector` used a separate localStorage key (`footy_margin_pick_v1`) that conflicted with the unified picks system. Margin selection is already handled inline in `TipCard`. Deleted both the component and its test.

## Priority 3 — Data pipeline improvements

### 3.1 Auto-populate results in archive snapshots
**Files**: `scripts/update_tips.py`, `scripts/lib/fetch_data.py`
**Problem**: Results (`homeScore`, `awayScore`, `actualWinner`) must currently be added manually to archive files.
**Fix**: When running the pipeline for a round that has already been played, fetch and populate result fields automatically.

### 3.2 Scheduled result backfill
**Files**: `.github/workflows/update-tips.yml`
**Problem**: The scheduled workflow only runs once per week. Results for completed games may not appear until the next run.
**Fix**: Add a second workflow trigger (e.g. daily) that runs `--evaluate` and backfills results for the most recently completed round.

## Priority 4 — Test coverage

### 4.1 Frontend tests for accuracy helpers
**Files**: `src/lib/__tests__/`
**Status**: `accuracyHelpers.ts` has no tests.
**Fix**: Add Vitest tests covering `resolveActualWinner`, `isModelCorrect`, `isUserCorrect`, and `calculateRoundAccuracy` with edge cases (draws, missing scores, null picks).

### 4.2 Frontend tests for `loadArchive`
**Files**: `src/lib/__tests__/`
**Status**: `loadArchive.ts` has no tests.
**Fix**: Add tests for deduplication logic and `loadRoundTips` fallback behaviour using mocked filesystem.

## Completed
- [x] Baked JSON architecture
- [x] Round tips display with team logos
- [x] User picks via localStorage
- [x] Margin game selection and input
- [x] Live override polling (pre-kickoff window)
- [x] Past round accuracy tracking (`RoundSummary`, `accuracyHelpers`)
- [x] Archive page (listing)
- [x] Round selector (all 27 rounds)
- [x] Freshness badge
- [x] ELO ratings + ensemble model
- [x] Backtesting + model monitoring
- [x] GitHub Actions CI + scheduled update
- [x] Git workflow and branching strategy documentation
