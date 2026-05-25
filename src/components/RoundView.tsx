"use client";

import type { RoundGameTip } from "@/lib/types";
import { TipCard } from "@/components/TipCard";

interface RoundViewProps {
  round: number;
  season: number;
  games: RoundGameTip[];
  mode?: "upcoming" | "all";
  disableInteractions?: boolean;
}

export function RoundView({
  round: _round,
  season: _season,
  games,
  mode = "upcoming",
  disableInteractions = false
}: RoundViewProps) {
  const visibleGames = mode === "all" ? games : games.filter((game) => game.status === "upcoming");

  return (
    <section className="space-y-3">
      {visibleGames.length === 0 ? (
        <p>No upcoming games available for tipping yet.</p>
      ) : (
        visibleGames.map((game, index) => (
          <div
            key={game.gameId}
            className="animate-fade-slide-up"
            style={{ animationDelay: `${index * 50}ms`, animationFillMode: "both" }}
          >
            <TipCard
              game={game}
              mode="current"
              disableInteractions={disableInteractions}
            />
          </div>
        ))
      )}
    </section>
  );
}
