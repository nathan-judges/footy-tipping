import { describe, expect, it } from "vitest";
import type { RoundGameTip, UserPicks } from "@/lib/types";
import { calculateRoundAccuracy, isModelCorrect, isUserCorrect, resolveActualWinner } from "@/lib/accuracyHelpers";

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

describe("accuracyHelpers", () => {
  it("derives actual winner from scores when missing", () => {
    expect(resolveActualWinner(finishedGame({ actualWinner: undefined, homeScore: 6, awayScore: 12 }))).toBe("Beta");
  });

  it("returns null actual winner on missing scores", () => {
    expect(resolveActualWinner(finishedGame({ homeScore: undefined, awayScore: undefined }))).toBeNull();
  });

  it("computes model/user correctness when results present", () => {
    const game = finishedGame({ tipTeam: "Alpha", homeScore: 18, awayScore: 10 });
    expect(isModelCorrect(game)).toBe(true);
    expect(isUserCorrect(game, "Alpha")).toBe(true);
    expect(isUserCorrect(game, "Beta")).toBe(false);
  });

  it("round accuracy uses finished games with results only", () => {
    const games: RoundGameTip[] = [
      finishedGame({ gameId: "a", tipTeam: "Alpha", homeScore: 18, awayScore: 10 }),
      finishedGame({ gameId: "b", tipTeam: "Beta", homeScore: 6, awayScore: 12 }),
      finishedGame({ gameId: "c", homeScore: undefined, awayScore: undefined })
    ];

    const picks: UserPicks = {
      winnerByGameId: {
        a: "Alpha",
        b: "Alpha"
      }
    };

    const summary = calculateRoundAccuracy(games, picks);
    expect(summary.finishedGamesWithResult).toBe(2);
    expect(summary.modelCorrect).toBe(2);
    expect(summary.userCorrect).toBe(1);
  });
});

