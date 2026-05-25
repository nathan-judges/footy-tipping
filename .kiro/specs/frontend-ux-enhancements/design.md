# Design Document: Frontend UX Enhancements

## Overview

Refactor `TipCard` and `RoundView` to remove interactive picking, add visual confidence indicators, and improve card design. No new dependencies — CSS transitions handle all animations, Tailwind handles all styling.

### Design Goals

1. **Simplify**: Remove all picking/margin state and logic
2. **Clarity**: Make the predicted winner immediately obvious at a glance
3. **Polish**: Smooth card load animation and confidence bar using CSS only

### Constraints

- No new npm dependencies (no Framer Motion, no GSAP)
- Tailwind v4 + existing shadcn/ui primitives only
- Must not break existing `RoundGameTip` type or `tipOverride` mechanism
- All animations respect `prefers-reduced-motion`

## Component Changes

### TipCard

**File**: `src/components/TipCard.tsx`

**Props removed:**
- `isMarginGame`, `marginPoints`, `modelMargin`, `onSetMarginGame`, `onMarginPointsChange`
- `userPick`, `onPickChange`, `disablePicks`

**Props kept:**
- `game: RoundGameTip` — unchanged
- `mode: "current" | "archive"` — unchanged
- `disableInteractions: boolean` — kept for future use, currently a no-op

**New visual logic:**

```typescript
type ConfidenceLevel = "high" | "medium" | "low";

function getConfidenceLevel(score: number): ConfidenceLevel {
  if (score > 70) return "high";
  if (score >= 55) return "medium";
  return "low";
}

const confidenceStyles: Record<ConfidenceLevel, string> = {
  high:   "font-bold text-foreground",
  medium: "font-semibold text-foreground/90",
  low:    "font-medium text-foreground/70",
};
```

**Card layout (simplified):**

```
┌─────────────────────────────────────────────┐
│  [Home Logo] HOME TEAM         AWAY TEAM [Away Logo] │
│  ████ 68%  ←confidence bar→  32%            │
│  Thu 8 May · Suncorp Stadium                │
└─────────────────────────────────────────────┘
```

- Predicted team: bold name, team color background tint (10–20% opacity), confidence % shown
- Non-predicted team: lighter weight, muted color
- Confidence bar: CSS `width` transition from 0% → final value on mount

**Confidence bar implementation:**

```tsx
// CSS transition handles animation — no JS needed
<div className="h-1.5 rounded-full overflow-hidden bg-muted flex">
  <div
    className="transition-[width] duration-700 ease-out"
    style={{
      width: `${homeWinProbability * 100}%`,
      backgroundColor: homeTeamColor,
    }}
  />
  <div
    className="flex-1"
    style={{ backgroundColor: awayTeamColor, opacity: 0.4 }}
  />
</div>
```

The `transition-[width]` starts from 0% because the element renders at 0 width initially (controlled by a `useEffect` that sets the final width after mount).

### RoundView

**File**: `src/components/RoundView.tsx`

**Removed:**
- `suggestedMarginGameId` prop
- `useRoundPicks` hook import and usage
- `winnerByGameId` state
- `marginGameId` and `marginPoints` state
- `saveUserPicksForRound` calls
- All localStorage reads/writes

**Kept:**
- `round`, `season`, `games`, `mode`, `disableInteractions` props
- Rendering logic for current vs archive mode
- `tipOverride` display

**Staggered card animation:**

```tsx
// Each TipCard gets an animation delay based on its index
// CSS handles the rest — no JS animation library needed
<div
  className="animate-fade-slide-up"
  style={{
    animationDelay: `${index * 50}ms`,
    animationFillMode: "both",
  }}
>
  <TipCard game={game} mode={mode} />
</div>
```

**CSS keyframe** (add to `src/app/globals.css`):

```css
@keyframes fade-slide-up {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-slide-up {
  animation: fade-slide-up 350ms ease-out;
}

@media (prefers-reduced-motion: reduce) {
  .animate-fade-slide-up {
    animation: none;
  }
}
```

### Hooks and Utilities to Remove/Deprecate

- `src/hooks/useRoundPicks.ts` — remove or mark deprecated with a comment
- `src/lib/saveUserPicks.ts` (or equivalent) — remove if only used by picking flow

### Files Not Changing

- `src/lib/accuracyHelpers.ts` — unchanged
- `src/lib/loadArchive.ts` — unchanged
- `src/app/api/live-override/route.ts` — unchanged
- All page components — unchanged (they pass `games` down, no picking state at page level)

## Confidence Level Styling Reference

| Level  | Score     | Predicted team style                        | Background tint |
|--------|-----------|---------------------------------------------|-----------------|
| High   | > 70%     | `font-bold`, full team color                | 15% opacity     |
| Medium | 55–70%    | `font-semibold`, team color at 80% opacity  | 10% opacity     |
| Low    | < 55%     | `font-medium`, team color at 60% opacity    | 5% opacity      |

Non-predicted team always renders at `font-normal`, `text-muted-foreground`.

## Architecture

The frontend is a Next.js App Router application. No architectural changes are needed — this is a component refactor within the existing structure:

```
src/
  app/
    globals.css          ← add fade-slide-up keyframe
  components/
    TipCard.tsx          ← refactor: remove picking, add confidence UI
    RoundView.tsx        ← refactor: remove picking state and localStorage
  hooks/
    useRoundPicks.ts     ← deprecate / remove
  lib/
    saveUserPicks.ts     ← remove if only used by picking flow
```

No new files, no new routes, no new API calls.

## Data Models

No data model changes. The existing `RoundGameTip` type is used as-is. The `confidence` field (already present as a number 0–100) drives the new visual tiers.

```typescript
// Existing type — unchanged
type RoundGameTip = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  kickoffAt: string;
  venue: string;
  modelPick: string;
  confidence: number;       // 0–100, drives confidence tier styling
  homeWinProbability: number; // 0–1, drives confidence bar width
  tipOverride?: { ... };
  homeScore?: number;
  awayScore?: number;
  actualWinner?: string;
  actualMargin?: number;
};
```

## Components and Interfaces

### TipCard

```typescript
interface TipCardProps {
  game: RoundGameTip;
  mode: "current" | "archive";
  disableInteractions?: boolean; // retained, currently no-op
}
```

All margin and picking props are removed. The component is a pure presentation component with one piece of internal state: a boolean `mounted` flag used to trigger the confidence bar CSS transition.

### RoundView

```typescript
interface RoundViewProps {
  round: number;
  season: number;
  games: RoundGameTip[];
  mode: "current" | "archive";
  disableInteractions?: boolean;
  // suggestedMarginGameId removed
}
```

## Correctness Properties

### Property 1: Confidence Level Completeness
`getConfidenceLevel(score)` must return exactly one of `"high" | "medium" | "low"` for any numeric input.

**Validates: Requirements 2.1, 2.2, 2.3**

### Property 2: Confidence Bar Accuracy
Confidence bar width must equal `homeWinProbability * 100` percent, clamped to [0, 100].

**Validates: Requirements 2.5**

### Property 3: Predicted Team Visual Priority
The predicted team (modelPick) must always receive the higher visual weight styling compared to the non-predicted team.

**Validates: Requirements 3.1, 3.2**

### Property 4: No localStorage Side Effects
No localStorage reads or writes occur during any render path after the refactor.

**Validates: Requirements 1.6**

## Error Handling

- If `getTeamIdentity` returns no color for a team, fall back to a neutral gray for the confidence bar and background tint
- If `confidence` is undefined or NaN, treat as low confidence (< 55%)
- If `homeWinProbability` is undefined, render the confidence bar at 50/50

## Testing Strategy

- Vitest + Testing Library for component tests
- Test all three confidence tiers render the correct CSS classes
- Test that removed props are not present in the component's TypeScript interface
- Test that RoundView does not call `localStorage.getItem` or `localStorage.setItem`
- Run existing test suite to confirm no regressions
