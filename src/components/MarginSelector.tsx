"use client";

import { useEffect, useMemo, useState } from "react";
import type { RoundGameTip } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";

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
    <Card className="my-[18px]">
      <CardContent>
        <h2 className="mt-0">Select Your Margin</h2>
        <p className="mt-0 text-muted-foreground">
          Pick one game for your round margin. Suggested game: <strong>{suggestedGameId ?? "n/a"}</strong>
        </p>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(230px,1fr))] gap-2.5">
          <label>
            <span className="mr-2">Margin game</span>
          <select
            className="mt-1.5 w-full rounded-md border bg-background px-2.5 py-2"
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
            <span className="mr-2">Predicted margin</span>
            <input
              type="number"
              className="mt-1.5 w-full rounded-md border bg-background px-2.5 py-2"
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
      </CardContent>
    </Card>
  );
}
