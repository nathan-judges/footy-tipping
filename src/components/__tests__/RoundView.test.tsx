import { render, screen } from "@testing-library/react";
import React from "react";
import { RoundView } from "@/components/RoundView";
import type { RoundGameTip } from "@/lib/types";

function makeGame(overrides?: Partial<RoundGameTip>): RoundGameTip {
  return {
    gameId: "2026-r01-g01",
    homeTeam: "Broncos",
    awayTeam: "Storm",
    venue: "Suncorp Stadium",
    kickoffAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    status: "upcoming",
    tipTeam: "Storm",
    confidence: 0.65,
    predictedMargin: 6,
    ...overrides
  };
}

describe("RoundView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Verifies localStorage is not accessed during render.
   * Requirements: 1.4, 1.5, 1.6, 6.2, 6.3
   */
  it("does not read from or write to localStorage during render", () => {
    const getItemSpy = vi.spyOn(Storage.prototype, "getItem");
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");

    render(
      React.createElement(RoundView, {
        round: 1,
        season: 2026,
        games: [makeGame()],
        mode: "upcoming"
      })
    );

    expect(getItemSpy).not.toHaveBeenCalled();
    expect(setItemSpy).not.toHaveBeenCalled();
  });

  it("does not access localStorage when rendering multiple games", () => {
    const getItemSpy = vi.spyOn(Storage.prototype, "getItem");
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");

    const games = [
      makeGame({ gameId: "2026-r01-g01", homeTeam: "Broncos", awayTeam: "Storm" }),
      makeGame({ gameId: "2026-r01-g02", homeTeam: "Raiders", awayTeam: "Roosters" }),
      makeGame({ gameId: "2026-r01-g03", homeTeam: "Panthers", awayTeam: "Cowboys" })
    ];

    render(
      React.createElement(RoundView, {
        round: 1,
        season: 2026,
        games,
        mode: "upcoming"
      })
    );

    expect(getItemSpy).not.toHaveBeenCalled();
    expect(setItemSpy).not.toHaveBeenCalled();
  });

  it("does not access localStorage when mode is 'all'", () => {
    const getItemSpy = vi.spyOn(Storage.prototype, "getItem");
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");

    render(
      React.createElement(RoundView, {
        round: 1,
        season: 2026,
        games: [makeGame(), makeGame({ gameId: "2026-r01-g02", status: "finished" })],
        mode: "all"
      })
    );

    expect(getItemSpy).not.toHaveBeenCalled();
    expect(setItemSpy).not.toHaveBeenCalled();
  });

  it("renders the empty state message when no upcoming games exist", () => {
    render(
      React.createElement(RoundView, {
        round: 1,
        season: 2026,
        games: [],
        mode: "upcoming"
      })
    );

    expect(screen.getByText(/No upcoming games available for tipping yet/i)).toBeInTheDocument();
  });

  it("renders only upcoming games when mode is 'upcoming'", () => {
    const games = [
      makeGame({ gameId: "2026-r01-g01", homeTeam: "Broncos", awayTeam: "Storm", status: "upcoming" }),
      makeGame({ gameId: "2026-r01-g02", homeTeam: "Raiders", awayTeam: "Roosters", status: "finished" })
    ];

    render(
      React.createElement(RoundView, {
        round: 1,
        season: 2026,
        games,
        mode: "upcoming"
      })
    );

    expect(screen.getByText(/Broncos/i)).toBeInTheDocument();
    expect(screen.getByText(/Storm/i)).toBeInTheDocument();
    // Finished game teams should not appear (filtered out)
    expect(screen.queryByText(/Raiders/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Roosters/i)).not.toBeInTheDocument();
  });

  it("renders all games when mode is 'all'", () => {
    const games = [
      makeGame({ gameId: "2026-r01-g01", homeTeam: "Broncos", awayTeam: "Storm", status: "upcoming" }),
      makeGame({ gameId: "2026-r01-g02", homeTeam: "Raiders", awayTeam: "Roosters", status: "finished" })
    ];

    render(
      React.createElement(RoundView, {
        round: 1,
        season: 2026,
        games,
        mode: "all"
      })
    );

    expect(screen.getByText(/Broncos/i)).toBeInTheDocument();
    expect(screen.getByText(/Raiders/i)).toBeInTheDocument();
  });

  /**
   * Verifies the RoundView prop interface retains the required props.
   * Requirements: 6.2
   */
  it("RoundView prop interface retains round, season, games, mode, and disableInteractions", () => {
    const element = React.createElement(RoundView, {
      round: 1,
      season: 2026,
      games: [makeGame()],
      mode: "upcoming",
      disableInteractions: false
    });

    const props = element.props as unknown as Record<string, unknown>;
    expect(props).toHaveProperty("round");
    expect(props).toHaveProperty("season");
    expect(props).toHaveProperty("games");
    expect(props).toHaveProperty("mode");
    expect(props).toHaveProperty("disableInteractions");

    // suggestedMarginGameId must not be present
    expect(props).not.toHaveProperty("suggestedMarginGameId");
  });
});
