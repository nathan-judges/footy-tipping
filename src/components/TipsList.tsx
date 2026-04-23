"use client";

import type { RoundGameTip } from "@/lib/types";
import { TipCard } from "./TipCard";

interface TipsListProps {
  round: number;
  season: number;
  games: RoundGameTip[];
  mode?: "upcoming" | "all";
}

export function TipsList({ games, mode = "upcoming", round, season }: TipsListProps) {
  const visibleGames = mode === "all" ? games : games.filter((game) => game.status === "upcoming");

  if (visibleGames.length === 0) {
    return mode === "all" ? <p>No games available for this round.</p> : <p>No upcoming games available for tipping yet.</p>;
  }

  return (
    <section className="grid gap-3">
      {visibleGames.map((game) => (
        <TipCard
          key={game.gameId}
          round={round}
          season={season}
          game={game}
        />
      ))}
    </section>
  );
}
