"use client";

import { useEffect, useState } from "react";
import type { RoundGameTip, UserPicks } from "@/lib/types";
import { buildPicksStorageKey } from "@/lib/useRoundPicks";

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
    const saved = window.localStorage.getItem(buildPicksStorageKey(round));
    if (!saved) return;
    try {
      setPicks(JSON.parse(saved) as UserPicks);
    } catch {
      setPicks(buildInitial(games));
    }
  }, [games, round]);

  useEffect(() => {
    window.localStorage.setItem(buildPicksStorageKey(round), JSON.stringify(picks));
  }, [picks, round]);

  return (
    <section style={{ marginTop: 24 }}>
      <h2 style={{ marginBottom: 12 }}>My Picks</h2>
      <div style={{ display: "grid", gap: 10 }}>
        {games
          .filter((game) => game.status === "upcoming")
          .map((game) => (
            <label
              key={game.gameId}
              style={{ background: "#fff", border: "1px solid #d0d7de", borderRadius: 10, padding: 12 }}
            >
              {game.homeTeam} vs {game.awayTeam}
              <select
                style={{ marginLeft: 8 }}
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
