import { render, screen } from "@testing-library/react";
import React from "react";
import { Ladder } from "@/components/Ladder";
import type { LadderData } from "@/lib/types";

const ladder: LadderData = {
  season: 2026,
  round: 8,
  generatedAt: "2026-04-23T00:00:00Z",
  rows: [
    {
      rank: 1,
      team: "Storm",
      played: 8,
      wins: 7,
      losses: 1,
      pointsFor: 180,
      pointsAgainst: 120,
      pointsDiff: 60,
      competitionPoints: 14
    }
  ]
};

describe("Ladder", () => {
  it("renders ladder row data", () => {
    render(React.createElement(Ladder, { ladder }));
    expect(screen.getByText("Ladder")).toBeInTheDocument();
    expect(screen.getByText("Storm")).toBeInTheDocument();
    expect(screen.getByText("14")).toBeInTheDocument();
  });
});
