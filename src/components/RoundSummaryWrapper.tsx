"use client";

import { useEffect, useState } from "react";
import type { RoundGameTip, UserPicks } from "@/lib/types";
import { RoundSummary } from "@/components/RoundSummary";
import { getUserPicksForRound } from "@/lib/userPicks";

interface RoundSummaryWrapperProps {
  round: number;
  season: number;
  games: RoundGameTip[];
}

/**
 * Client wrapper that hydrates saved localStorage picks and passes them
 * to RoundSummary. Only renders the summary when at least one game is finished
 * with a result — upcoming-only rounds show nothing.
 */
export function RoundSummaryWrapper({ round, season, games }: RoundSummaryWrapperProps) {
  const [userPicks, setUserPicks] = useState<UserPicks | null>(null);
  const [hasSavedPicks, setHasSavedPicks] = useState(false);

  useEffect(() => {
    const saved = getUserPicksForRound(round);
    setUserPicks(saved);
    setHasSavedPicks(saved != null);
  }, [round]);

  const hasFinishedWithResult = games.some(
    (g) =>
      g.status === "finished" &&
      (typeof g.actualWinner === "string" ||
        (typeof g.homeScore === "number" && typeof g.awayScore === "number"))
  );

  if (!hasFinishedWithResult) return null;

  return (
    <RoundSummary
      round={round}
      season={season}
      games={games}
      userPicks={userPicks}
      hasSavedPicks={hasSavedPicks}
    />
  );
}
