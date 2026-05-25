# Requirements Document

## Introduction

This document specifies requirements for simplifying and modernizing the NRL tipping app's UI. The changes remove interactive picking features (no longer needed now that the app is a prediction showcase), add visual confidence indicators, and improve the card design and visual hierarchy. Animations are handled with CSS transitions — no new animation library dependencies.

## Glossary

- **TipCard**: The component displaying a single game's prediction
- **RoundView**: The component displaying all games in a round
- **Confidence_Score**: A percentage (0–100%) indicating prediction certainty
- **Model_Prediction**: The machine learning model's predicted winner

## Requirements

### Requirement 1: Remove Margin Selection and Interactive Picking

**User Story:** As a user, I want a simplified interface without margin selection or team picking, so that the app clearly presents model predictions rather than asking for my input.

#### Acceptance Criteria

1. THE TipCard SHALL NOT display margin game selection buttons, margin input fields, or model spread indicators
2. THE TipCard SHALL NOT accept `isMarginGame`, `marginPoints`, `modelMargin`, `onSetMarginGame`, or `onMarginPointsChange` props
3. THE TipCard SHALL NOT display clickable team selection buttons and SHALL NOT accept `userPick`, `onPickChange`, or `disablePicks` props
4. THE RoundView SHALL NOT manage margin game state or user pick state
5. THE RoundView SHALL NOT use the `useRoundPicks` hook or call `saveUserPicksForRound`
6. THE UI_System SHALL NOT read from or write to localStorage for user picks
7. WHEN displaying a game, THE TipCard SHALL show the Model_Prediction as the only highlighted team

### Requirement 2: Visual Confidence Indicators

**User Story:** As a user, I want to see how confident the model is about each prediction, so that I can quickly gauge which tips are strong and which are marginal calls.

#### Acceptance Criteria

1. WHEN the Confidence_Score is above 70%, THE TipCard SHALL apply high-confidence visual styling (strong color, bold weight) to the predicted team
2. WHEN the Confidence_Score is between 55% and 70%, THE TipCard SHALL apply medium-confidence visual styling to the predicted team
3. WHEN the Confidence_Score is below 55%, THE TipCard SHALL apply low-confidence visual styling (muted color, lighter weight) to the predicted team
4. THE TipCard SHALL display the Confidence_Score as a percentage next to the predicted team name
5. THE TipCard SHALL display a horizontal confidence bar showing the probability split between teams, using each team's brand color
6. THE confidence bar SHALL animate from 0% to its final width using a CSS transition (no JS animation library required)
7. THE confidence indicators SHALL be understandable without relying solely on color (include text percentage)

### Requirement 3: Modern Card Design and Visual Hierarchy

**User Story:** As a user, I want visually clear game cards where the predicted winner is immediately obvious, so that I can scan the round at a glance.

#### Acceptance Criteria

1. THE TipCard SHALL display the predicted team with prominent visual weight: font-weight-700 or higher, team brand color accent
2. THE TipCard SHALL display the non-predicted team with reduced visual weight: lighter font weight, muted color
3. WHEN a team is the predicted winner, THE TipCard SHALL apply a subtle background tint using the team's primary color (opacity 10–20%)
4. THE TipCard SHALL display team logos from the existing `/public/team-logos/` directory with appropriate sizing
5. THE TipCard SHALL display game metadata (kickoff time, venue) with reduced visual prominence (text-sm, muted color)
6. THE TipCard SHALL use the existing `getTeamIdentity` function for team color and branding data
7. THE TipCard SHALL use subtle shadow or border to create card depth, consistent with existing Tailwind v4 design tokens

### Requirement 4: Responsive Layout

**User Story:** As a user on any device, I want the cards to display well at all screen sizes.

#### Acceptance Criteria

1. WHEN viewed on mobile (< 640px), THE TipCard SHALL stack team information vertically
2. WHEN viewed on tablet and desktop (≥ 640px), THE TipCard SHALL use a horizontal layout with the two teams side by side
3. THE team logos SHALL scale appropriately across breakpoints using Tailwind responsive classes
4. THE confidence bar SHALL remain readable at all breakpoints

### Requirement 5: Card Load Animation

**User Story:** As a user, I want cards to appear smoothly when the page loads, so that the interface feels polished.

#### Acceptance Criteria

1. WHEN a RoundView loads, THE TipCard components SHALL animate into view with a staggered fade-in and slide-up effect
2. THE stagger delay SHALL be implemented using CSS `animation-delay` (30–60ms per card index)
3. THE animation SHALL use a CSS keyframe or Tailwind animation class — no JavaScript animation library
4. WHEN a user has `prefers-reduced-motion` enabled, THE TipCard components SHALL appear immediately without animation

### Requirement 6: Data Compatibility and Backward Compatibility

**User Story:** As a developer, I want the refactored UI to work with existing data structures, so that no backend changes are required.

#### Acceptance Criteria

1. THE TipCard SHALL accept the existing `RoundGameTip` type without modifications to the type definition
2. THE RoundView SHALL continue to accept `round`, `season`, `games`, `mode`, and `disableInteractions` props
3. THE UI_System SHALL continue to read from `data/current_round_tips.json` without schema changes
4. THE UI_System SHALL continue to support the existing `tipOverride` mechanism
5. THE UI_System SHALL display `homeScore`, `awayScore`, `actualWinner`, and `actualMargin` for finished games

### Requirement 7: Testing

**User Story:** As a developer, I want tests for the refactored components, so that regressions are caught early.

#### Acceptance Criteria

1. THE TipCard SHALL have Vitest tests covering all three confidence level styling variations (high, medium, low)
2. THE TipCard SHALL have a Vitest test verifying that margin and picking props are not present in the component interface
3. THE RoundView SHALL have a Vitest test verifying that localStorage is not accessed during render
4. THE existing test suite SHALL continue to pass after the refactor
