"use client";

import type { RoundGameTip } from "@/lib/types";
import { TipCard } from "./TipCard";
import type { UserPicks } from "@/lib/types";

interface TipsListProps {
  games: RoundGameTip[];
  mode?: "upcoming" | "all";
  userPicks?: UserPicks | null;
}

export function TipsList({ games, mode = "upcoming", userPicks }: TipsListProps) {
  const visibleGames = mode === "all" ? games : games.filter((game) => game.status === "upcoming");

  if (visibleGames.length === 0) {
    return mode === "all" ? <p>No games available for this round.</p> : <p>No upcoming games available for tipping yet.</p>;
  }

  return (
    <section style={{ display: "grid", gap: 12 }}>
      {visibleGames.map((game) => (
        <TipCard key={game.gameId} game={game} userPick={userPicks?.winnerByGameId?.[game.gameId]} />
      ))}
    </section>
  );
}
