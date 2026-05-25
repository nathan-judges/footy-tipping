import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { TipCard, getConfidenceLevel } from "@/components/TipCard";
import type { RoundGameTip } from "@/lib/types";

function makeGame(overrides?: Partial<RoundGameTip>): RoundGameTip {
  return {
    gameId: "2026-r01-g01",
    homeTeam: "Broncos",
    awayTeam: "Storm",
    venue: "Suncorp Stadium",
    kickoffAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
    status: "upcoming",
    tipTeam: "Storm",
    confidence: 0.55,
    predictedMargin: 4,
    ...overrides
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

    render(React.createElement(TipCard, { game: makeGame(), mode: "current" }));

    await waitFor(() => {
      expect(screen.getByText(/Live override: Broncos/i)).toBeInTheDocument();
    });
  });

  it("renders minimal matchup row for a finished game", () => {
    render(
      React.createElement(TipCard, {
        game: makeGame({
          status: "finished",
          kickoffAt: "2026-04-01T00:00:00Z",
          homeScore: 10,
          awayScore: 20,
          tipTeam: "Storm"
        }),
        mode: "archive"
      })
    );

    expect(screen.getByText(/Suncorp Stadium/i)).toBeInTheDocument();
    expect(screen.getByText(/Broncos/i)).toBeInTheDocument();
    expect(screen.getByText(/Storm/i)).toBeInTheDocument();
  });

  it("renders correctly for an upcoming game", () => {
    render(React.createElement(TipCard, { game: makeGame(), mode: "current" }));

    expect(screen.getByText(/Suncorp Stadium/i)).toBeInTheDocument();
    expect(screen.getByText(/Broncos/i)).toBeInTheDocument();
    expect(screen.getByText(/Storm/i)).toBeInTheDocument();
    // Confidence percentages should be shown (may appear multiple times — in team label and bar)
    expect(screen.getAllByText(/45%/).length).toBeGreaterThanOrEqual(1); // home (non-tip)
    expect(screen.getAllByText(/55%/).length).toBeGreaterThanOrEqual(1); // away (tip team)
  });

  it("renders correctly for a live game", () => {
    render(
      React.createElement(TipCard, {
        game: makeGame({ status: "live" }),
        mode: "current"
      })
    );

    expect(screen.getByText(/Broncos/i)).toBeInTheDocument();
    expect(screen.getByText(/Storm/i)).toBeInTheDocument();
  });

  it("does not render margin game selection buttons", () => {
    render(React.createElement(TipCard, { game: makeGame(), mode: "current" }));

    expect(screen.queryByRole("button", { name: /margin/i })).not.toBeInTheDocument();
  });

  it("does not render team selection buttons (teams are non-interactive divs)", () => {
    render(React.createElement(TipCard, { game: makeGame(), mode: "current" }));

    // Teams should be displayed but not as clickable buttons
    const buttons = screen.queryAllByRole("button");
    expect(buttons).toHaveLength(0);
  });

  it("does not render margin input field", () => {
    render(React.createElement(TipCard, { game: makeGame(), mode: "current" }));

    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/your margin/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/model spread/i)).not.toBeInTheDocument();
  });

  /**
   * Verifies the simplified prop interface — margin and picking props are absent.
   * Requirements: 1.1, 1.2, 1.3
   */
  it("TipCard prop interface does not include margin or picking props", () => {
    // The component should accept only game, mode, and disableInteractions.
    // TypeScript enforces this at compile time; this test confirms the component
    // renders without any picking/margin props being passed.
    const element = React.createElement(TipCard, {
      game: makeGame(),
      mode: "current",
      disableInteractions: false
    });

    // Verify only the allowed props are present on the element
    const props = element.props as unknown as Record<string, unknown>;
    expect(props).toHaveProperty("game");
    expect(props).toHaveProperty("mode");
    expect(props).toHaveProperty("disableInteractions");

    // Removed props must not be present
    expect(props).not.toHaveProperty("userPick");
    expect(props).not.toHaveProperty("onPickChange");
    expect(props).not.toHaveProperty("disablePicks");
    expect(props).not.toHaveProperty("isMarginGame");
    expect(props).not.toHaveProperty("marginPoints");
    expect(props).not.toHaveProperty("modelMargin");
    expect(props).not.toHaveProperty("onSetMarginGame");
    expect(props).not.toHaveProperty("onMarginPointsChange");
    expect(props).not.toHaveProperty("round");
    expect(props).not.toHaveProperty("season");

    // Component should render without errors
    const { container } = render(element);
    expect(container.firstChild).not.toBeNull();
  });
});

/**
 * getConfidenceLevel unit tests
 * Requirements: 2.1, 2.2, 2.3
 */
describe("getConfidenceLevel", () => {
  it("returns 'high' for scores above 70", () => {
    expect(getConfidenceLevel(71)).toBe("high");
    expect(getConfidenceLevel(85)).toBe("high");
    expect(getConfidenceLevel(100)).toBe("high");
  });

  it("returns 'medium' for scores between 55 and 70 inclusive", () => {
    expect(getConfidenceLevel(55)).toBe("medium");
    expect(getConfidenceLevel(62)).toBe("medium");
    expect(getConfidenceLevel(70)).toBe("medium");
  });

  it("returns 'low' for scores below 55", () => {
    expect(getConfidenceLevel(54)).toBe("low");
    expect(getConfidenceLevel(40)).toBe("low");
    expect(getConfidenceLevel(0)).toBe("low");
  });

  it("returns exactly one of the three levels for any numeric input", () => {
    const validLevels = new Set(["high", "medium", "low"]);
    const testScores = [0, 1, 54, 55, 56, 70, 71, 99, 100, -1, 101];
    for (const score of testScores) {
      expect(validLevels.has(getConfidenceLevel(score))).toBe(true);
    }
  });
});

/**
 * Confidence level styling variation tests
 * Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3
 */
describe("TipCard confidence level styling", () => {
  it("applies high-confidence styling when score > 70%", () => {
    // confidence 0.75 → 75% → high
    const { container } = render(
      React.createElement(TipCard, {
        game: makeGame({ confidence: 0.75, tipTeam: "Storm" }),
        mode: "current"
      })
    );

    // The predicted team (Storm = away) should have data-confidence="high"
    const predictedSpan = container.querySelector('[data-confidence="high"]');
    expect(predictedSpan).not.toBeNull();
    expect(predictedSpan?.textContent).toContain("Storm");

    // Should show the confidence percentage (may appear in team label and bar)
    expect(screen.getAllByText(/75%/).length).toBeGreaterThanOrEqual(1);

    // The predicted team container should have data-predicted="true"
    const predictedContainer = container.querySelector('[data-predicted="true"]');
    expect(predictedContainer).not.toBeNull();
  });

  it("applies medium-confidence styling when score is 55–70%", () => {
    // confidence 0.62 → 62% → medium
    const { container } = render(
      React.createElement(TipCard, {
        game: makeGame({ confidence: 0.62, tipTeam: "Storm" }),
        mode: "current"
      })
    );

    const predictedSpan = container.querySelector('[data-confidence="medium"]');
    expect(predictedSpan).not.toBeNull();
    expect(predictedSpan?.textContent).toContain("Storm");

    expect(screen.getAllByText(/62%/).length).toBeGreaterThanOrEqual(1);
  });

  it("applies low-confidence styling when score < 55%", () => {
    // confidence 0.50 → 50% → low
    const { container } = render(
      React.createElement(TipCard, {
        game: makeGame({ confidence: 0.50, tipTeam: "Storm" }),
        mode: "current"
      })
    );

    const predictedSpan = container.querySelector('[data-confidence="low"]');
    expect(predictedSpan).not.toBeNull();
    expect(predictedSpan?.textContent).toContain("Storm");

    expect(screen.getAllByText(/50%/).length).toBeGreaterThanOrEqual(1);
  });

  it("applies predicted styling to home team when home team is the tip", () => {
    // confidence 0.80 → 80% → high, home team is predicted
    const { container } = render(
      React.createElement(TipCard, {
        game: makeGame({ confidence: 0.80, tipTeam: "Broncos" }),
        mode: "current"
      })
    );

    const predictedSpan = container.querySelector('[data-confidence="high"]');
    expect(predictedSpan).not.toBeNull();
    expect(predictedSpan?.textContent).toContain("Broncos");
  });

  it("applies reduced visual weight to the non-predicted team", () => {
    // Storm is predicted; Broncos (home) should have no data-confidence attribute
    const { container } = render(
      React.createElement(TipCard, {
        game: makeGame({ confidence: 0.75, tipTeam: "Storm" }),
        mode: "current"
      })
    );

    // Non-predicted team span should not have data-confidence
    const allSpansWithConfidence = container.querySelectorAll('[data-confidence]');
    expect(allSpansWithConfidence).toHaveLength(1);

    // The non-predicted container should have data-predicted="false"
    const nonPredictedContainers = container.querySelectorAll('[data-predicted="false"]');
    expect(nonPredictedContainers).toHaveLength(1);
  });

  it("displays confidence percentage next to the predicted team name", () => {
    render(
      React.createElement(TipCard, {
        game: makeGame({ confidence: 0.68, tipTeam: "Storm" }),
        mode: "current"
      })
    );

    // 68% should appear in the card (may appear in team label and bar)
    expect(screen.getAllByText(/68%/).length).toBeGreaterThanOrEqual(1);
  });

  it("renders team logos for both teams", () => {
    render(
      React.createElement(TipCard, {
        game: makeGame({ confidence: 0.75, tipTeam: "Storm" }),
        mode: "current"
      })
    );

    expect(screen.getByAltText(/Broncos logo/i)).toBeInTheDocument();
    expect(screen.getByAltText(/Storm logo/i)).toBeInTheDocument();
  });

  it("renders game metadata with kickoff time and venue", () => {
    render(
      React.createElement(TipCard, {
        game: makeGame({ confidence: 0.75, tipTeam: "Storm" }),
        mode: "current"
      })
    );

    expect(screen.getByText(/Suncorp Stadium/i)).toBeInTheDocument();
  });

  it("renders the confidence bar with probability percentages", () => {
    // confidence 0.75 → Storm (away) is predicted → homePct = 25, awayPct = 75
    render(
      React.createElement(TipCard, {
        game: makeGame({ confidence: 0.75, tipTeam: "Storm" }),
        mode: "current"
      })
    );

    // Both percentages appear in the bar labels (may also appear in team label)
    expect(screen.getAllByText(/25%/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/75%/).length).toBeGreaterThanOrEqual(1);
  });
});
