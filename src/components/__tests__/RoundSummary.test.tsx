import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import { RoundSummary } from "@/components/RoundSummary";
import type { RoundGameTip, UserPicks } from "@/lib/types";

function finishedGame(overrides: Partial<RoundGameTip> = {}): RoundGameTip {
  return {
    gameId: "g1",
    homeTeam: "Alpha",
    awayTeam: "Beta",
    venue: "Somewhere",
    kickoffAt: "2026-04-01T00:00:00Z",
    status: "finished",
    tipTeam: "Alpha",
    confidence: 0.6,
    predictedMargin: 4,
    homeScore: 18,
    awayScore: 10,
    ...overrides
  };
}

describe("RoundSummary", () => {
  it("renders empty-state message when no finished games with results", () => {
    const games: RoundGameTip[] = [
      {
        gameId: "u1",
        homeTeam: "A",
        awayTeam: "B",
        venue: "V",
        kickoffAt: "2026-04-01T00:00:00Z",
        status: "upcoming",
        tipTeam: "A",
        confidence: 0.5,
        predictedMargin: 1
      }
    ];

    render(React.createElement(RoundSummary, { round: 1, season: 2026, games }));
    expect(screen.getByText(/Round 1 has not started yet/i)).toBeInTheDocument();
  });

  it("renders model and user accuracy when picks exist", () => {
    const games = [finishedGame({ gameId: "a", tipTeam: "Alpha", homeScore: 18, awayScore: 10 })];
    const picks: UserPicks = { winnerByGameId: { a: "Alpha" } };

    render(React.createElement(RoundSummary, { round: 1, season: 2026, games, userPicks: picks, hasSavedPicks: true }));

    expect(screen.getByText(/Model:/i)).toBeInTheDocument();
    expect(
      screen.getByText((_, el) => el?.tagName === "P" && (el.textContent ?? "").includes("Model:") && (el.textContent ?? "").includes("correct (100%)"))
    ).toBeInTheDocument();
    expect(screen.getByText(/Your picks:/i)).toBeInTheDocument();
  });
});

