import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { MarginSelector } from "@/components/MarginSelector";
import type { RoundGameTip } from "@/lib/types";

const games: RoundGameTip[] = [
  {
    gameId: "2026-r01-g01",
    homeTeam: "Broncos",
    awayTeam: "Storm",
    venue: "Suncorp Stadium",
    kickoffAt: "2026-04-24T09:55:00.000Z",
    status: "upcoming",
    tipTeam: "Storm",
    confidence: 0.55,
    predictedMargin: 4
  }
];

describe("MarginSelector", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("persists margin game and points to localStorage", () => {
    render(React.createElement(MarginSelector, { games, suggestedGameId: "2026-r01-g01" }));

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "2026-r01-g01" } });

    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "13" } });

    const stored = window.localStorage.getItem("footy_margin_pick_v1");
    expect(stored).not.toBeNull();
    expect(stored).toContain("2026-r01-g01");
    expect(stored).toContain("13");
  });
});
