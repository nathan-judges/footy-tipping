import { loadCurrentRoundTips } from "@/lib/loadTips";
import type { RoundGameTip, TipOverride } from "@/lib/types";

export const runtime = "edge";

const REQUEST_TIMEOUT_MS = 3000;
const USER_AGENT = "FootyTippingBot/1.0";

type NrlLineupPlayer = {
  teamSide: "home" | "away";
  playerName: string;
  status?: string;
  role?: "starting" | "interchange" | "reserve";
  number?: number;
};

export async function GET(request: Request) {
  const url = new URL(request.url);
  const gameId = url.searchParams.get("gameId");
  if (!gameId) {
    return Response.json({ error: "gameId is required" }, { status: 400 });
  }

  const tips = loadCurrentRoundTips();
  const game = tips.games.find((entry) => entry.gameId === gameId);
  if (!game) {
    return Response.json({ error: "game not found" }, { status: 404 });
  }

  let tipOverride: TipOverride | null = null;
  let reason = "no late lineup changes detected";
  let source = "nrl-match-centre";

  try {
    tipOverride = await fetchLiveOverride(game, tips.season, tips.round);
  } catch (error) {
    const message = error instanceof Error ? error.message : "unknown error";
    reason = `live scrape failed softly: ${message}`;
    source = "nrl-match-centre-error";
  }

  if (tipOverride?.reason) {
    reason = tipOverride.reason;
    source = tipOverride.source;
  }

  return Response.json({
    gameId,
    tipOverride,
    source,
    reason,
    checkedAt: new Date().toISOString()
  });
}

async function fetchLiveOverride(
  game: RoundGameTip,
  season: number,
  round: number
): Promise<TipOverride | null> {
  const jsonPayload = await fetchMatchJsonPayload(game.nrlMatchId);
  if (jsonPayload) {
    const jsonOverride = deriveTipOverrideFromPayload(game, jsonPayload, "nrl-match-centre-json");
    if (jsonOverride) return jsonOverride;
  }

  const slug = game.nrlSlug ?? fallbackGameSlug(game);
  if (!slug) return null;

  const html = await fetchMatchHtml({ slug, season, round });
  if (!html) return null;

  const embeddedPayload = extractEmbeddedMatchData(html);
  if (embeddedPayload) {
    const embeddedOverride = deriveTipOverrideFromPayload(game, embeddedPayload, "nrl-match-centre-embedded");
    if (embeddedOverride) return embeddedOverride;
  }

  const htmlSignals = detectOutSignalsFromHtml(html);
  return buildOverrideFromOutSignals(game, htmlSignals, "nrl-team-list-html");
}

async function fetchMatchJsonPayload(matchId?: number): Promise<unknown | null> {
  if (!matchId) return null;
  const endpoints = [
    `https://www.nrl.com/match-centre/api/match/${matchId}`,
    `https://www.nrl.com/match-centre/api/matches/${matchId}`,
    `https://www.nrl.com/api/match-centre/match/${matchId}`
  ];

  for (const endpoint of endpoints) {
    const response = await safeFetch(endpoint);
    if (!response?.ok) continue;
    const payload = await safeJson(response);
    if (payload) return payload;
  }
  return null;
}

async function fetchMatchHtml({
  slug,
  season,
  round
}: {
  slug: string;
  season: number;
  round: number;
}): Promise<string | null> {
  const url = `https://www.nrl.com/draw/nrl-premiership/${season}/round-${round}/${slug}/`;
  const response = await safeFetch(url);
  if (!response?.ok) return null;
  return response.text();
}

async function safeFetch(url: string): Promise<Response | null> {
  try {
    return await fetch(url, {
      headers: { "User-Agent": USER_AGENT },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
    });
  } catch {
    return null;
  }
}

async function safeJson(response: Response): Promise<unknown | null> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function deriveTipOverrideFromPayload(
  game: RoundGameTip,
  payload: unknown,
  source: string
): TipOverride | null {
  const players = collectPlayers(payload);
  if (players.length === 0) return null;
  return buildOverrideFromLineup(game, players, source);
}

function collectPlayers(payload: unknown): NrlLineupPlayer[] {
  const flattened = flattenObjects(payload);
  const players: NrlLineupPlayer[] = [];

  for (const node of flattened) {
    if (!node || typeof node !== "object") continue;
    const rawName = getString(node, ["displayName", "name", "fullName", "playerName"]);
    if (!rawName) continue;

    const status = getString(node, ["status", "teamListStatus", "availability"]);
    const side = inferTeamSide(node);
    if (!side) continue;

    const role = inferPlayerRole(node);
    const number = getNumber(node, ["number", "jerseyNumber", "shirtNumber", "positionNumber"]);

    players.push({
      teamSide: side,
      playerName: rawName,
      status,
      role,
      number
    });
  }

  return players;
}

function buildOverrideFromLineup(
  game: RoundGameTip,
  players: NrlLineupPlayer[],
  source: string
): TipOverride | null {
  const homeOuts = extractImportantOuts(players, "home");
  const awayOuts = extractImportantOuts(players, "away");

  if (homeOuts.length === 0 && awayOuts.length === 0) return null;
  return buildOverrideFromOutLists(game, homeOuts, awayOuts, source);
}

function buildOverrideFromOutSignals(
  game: RoundGameTip,
  signals: { homeOuts: string[]; awayOuts: string[] },
  source: string
): TipOverride | null {
  return buildOverrideFromOutLists(game, signals.homeOuts, signals.awayOuts, source);
}

function buildOverrideFromOutLists(
  game: RoundGameTip,
  homeOuts: string[],
  awayOuts: string[],
  source: string
): TipOverride | null {
  if (homeOuts.length === 0 && awayOuts.length === 0) return null;
  if (homeOuts.length === awayOuts.length) return null;

  const homeHarderHit = homeOuts.length > awayOuts.length;
  const tipTeam = homeHarderHit ? game.awayTeam : game.homeTeam;
  const impactedTeam = homeHarderHit ? game.homeTeam : game.awayTeam;
  const keyPlayersOut = (homeHarderHit ? homeOuts : awayOuts).slice(0, 5);

  return {
    source,
    updatedAt: new Date().toISOString(),
    tipTeam,
    reason: `late changes for ${impactedTeam}: ${keyPlayersOut.join(", ")}`,
    lineupConfirmed: true,
    keyPlayersOut
  };
}

function extractImportantOuts(players: NrlLineupPlayer[], side: "home" | "away"): string[] {
  const sidePlayers = players.filter((player) => player.teamSide === side);
  return sidePlayers
    .filter((player) => isOutStatus(player.status) && isKeyLineupRole(player))
    .map((player) => player.playerName);
}

function isKeyLineupRole(player: NrlLineupPlayer): boolean {
  if (player.role === "starting" || player.role === "interchange") return true;
  if (typeof player.number === "number") return player.number >= 1 && player.number <= 17;
  return false;
}

function isOutStatus(status?: string): boolean {
  if (!status) return false;
  return /\b(out|withdrawn|scratched|late out)\b/i.test(status);
}

function inferTeamSide(node: Record<string, unknown>): "home" | "away" | null {
  const sideValue = getString(node, ["teamSide", "side", "teamType", "team"]);
  if (sideValue) {
    if (/home/i.test(sideValue)) return "home";
    if (/away|visitor/i.test(sideValue)) return "away";
  }

  const teamName = getString(node, ["teamName", "teamDisplayName"]);
  if (teamName) {
    if (/home/i.test(teamName)) return "home";
    if (/away/i.test(teamName)) return "away";
  }

  return null;
}

function inferPlayerRole(node: Record<string, unknown>): "starting" | "interchange" | "reserve" | undefined {
  const role = getString(node, ["role", "listRole", "squad", "group"]);
  if (!role) return undefined;
  if (/start|starting|run-on|first/i.test(role)) return "starting";
  if (/interchange|bench/i.test(role)) return "interchange";
  if (/reserve|extended/i.test(role)) return "reserve";
  return undefined;
}

function detectOutSignalsFromHtml(html: string): { homeOuts: string[]; awayOuts: string[] } {
  const normalized = html.replace(/\s+/g, " ");
  const homeOuts = extractOutsByTeamClass(normalized, "home");
  const awayOuts = extractOutsByTeamClass(normalized, "away");
  return { homeOuts, awayOuts };
}

function extractOutsByTeamClass(html: string, teamClass: "home" | "away"): string[] {
  const sectionRegex = new RegExp(`${teamClass}[\\w\\-\\s\\"]{0,1200}?(?:OUT|Late Out|Withdrawn)`, "gi");
  const snippets = html.match(sectionRegex) ?? [];
  return snippets.map((snippet, index) => `${teamClass.toUpperCase()} OUT ${index + 1}`);
}

function extractEmbeddedMatchData(html: string): unknown | null {
  const nextDataMatch = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/i);
  if (nextDataMatch?.[1]) {
    try {
      return JSON.parse(nextDataMatch[1]);
    } catch {
      return null;
    }
  }

  const hydrationMatch = html.match(/window\.__INITIAL_STATE__\s*=\s*({[\s\S]*?});/i);
  if (hydrationMatch?.[1]) {
    try {
      return JSON.parse(hydrationMatch[1]);
    } catch {
      return null;
    }
  }

  return null;
}

function flattenObjects(input: unknown): Record<string, unknown>[] {
  if (!input || typeof input !== "object") return [];
  const results: Record<string, unknown>[] = [];
  const queue: unknown[] = [input];
  const seen = new Set<object>();

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || typeof current !== "object") continue;
    if (seen.has(current)) continue;
    seen.add(current);

    if (!Array.isArray(current)) {
      results.push(current as Record<string, unknown>);
    }

    for (const value of Object.values(current)) {
      if (value && typeof value === "object") queue.push(value);
    }
  }

  return results;
}

function getString(node: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = node[key];
    if (typeof value === "string" && value.trim().length > 0) return value.trim();
  }
  return undefined;
}

function getNumber(node: Record<string, unknown>, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = node[key];
    if (typeof value === "number") return value;
    if (typeof value === "string" && value.trim() !== "") {
      const parsed = Number(value);
      if (!Number.isNaN(parsed)) return parsed;
    }
  }
  return undefined;
}

function fallbackGameSlug(game: RoundGameTip): string {
  return `${slugify(game.homeTeam)}-vs-${slugify(game.awayTeam)}`;
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}
