export type GameStatus = "upcoming" | "live" | "finished";

export interface GameOdds {
  home: number;
  away: number;
}

export interface TipOverride {
  source: string;
  updatedAt: string;
  tipTeam: string;
  reason?: string;
  lineupConfirmed?: boolean;
  keyPlayersOut?: string[];
}

export interface RoundGameTip {
  gameId: string;
  nrlMatchId?: number;
  nrlSlug?: string;
  homeTeam: string;
  awayTeam: string;
  venue: string;
  kickoffAt: string;
  status: GameStatus;
  tipTeam: string;
  confidence: number;
  predictedMargin: number;
  odds?: GameOdds;
  tipOverride?: TipOverride;

  /**
   * Final score/result fields (only present when `status === "finished"`).
   * These are optional because older archive snapshots may not have them.
   */
  homeScore?: number;
  awayScore?: number;
  actualWinner?: string;
  actualMargin?: number;
}

export interface CurrentRoundTips {
  round: number;
  season: number;
  modelVersion: string;
  generatedAt: string;
  lastUpdated?: string;
  marginGameId?: string;
  games: RoundGameTip[];
}

export interface LastUpdateMeta {
  lastSuccessfulUpdateAt: string;
  source: string;
  status: "ok" | "stale" | "error";
}

export interface LadderRow {
  rank: number;
  team: string;
  played: number;
  wins: number;
  losses: number;
  pointsFor: number;
  pointsAgainst: number;
  pointsDiff: number;
  competitionPoints: number;
}

export interface LadderData {
  season: number;
  round: number;
  generatedAt: string;
  rows: LadderRow[];
}

export interface UserPicks {
  winnerByGameId: Record<string, string>;
  marginGameId?: string;
  marginPoints?: number;
}
