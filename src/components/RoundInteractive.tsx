"use client";

import type { RoundGameTip } from "@/lib/types";
import { useRoundPicks } from "@/lib/useRoundPicks";
import { RoundSummary } from "@/components/RoundSummary";
import { TipsList } from "@/components/TipsList";

interface RoundInteractiveProps {
  round: number;
  season: number;
  games: RoundGameTip[];
  showPicks?: boolean;
  mode?: "upcoming" | "all";
}

export function RoundInteractive({ round, season, games, showPicks = false, mode = "upcoming" }: RoundInteractiveProps) {
  const { picks, hasSavedPicks, updateWinnerPick } = useRoundPicks(round, games);
  void showPicks;

  return (
    <>
      <RoundSummary round={round} season={season} games={games} userPicks={picks} hasSavedPicks={hasSavedPicks} />
      <TipsList games={games} mode={mode} userPicks={picks} onPickChange={updateWinnerPick} />
    </>
  );
}

