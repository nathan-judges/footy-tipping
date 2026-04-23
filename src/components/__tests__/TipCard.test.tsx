import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { TipCard } from "@/components/TipCard";
import type { RoundGameTip } from "@/lib/types";

function makeGame(): RoundGameTip {
  return {
    gameId: "2026-r01-g01",
    homeTeam: "Broncos",
    awayTeam: "Storm",
    venue: "Suncorp Stadium",
    kickoffAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
    status: "upcoming",
    tipTeam: "Storm",
    confidence: 0.55,
    predictedMargin: 4
  };
}

describe("TipCard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("applies override tip from live endpoint in pre-kickoff window", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          tipOverride: { tipTeam: "Broncos", reason: "late changes for Storm: OUT 1" }
        }),
        { status: 200 }
      )
    );

    render(React.createElement(TipCard, { game: makeGame(), round: 1, season: 2026 }));

    await waitFor(() => {
      expect(screen.getByText(/Live override: Broncos/i)).toBeInTheDocument();
    });
  });

  it("renders minimal matchup row", () => {
    render(
      React.createElement(TipCard, {
        game: {
          ...makeGame(),
          status: "finished",
          kickoffAt: "2026-04-01T00:00:00Z",
          homeScore: 10,
          awayScore: 20,
          tipTeam: "Storm"
        },
        round: 1,
        season: 2026
      })
    );

    expect(screen.getByText(/Suncorp Stadium/i)).toBeInTheDocument();
    expect(screen.getByText(/VIEW STATS/i)).toBeInTheDocument();
    expect(screen.getByText(/Broncos/i)).toBeInTheDocument();
    expect(screen.getByText(/Storm/i)).toBeInTheDocument();
  });
});
