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

  if (total === 0) {
    return (
      <section className="mb-4 rounded-md border bg-card p-4">
        <h2 className="mb-2.5">
          Round {round} Summary <span className="font-medium text-muted-foreground">({season})</span>
        </h2>
        <p className="text-muted-foreground">Round {round} has not started yet. Check back after the games!</p>
      </section>
    );
  }

  const modelPct = Math.round((summary.modelCorrect / total) * 100);
  const userPct = summary.userCorrect == null ? null : Math.round((summary.userCorrect / total) * 100);

  return (
    <section className="mb-4 rounded-md border bg-card p-4">
      <h2 className="mb-2.5">
        Round {round} Summary <span className="font-medium text-muted-foreground">({season})</span>
      </h2>
      <p className="mb-1.5">
        Model: <strong>{summary.modelCorrect}</strong>/<strong>{total}</strong> correct ({modelPct}%)
      </p>
      <p>
        Your picks:{" "}
        {hasSavedPicks === false || summary.userCorrect == null ? (
          <span className="text-muted-foreground">not set for this round</span>
        ) : (
          <>
            <strong>{summary.userCorrect}</strong>/<strong>{total}</strong> correct ({userPct}%)
          </>
        )}
      </p>
    </section>
  );
}

