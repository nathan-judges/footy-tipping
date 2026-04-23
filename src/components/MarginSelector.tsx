"use client";

import { useEffect, useMemo, useState } from "react";
import type { RoundGameTip } from "@/lib/types";

const MARGIN_KEY = "footy_margin_pick_v1";

interface MarginState {
  marginGameId?: string;
  marginPoints?: number;
}

interface MarginSelectorProps {
  games: RoundGameTip[];
  suggestedGameId?: string;
}

export function MarginSelector({ games, suggestedGameId }: MarginSelectorProps) {
  const upcomingGames = useMemo(() => games.filter((g) => g.status === "upcoming"), [games]);
  const [state, setState] = useState<MarginState>({});

  useEffect(() => {
    const raw = window.localStorage.getItem(MARGIN_KEY);
    if (!raw) {
      setState({ marginGameId: suggestedGameId });
      return;
    }
    try {
      setState(JSON.parse(raw) as MarginState);
    } catch {
      setState({ marginGameId: suggestedGameId });
    }
  }, [suggestedGameId]);

  useEffect(() => {
    window.localStorage.setItem(MARGIN_KEY, JSON.stringify(state));
  }, [state]);

  return (
    <section style={{ margin: "24px 0", background: "#fff", border: "1px solid #d0d7de", borderRadius: 10, padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>Select Your Margin</h2>
      <p style={{ marginTop: 0, color: "#57606a" }}>
        Pick one game for your round margin. Suggested game: <strong>{suggestedGameId ?? "n/a"}</strong>
      </p>
      <div style={{ display: "grid", gap: 10 }}>
        <label>
          Margin game
          <select
            style={{ marginLeft: 8 }}
            value={state.marginGameId ?? ""}
            onChange={(event) => setState((prev) => ({ ...prev, marginGameId: event.target.value || undefined }))}
          >
            <option value="">Select game</option>
            {upcomingGames.map((game) => (
              <option key={game.gameId} value={game.gameId}>
                {game.homeTeam} vs {game.awayTeam}
              </option>
            ))}
          </select>
        </label>
        <label>
          Predicted margin
          <input
            type="number"
            style={{ marginLeft: 8, width: 90 }}
            value={state.marginPoints ?? ""}
            onChange={(event) =>
              setState((prev) => ({
                ...prev,
                marginPoints: event.target.value ? Number(event.target.value) : undefined
              }))
            }
          />
        </label>
      </div>
    </section>
  );
}
