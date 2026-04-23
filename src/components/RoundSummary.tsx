"use client";

import type { RoundGameTip, UserPicks } from "@/lib/types";
import { calculateRoundAccuracy } from "@/lib/accuracyHelpers";

interface RoundSummaryProps {
  round: number;
  season: number;
  games: RoundGameTip[];
  userPicks?: UserPicks | null;
  hasSavedPicks?: boolean;
}

export function RoundSummary({ round, season, games, userPicks, hasSavedPicks }: RoundSummaryProps) {
  const summary = calculateRoundAccuracy(games, userPicks);
  const total = summary.finishedGamesWithResult;

  if (total === 0) return null;

  const modelPct = Math.round((summary.modelCorrect / total) * 100);
  const userPct = summary.userCorrect == null ? null : Math.round((summary.userCorrect / total) * 100);

  return (
    <section
      style={{
        background: "#fff",
        border: "1px solid #d0d7de",
        borderRadius: 10,
        padding: 16,
        marginBottom: 16
      }}
    >
      <h2 style={{ margin: "0 0 10px" }}>
        Round {round} Summary <span style={{ color: "#57606a", fontWeight: 500 }}>({season})</span>
      </h2>
      <p style={{ margin: "0 0 6px" }}>
        Model: <strong>{summary.modelCorrect}</strong>/<strong>{total}</strong> correct ({modelPct}%)
      </p>
      <p style={{ margin: 0 }}>
        Your picks:{" "}
        {hasSavedPicks === false || summary.userCorrect == null ? (
          <span style={{ color: "#57606a" }}>not set for this round</span>
        ) : (
          <>
            <strong>{summary.userCorrect}</strong>/<strong>{total}</strong> correct ({userPct}%)
          </>
        )}
      </p>
    </section>
  );
}

