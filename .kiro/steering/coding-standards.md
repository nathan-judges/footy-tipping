# Coding Standards

## TypeScript
- Strict mode — no `any` in new code
- Prefer server components by default; add `"use client"` only when needed (hooks, event handlers, browser APIs)
- Small composable helpers in `src/lib/`
- Shared utility functions (e.g. `computeFreshness`, `formatRoundUpdatedLabel`) belong in `src/lib/utils.ts` — never duplicated across pages

## React / Next.js
- App Router only — no Pages Router
- Page-level data loading via direct imports of baked JSON or `loadXxx()` helpers in `src/lib/`
- No `fetch()` in server components — read from filesystem via `loadArchive.ts` / `loadTips.ts`
- Edge runtime for API routes (`export const runtime = "edge"`)
- API routes must fail-soft: always return a valid JSON response, never throw to the client

## Python
- PEP 8, docstrings on non-trivial functions
- All pipeline modules live in `scripts/lib/`
- Tests in `tests/python/` using pytest
- Non-fatal helpers (ELO build, evaluation, backtesting) must not block the main pipeline

## Testing
- Frontend: Vitest + Testing Library (`npm test`)
- Python: pytest (`npm run test:python` or `pytest tests/python/`)
- Run `npm run check` before committing (lint + typecheck + frontend tests)
- Run `npm run check:all` to include Python tests

## Git & Commits
- Follow the branching strategy in `git-workflow.md`
- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`, `test/`, `perf/`
- Conventional Commits: `<type>(<scope>): <description>`
- Keep commits focused — one logical change per commit
- All changes via PR (except automated bot commits)
- Squash merge to main for clean history

## File organisation
```
src/
  app/          # Next.js routes (page.tsx, layout.tsx, api/)
  components/   # React components
    ui/         # shadcn primitives only
  lib/          # Pure helpers, types, data loaders
scripts/
  lib/          # Python pipeline modules
tests/
  python/       # pytest tests
data/           # Baked JSON artifacts (committed)
docs/           # Architecture decisions, runbooks
```
