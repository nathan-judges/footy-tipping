"use client";

import { useEffect, useMemo } from "react";
import type { RoundGameTip } from "@/lib/types";
import { TipCard } from "@/components/TipCard";
import { useRoundPicks } from "@/lib/useRoundPicks";
import { saveUserPicksForRound } from "@/lib/userPicks";

interface RoundViewProps {
  round: number;
  season: number;
  games: RoundGameTip[];
  suggestedMarginGameId?: string;
  mode?: "upcoming" | "all";
  disableInteractions?: boolean;
}

export function RoundView({
  round,
  season,
  games,
  suggestedMarginGameId,
  mode = "upcoming",
  disableInteractions = false
}: RoundViewProps) {
  const { picks, setPicks, updateWinnerPick } = useRoundPicks(round, games);
  const visibleGames = mode === "all" ? games : games.filter((game) => game.status === "upcoming");
  const marginGames = games.filter((game) => game.status === "upcoming");

  const selectedMarginGame = useMemo(
    () => games.find((game) => game.gameId === picks.marginGameId) ?? null,
    [games, picks.marginGameId]
  );

  useEffect(() => {
    if (marginGames.length === 0) return;
    const fallbackMarginGameId = suggestedMarginGameId ?? marginGames[0]?.gameId;
    if (!fallbackMarginGameId) return;

    const modelMargin =
      games.find((game) => game.gameId === (picks.marginGameId ?? fallbackMarginGameId))?.predictedMargin ?? undefined;

    if (picks.marginGameId && typeof picks.marginPoints === "number") return;

    const next = {
      ...picks,
      marginGameId: picks.marginGameId ?? fallbackMarginGameId,
      marginPoints: typeof picks.marginPoints === "number" ? picks.marginPoints : modelMargin
    };
    setPicks(next);
    saveUserPicksForRound(round, next);
  }, [games, marginGames, picks, round, setPicks, suggestedMarginGameId]);

  function updateMargin(marginGameId: string | undefined, marginPoints: number | undefined) {
    const next = { ...picks, marginGameId, marginPoints };
    setPicks(next);
    saveUserPicksForRound(round, next);
  }

  return (
    <section className="space-y-3">
      {visibleGames.length === 0 ? (
        <p>No upcoming games available for tipping yet.</p>
      ) : (
        visibleGames.map((game) => (
          <TipCard
            key={game.gameId}
            round={round}
            season={season}
            game={game}
            userPick={picks.winnerByGameId[game.gameId]}
            onPickChange={disableInteractions ? undefined : updateWinnerPick}
            disablePicks={disableInteractions}
          />
        ))
      )}

      <div className="rounded-md border bg-card p-4">
        <h3 className="m-0 text-sm font-semibold">Margin</h3>
        <div className="mt-2 grid grid-cols-1 gap-3 md:grid-cols-3">
          <label className="block">
            <span className="text-xs text-muted-foreground">Margin game</span>
            <select
              className="mt-1.5 w-full rounded-md border bg-background px-2.5 py-2"
              value={picks.marginGameId ?? ""}
              disabled={disableInteractions}
              onChange={(event) => {
                const marginGameId = event.target.value || undefined;
                const modelMargin =
                  (marginGameId ? games.find((game) => game.gameId === marginGameId)?.predictedMargin : undefined) ??
                  undefined;
                updateMargin(marginGameId, typeof picks.marginPoints === "number" ? picks.marginPoints : modelMargin);
              }}
            >
              <option value="">Select game</option>
              {marginGames.map((game) => (
                <option key={game.gameId} value={game.gameId}>
                  {game.homeTeam} vs {game.awayTeam}
                </option>
              ))}
            </select>
          </label>

          <div>
            <span className="text-xs text-muted-foreground">Model spread</span>
            <div className="mt-1.5 rounded-md border bg-background px-2.5 py-2 text-sm tabular-nums">
              {selectedMarginGame ? `${selectedMarginGame.predictedMargin >= 0 ? "+" : ""}${selectedMarginGame.predictedMargin}` : "—"}
            </div>
          </div>

          <label className="block">
            <span className="text-xs text-muted-foreground">Your margin</span>
            <input
              type="number"
              className="mt-1.5 w-full rounded-md border bg-background px-2.5 py-2"
              value={picks.marginPoints ?? ""}
              disabled={disableInteractions}
              onChange={(event) =>
                updateMargin(
                  picks.marginGameId,
                  event.target.value === "" ? undefined : Number(event.target.value)
                )
              }
            />
          </label>
        </div>
      </div>
    </section>
  );
}

