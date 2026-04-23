"use client";

import type { RoundGameTip } from "@/lib/types";
import { TipCard } from "./TipCard";
import type { UserPicks } from "@/lib/types";

interface TipsListProps {
  games: RoundGameTip[];
  mode?: "upcoming" | "all";
  userPicks?: UserPicks | null;
  onPickChange?: (gameId: string, pick: string) => void;
}

export function TipsList({ games, mode = "upcoming", userPicks, onPickChange }: TipsListProps) {
  const visibleGames = mode === "all" ? games : games.filter((game) => game.status === "upcoming");

  if (visibleGames.length === 0) {
    return mode === "all" ? <p>No games available for this round.</p> : <p>No upcoming games available for tipping yet.</p>;
  }

  return (
    <section className="grid gap-3">
      {visibleGames.map((game) => (
        <TipCard
          key={game.gameId}
          game={game}
          userPick={userPicks?.winnerByGameId?.[game.gameId]}
          onPickChange={onPickChange}
        />
      ))}
    </section>
  );
}
