"use client";

import { useEffect, useState } from "react";
import type { RoundGameTip, UserPicks } from "@/lib/types";
import { getUserPicksForRound, saveUserPicksForRound } from "@/lib/userPicks";

interface MyPicksProps {
  round: number;
  games: RoundGameTip[];
}

function buildInitial(games: RoundGameTip[]): UserPicks {
  const winnerByGameId: Record<string, string> = {};
  games.forEach((game) => {
    winnerByGameId[game.gameId] = game.tipTeam;
  });
  return { winnerByGameId };
}

export function MyPicks({ round, games }: MyPicksProps) {
  const [picks, setPicks] = useState<UserPicks>(() => buildInitial(games));

  useEffect(() => {
    const saved = getUserPicksForRound(round);
    if (!saved) return;
    setPicks(saved);
  }, [games, round]);

  useEffect(() => {
    saveUserPicksForRound(round, picks);
  }, [picks, round]);

  return (
    <section className="mt-6">
      <h2 className="mb-3">My Picks</h2>
      <div className="grid gap-2.5">
        {games
          .filter((game) => game.status === "upcoming")
          .map((game) => (
            <label
              key={game.gameId}
              className="rounded-md border bg-card p-3"
            >
              {game.homeTeam} vs {game.awayTeam}
              <select
                className="ml-2 rounded-md border bg-background px-2 py-1"
                value={picks.winnerByGameId[game.gameId] ?? game.tipTeam}
                onChange={(event) =>
                  setPicks((prev) => ({
                    ...prev,
                    winnerByGameId: { ...prev.winnerByGameId, [game.gameId]: event.target.value }
                  }))
                }
              >
                <option value={game.homeTeam}>{game.homeTeam}</option>
                <option value={game.awayTeam}>{game.awayTeam}</option>
              </select>
            </label>
          ))}
      </div>
    </section>
  );
}
