"use client";

import { useEffect, useMemo, useState } from "react";
import type { RoundGameTip, UserPicks } from "@/lib/types";
import { getUserPicksForRound, getUserPicksStorageKey, saveUserPicksForRound } from "@/lib/userPicks";

export function buildPicksStorageKey(round: number) {
  return getUserPicksStorageKey(round);
}

function buildInitial(games: RoundGameTip[]): UserPicks {
  const winnerByGameId: Record<string, string> = {};
  games.forEach((game) => {
    winnerByGameId[game.gameId] = game.tipTeam;
  });
  return { winnerByGameId };
}

export function useRoundPicks(round: number, games: RoundGameTip[]) {
  const storageKey = useMemo(() => buildPicksStorageKey(round), [round]);
  const [hasSavedPicks, setHasSavedPicks] = useState(false);
  const [picks, setPicks] = useState<UserPicks>(() => buildInitial(games));

  useEffect(() => {
    const saved = getUserPicksForRound(round);
    if (!saved) {
      setHasSavedPicks(false);
      setPicks(buildInitial(games));
      return;
    }
    setPicks(saved);
    setHasSavedPicks(true);
  }, [games, round, storageKey]);

  useEffect(() => {
    saveUserPicksForRound(round, picks);
    setHasSavedPicks(true);
  }, [picks, round, storageKey]);

  return { picks, setPicks, hasSavedPicks, storageKey };
}

