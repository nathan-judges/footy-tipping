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

  useEffect(() => {
    if (marginGames.length === 0) return;
    const fallbackMarginGameId = suggestedMarginGameId ?? marginGames[0]?.gameId;
    if (!fallbackMarginGameId) return;
    if (picks.marginGameId) return;

    const suggested = games.find((game) => game.gameId === fallbackMarginGameId);
    if (!suggested) return;

    const nextWinnerByGameId = { ...picks.winnerByGameId };
    if (!nextWinnerByGameId[suggested.gameId]) {
      nextWinnerByGameId[suggested.gameId] = suggested.tipTeam;
    }

    const next = {
      ...picks,
      winnerByGameId: nextWinnerByGameId,
      marginGameId: suggested.gameId,
      marginPoints: suggested.predictedMargin
    };
    setPicks(next);
    saveUserPicksForRound(round, next);
  }, [games, marginGames, picks, round, setPicks, suggestedMarginGameId]);

  const marginGame = useMemo(
    () => (picks.marginGameId ? games.find((game) => game.gameId === picks.marginGameId) ?? null : null),
    [games, picks.marginGameId]
  );

  function setMarginGame(game: RoundGameTip) {
    if (game.status !== "upcoming") return;
    const nextWinnerByGameId = { ...picks.winnerByGameId };
    if (!nextWinnerByGameId[game.gameId]) {
      nextWinnerByGameId[game.gameId] = game.tipTeam;
    }

    const next = {
      ...picks,
      winnerByGameId: nextWinnerByGameId,
      marginGameId: game.gameId,
      marginPoints: typeof picks.marginPoints === "number" ? picks.marginPoints : game.predictedMargin
    };
    setPicks(next);
    saveUserPicksForRound(round, next);
  }

  function updateMarginPoints(points: number | undefined) {
    const next = { ...picks, marginPoints: points };
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
            isMarginGame={picks.marginGameId === game.gameId}
            marginPoints={picks.marginGameId === game.gameId ? picks.marginPoints : undefined}
            modelMargin={game.predictedMargin}
            onSetMarginGame={disableInteractions ? undefined : () => setMarginGame(game)}
            onMarginPointsChange={disableInteractions ? undefined : updateMarginPoints}
          />
        ))
      )}
    </section>
  );
}

