"use client";

import type { RoundGameTip } from "@/lib/types";
import { TipsList } from "@/components/TipsList";

interface RoundInteractiveProps {
  round: number;
  season: number;
  games: RoundGameTip[];
  mode?: "upcoming" | "all";
}

export function RoundInteractive({ round, season, games, mode = "upcoming" }: RoundInteractiveProps) {
  return (
    <TipsList round={round} season={season} games={games} mode={mode} />
  );
}

