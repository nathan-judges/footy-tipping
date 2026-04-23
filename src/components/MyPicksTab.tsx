"use client";

import { useEffect, useMemo, useState } from "react";
import type { RoundGameTip, UserPicks } from "@/lib/types";
import { getUserPicksForRound, saveUserPicksForRound } from "@/lib/userPicks";

interface MyPicksTabProps {
  games: RoundGameTip[];
  round: number;
  season: number;
  suggestedMarginGameId?: string;
  disabled?: boolean;
}

function buildDefaultPicks(games: RoundGameTip[], suggestedMarginGameId?: string): UserPicks {
  const winnerByGameId: Record<string, string> = {};
  games.forEach((game) => {
    winnerByGameId[game.gameId] = game.tipTeam;
  });

  const marginGameId =
    suggestedMarginGameId ??
    games.find((g) => g.status === "upcoming")?.gameId ??
    games[0]?.gameId ??
    undefined;

  const marginPoints =
    (marginGameId ? games.find((g) => g.gameId === marginGameId)?.predictedMargin : undefined) ?? undefined;

  return { winnerByGameId, marginGameId, marginPoints };
}

export function MyPicksTab({ games, round, season, suggestedMarginGameId, disabled }: MyPicksTabProps) {
  const [draft, setDraft] = useState<UserPicks>(() => buildDefaultPicks(games, suggestedMarginGameId));
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  useEffect(() => {
    const saved = getUserPicksForRound(round);
    if (saved) {
      setDraft(saved);
      return;
    }
    setDraft(buildDefaultPicks(games, suggestedMarginGameId));
  }, [games, round, suggestedMarginGameId]);

  const upcomingGames = useMemo(() => games.filter((g) => g.status === "upcoming"), [games]);

  const selectedMarginGame = useMemo(
    () => games.find((g) => g.gameId === draft.marginGameId) ?? null,
    [draft.marginGameId, games]
  );

  function setWinner(gameId: string, team: string) {
    setDraft((prev) => ({ ...prev, winnerByGameId: { ...prev.winnerByGameId, [gameId]: team } }));
  }

  function saveAll() {
    saveUserPicksForRound(round, draft);
    setSavedAt(new Date());
  }

  const roundLabel = `Round ${round} (${season})`;

  return (
    <section className="mt-4 space-y-4">
      <div>
        <h2 className="mb-1.5">My Picks</h2>
        <p className="text-sm text-muted-foreground">{roundLabel}</p>
      </div>

      <div className="rounded-md border bg-card p-4">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="m-0 text-base font-semibold">Margin</h3>
          {savedAt ? <p className="m-0 text-xs text-muted-foreground">Saved {savedAt.toLocaleTimeString("en-AU")}</p> : null}
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <label className="block">
            <span className="text-sm text-muted-foreground">Margin game</span>
            <select
              className="mt-1.5 w-full rounded-md border bg-background px-2.5 py-2"
              value={draft.marginGameId ?? ""}
              disabled={disabled}
              onChange={(event) => {
                const marginGameId = event.target.value || undefined;
                const modelMargin =
                  (marginGameId ? games.find((g) => g.gameId === marginGameId)?.predictedMargin : undefined) ?? undefined;
                setDraft((prev) => ({
                  ...prev,
                  marginGameId,
                  marginPoints: prev.marginPoints ?? modelMargin
                }));
              }}
            >
              <option value="">Select game</option>
              {upcomingGames.map((game) => (
                <option key={game.gameId} value={game.gameId}>
                  {game.homeTeam} vs {game.awayTeam}
                </option>
              ))}
            </select>
          </label>

          <div className="block">
            <span className="text-sm text-muted-foreground">Model spread</span>
            <div className="mt-2 rounded-md border bg-background px-3 py-2 text-sm tabular-nums">
              {selectedMarginGame ? (selectedMarginGame.predictedMargin >= 0 ? "+" : "") + selectedMarginGame.predictedMargin : "—"}
            </div>
          </div>

          <label className="block">
            <span className="text-sm text-muted-foreground">Your margin</span>
            <input
              type="number"
              className="mt-1.5 w-full rounded-md border bg-background px-2.5 py-2"
              value={draft.marginPoints ?? ""}
              disabled={disabled}
              onChange={(event) =>
                setDraft((prev) => ({
                  ...prev,
                  marginPoints: event.target.value ? Number(event.target.value) : undefined
                }))
              }
            />
          </label>
        </div>

        {disabled ? (
          <p className="mt-3 text-sm text-muted-foreground">Picks locked until team lists are announced.</p>
        ) : (
          <button
            type="button"
            className="mt-3 inline-flex items-center justify-center rounded-md bg-black px-3 py-2 text-sm font-semibold text-white hover:bg-black/90"
            onClick={saveAll}
          >
            Save All Picks
          </button>
        )}
      </div>

      <div className="grid gap-2.5">
        {games.map((game) => {
          const current = draft.winnerByGameId[game.gameId] ?? game.tipTeam;
          return (
            <div key={game.gameId} className="rounded-md border bg-card p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="m-0 truncate text-sm font-semibold">
                    {game.homeTeam} vs {game.awayTeam}
                  </p>
                  <p className="m-0 text-xs text-muted-foreground">
                    {new Date(game.kickoffAt).toLocaleString("en-AU", { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-1.5">
                  <button
                    type="button"
                    disabled={disabled}
                    className={`rounded-md border px-2.5 py-1.5 text-sm font-semibold ${
                      current === game.homeTeam ? "bg-foreground text-background" : "bg-background"
                    }`}
                    onClick={() => setWinner(game.gameId, game.homeTeam)}
                  >
                    {game.homeTeam}
                  </button>
                  <button
                    type="button"
                    disabled={disabled}
                    className={`rounded-md border px-2.5 py-1.5 text-sm font-semibold ${
                      current === game.awayTeam ? "bg-foreground text-background" : "bg-background"
                    }`}
                    onClick={() => setWinner(game.gameId, game.awayTeam)}
                  >
                    {game.awayTeam}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

