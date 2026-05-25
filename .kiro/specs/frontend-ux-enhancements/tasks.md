# Implementation Plan: Frontend UX Enhancements

## Overview

Four focused tasks to refactor the UI from an interactive tipping tool into a clean prediction showcase. No new dependencies — CSS transitions and Tailwind handle everything. Estimated total effort: 1–2 days.

## Tasks

### Phase 1: Remove Interactive Features

- [ ] 1. Refactor TipCard — remove picking and margin props
  - Remove props from `TipCard`: `isMarginGame`, `marginPoints`, `modelMargin`, `onSetMarginGame`, `onMarginPointsChange`, `userPick`, `onPickChange`, `disablePicks`
  - Remove all JSX that renders margin buttons, margin inputs, and team selection buttons
  - Remove internal state related to picking or margin selection
  - Ensure `game: RoundGameTip`, `mode`, and `disableInteractions` props are retained unchanged
  - Verify the component still renders correctly for upcoming, live, and finished game states
  - Write Vitest test verifying the simplified prop interface (margin and picking props absent)
  - _Requirements: 1.1, 1.2, 1.3, 6.1, 6.4, 6.5_

- [ ] 2. Refactor RoundView — remove picking state and localStorage
  - Remove `suggestedMarginGameId` prop from `RoundView`
  - Remove `useRoundPicks` hook import and all usage
  - Remove `winnerByGameId`, `marginGameId`, `marginPoints` state
  - Remove all `saveUserPicksForRound` calls and localStorage reads/writes
  - Remove or deprecate `src/hooks/useRoundPicks.ts` (add deprecation comment if other code references it)
  - Retain `round`, `season`, `games`, `mode`, `disableInteractions` props unchanged
  - Write Vitest test verifying localStorage is not accessed during render
  - _Requirements: 1.4, 1.5, 1.6, 6.2, 6.3_

### Phase 2: Visual Improvements

- [ ] 3. Add confidence indicators and modern card design to TipCard
  - Implement `getConfidenceLevel(score: number): "high" | "medium" | "low"` helper (>70% high, 55–70% medium, <55% low)
  - Apply confidence-based styling to the predicted team: font weight, color intensity, and subtle background tint (10–20% opacity) using `getTeamIdentity` colors
  - Apply reduced visual weight to the non-predicted team (lighter font, muted color)
  - Display the confidence percentage next to the predicted team name
  - Add a horizontal confidence bar below the team names: home team color on the left (width = home win probability %), away team color on the right; use CSS `transition-[width] duration-700` for the fill animation triggered by a `useEffect` on mount
  - Display team logos from `/public/team-logos/` with responsive sizing (Tailwind `w-8 h-8 sm:w-10 sm:h-10`)
  - Display game metadata (kickoff time, venue) with `text-sm text-muted-foreground`
  - Apply responsive layout: vertical stack on mobile (`< 640px`), horizontal on tablet/desktop
  - Write Vitest tests covering all three confidence level styling variations
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.4_

- [ ] 4. Add staggered card load animation
  - Add a `fade-slide-up` CSS keyframe to `src/app/globals.css`:
    - `from`: `opacity: 0; transform: translateY(8px)`
    - `to`: `opacity: 1; transform: translateY(0)`
    - Duration: 350ms, easing: `ease-out`
    - Include `@media (prefers-reduced-motion: reduce)` override that disables the animation
  - In `RoundView`, wrap each `TipCard` in a container with `className="animate-fade-slide-up"` and `style={{ animationDelay: \`${index * 50}ms\`, animationFillMode: "both" }}`
  - Verify animation plays on page load and is absent when `prefers-reduced-motion` is set
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

## Notes

- Tasks 1 and 2 should be completed and tested before starting task 3 — a clean component interface makes the visual work easier
- The confidence bar animation uses a `useEffect` that sets a CSS variable or inline style to the final width after mount; the CSS transition does the rest
- No Framer Motion, no GSAP — if a CSS transition feels insufficient for any effect, use a simple `useEffect` + `requestAnimationFrame` before reaching for a library
- The `disableInteractions` prop is retained on `RoundView` and `TipCard` for forward compatibility but is currently a no-op after picking is removed

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": ["1"],
      "description": "Remove picking and margin props from TipCard — clean interface first"
    },
    {
      "wave": 2,
      "tasks": ["2"],
      "description": "Remove picking state and localStorage from RoundView — depends on task 1"
    },
    {
      "wave": 3,
      "tasks": ["3"],
      "description": "Add confidence indicators and card design — depends on clean TipCard interface from task 1"
    },
    {
      "wave": 4,
      "tasks": ["4"],
      "description": "Add staggered load animation in RoundView — depends on task 2"
    }
  ]
}
```
