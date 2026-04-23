import type { RoundGameTip, UserPicks } from "@/lib/types";

export function resolveActualWinner(game: RoundGameTip): string | null {
  if (typeof game.actualWinner === "string" && game.actualWinner.trim().length > 0) return game.actualWinner;
  if (typeof game.homeScore !== "number" || typeof game.awayScore !== "number") return null;
  if (game.homeScore === game.awayScore) return null;
  return game.homeScore > game.awayScore ? game.homeTeam : game.awayTeam;
}

export function resolveActualMargin(game: RoundGameTip): number | null {
  if (typeof game.actualMargin === "number") return game.actualMargin;
  if (typeof game.homeScore !== "number" || typeof game.awayScore !== "number") return null;
  if (game.homeScore === game.awayScore) return 0;
  const winner = resolveActualWinner(game);
  if (!winner) return null;
  const rawMargin = Math.abs(game.homeScore - game.awayScore);
  return winner === game.homeTeam ? rawMargin : -rawMargin;
}

export function isModelCorrect(game: RoundGameTip): boolean | null {
  const actualWinner = resolveActualWinner(game);
  if (!actualWinner) return null;
  return game.tipTeam === actualWinner;
}

export function isUserCorrect(game: RoundGameTip, userPick: string | null | undefined): boolean | null {
  const actualWinner = resolveActualWinner(game);
  if (!actualWinner) return null;
  if (!userPick) return null;
  return userPick === actualWinner;
}

export interface RoundAccuracySummary {
  finishedGamesWithResult: number;
  modelCorrect: number;
  userCorrect: number | null;
  userPicksCount: number;
}

export function calculateRoundAccuracy(games: RoundGameTip[], userPicks?: UserPicks | null): RoundAccuracySummary {
  const finished = games.filter((g) => g.status === "finished");
  const finishedWithResult = finished.filter((g) => resolveActualWinner(g) != null);

  const modelCorrect = finishedWithResult.reduce((acc, g) => (isModelCorrect(g) ? acc + 1 : acc), 0);

  const pickMap = userPicks?.winnerByGameId ?? {};
  const userPicksCount = finishedWithResult.reduce((acc, g) => (pickMap[g.gameId] ? acc + 1 : acc), 0);
  const userCorrect =
    userPicksCount === 0
      ? null
      : finishedWithResult.reduce((acc, g) => (isUserCorrect(g, pickMap[g.gameId]) ? acc + 1 : acc), 0);

  return {
    finishedGamesWithResult: finishedWithResult.length,
    modelCorrect,
    userCorrect,
    userPicksCount
  };
}

