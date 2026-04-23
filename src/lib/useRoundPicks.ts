"use client";

import { useEffect, useMemo, useState } from "react";
import type { RoundGameTip, UserPicks } from "@/lib/types";

export function buildPicksStorageKey(round: number) {
  return `nrl_tipping_picks_round_${round}`;
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
    const saved = window.localStorage.getItem(storageKey);
    if (!saved) {
      setHasSavedPicks(false);
      setPicks(buildInitial(games));
      return;
    }
    try {
      const parsed = JSON.parse(saved) as UserPicks;
      setPicks(parsed);
      setHasSavedPicks(true);
    } catch {
      setHasSavedPicks(false);
      setPicks(buildInitial(games));
    }
  }, [games, storageKey]);

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(picks));
    setHasSavedPicks(true);
  }, [picks, storageKey]);

  return { picks, setPicks, hasSavedPicks, storageKey };
}

