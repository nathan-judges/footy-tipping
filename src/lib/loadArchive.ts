import fs from "node:fs";
import path from "node:path";
import { loadCurrentRoundTips } from "./loadTips";
import type { CurrentRoundTips } from "./types";

export interface ArchiveRoundEntry {
  id: string;
  round: number;
  season: number;
  generatedAt: string;
  modelVersion: string;
  gameCount: number;
  marginGameId?: string;
}

const ARCHIVE_DIR = path.join(process.cwd(), "data", "archive");

export function loadArchiveRounds(): ArchiveRoundEntry[] {
  const rounds: CurrentRoundTips[] = [];

  if (fs.existsSync(ARCHIVE_DIR)) {
    const archiveFiles = fs
      .readdirSync(ARCHIVE_DIR)
      .filter((fileName) => fileName.endsWith(".json"))
      .sort();

    for (const fileName of archiveFiles) {
      const filePath = path.join(ARCHIVE_DIR, fileName);
      try {
        const raw = fs.readFileSync(filePath, "utf8");
        const parsed = JSON.parse(raw) as Partial<CurrentRoundTips>;
        if (isCurrentRoundTips(parsed)) {
          rounds.push(parsed);
        }
      } catch {
        // Ignore malformed snapshots so one bad file does not break archive page.
      }
    }
  }

  rounds.push(loadCurrentRoundTips());

  const dedupedById = new Map<string, ArchiveRoundEntry>();
  for (const entry of rounds) {
    const id = `${entry.season}-r${String(entry.round).padStart(2, "0")}`;
    dedupedById.set(id, {
      id,
      round: entry.round,
      season: entry.season,
      generatedAt: entry.generatedAt,
      modelVersion: entry.modelVersion,
      gameCount: entry.games.length,
      marginGameId: entry.marginGameId
    });
  }

  return Array.from(dedupedById.values()).sort(
    (a, b) => new Date(b.generatedAt).getTime() - new Date(a.generatedAt).getTime()
  );
}

export function loadAvailableRoundNumbers(season?: number): number[] {
  const rounds = loadArchiveRounds()
    .filter((entry) => (season ? entry.season === season : true))
    .map((entry) => entry.round);

  return Array.from(new Set(rounds)).sort((a, b) => a - b);
}

export function loadRoundTips(round: number): CurrentRoundTips | null {
  const current = loadCurrentRoundTips();
  if (round === current.round) return current;

  const archiveDirExists = fs.existsSync(ARCHIVE_DIR);
  if (!archiveDirExists) return null;

  const roundFileName = `round_${round}.json`;
  const roundFilePath = path.join(ARCHIVE_DIR, roundFileName);
  if (fs.existsSync(roundFilePath)) {
    return readTipsSnapshot(roundFilePath);
  }

  const candidates = fs
    .readdirSync(ARCHIVE_DIR)
    .filter((fileName) => fileName.endsWith(`_round_${round}.json`))
    .sort();

  if (candidates.length === 0) return null;

  const newestCandidate = candidates[candidates.length - 1];
  return readTipsSnapshot(path.join(ARCHIVE_DIR, newestCandidate));
}

function isCurrentRoundTips(payload: Partial<CurrentRoundTips>): payload is CurrentRoundTips {
  return (
    typeof payload.round === "number" &&
    typeof payload.season === "number" &&
    typeof payload.modelVersion === "string" &&
    typeof payload.generatedAt === "string" &&
    Array.isArray(payload.games)
  );
}

function readTipsSnapshot(filePath: string): CurrentRoundTips | null {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    const parsed = JSON.parse(raw) as Partial<CurrentRoundTips>;
    return isCurrentRoundTips(parsed) ? parsed : null;
  } catch {
    return null;
  }
}
