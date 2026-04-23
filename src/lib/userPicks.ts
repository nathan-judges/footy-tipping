import type { UserPicks } from "@/lib/types";

const STORAGE_PREFIX = "nrl_tipping_picks_round_";

export function getUserPicksStorageKey(round: number): string {
  return `${STORAGE_PREFIX}${round}`;
}

export function getUserPicksForRound(round: number): UserPicks | null {
  if (typeof window === "undefined") return null;
  const stored = window.localStorage.getItem(getUserPicksStorageKey(round));
  if (!stored) return null;
  try {
    return JSON.parse(stored) as UserPicks;
  } catch {
    return null;
  }
}

export function saveUserPicksForRound(round: number, picks: UserPicks): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(getUserPicksStorageKey(round), JSON.stringify(picks));
}

export function saveUserPick(round: number, gameId: string, pick: string): void {
  if (typeof window === "undefined") return;
  const current = getUserPicksForRound(round) ?? { winnerByGameId: {} };
  current.winnerByGameId[gameId] = pick;
  saveUserPicksForRound(round, current);
}
