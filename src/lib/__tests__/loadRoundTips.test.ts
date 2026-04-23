import { describe, expect, it, vi } from "vitest";

vi.mock("node:fs", () => {
  const state = {
    exists: new Set<string>(),
    dirs: new Map<string, string[]>(),
    files: new Map<string, string>()
  };

  const api = {
    existsSync: (p: string) => state.exists.has(p),
    readdirSync: (p: string) => state.dirs.get(p) ?? [],
    readFileSync: (p: string) => {
      const content = state.files.get(p);
      if (content == null) throw new Error("missing");
      return content;
    }
  };

  return {
    __state: state,
    default: api,
    ...api
  };
});

vi.mock("node:path", async () => {
  const actual = await vi.importActual<typeof import("node:path")>("node:path");
  return actual;
});

vi.mock("../loadTips", () => ({
  loadCurrentRoundTips: () => ({
    round: 9,
    season: 2026,
    modelVersion: "x",
    generatedAt: "2026-04-23T00:00:00Z",
    games: []
  })
}));

import path from "node:path";
import * as fs from "node:fs";
import { loadRoundTips } from "../loadArchive";

function setFsState(next: {
  exists?: string[];
  dirs?: Record<string, string[]>;
  files?: Record<string, unknown>;
}) {
  const state = (fs as unknown as { __state: any }).__state;
  state.exists = new Set(next.exists ?? []);
  state.dirs = new Map(Object.entries(next.dirs ?? {}));
  state.files = new Map(
    Object.entries(next.files ?? {}).map(([k, v]) => [k, JSON.stringify(v)])
  );
}

describe("loadRoundTips", () => {
  it("returns current tips when requesting current round", () => {
    const tips = loadRoundTips(9);
    expect(tips?.round).toBe(9);
    expect(tips?.season).toBe(2026);
  });

  it("prefers data/archive/round_N.json when present", () => {
    const archiveDir = path.join(process.cwd(), "data", "archive");
    const roundFile = path.join(archiveDir, "round_3.json");
    setFsState({
      exists: [archiveDir, roundFile],
      files: {
        [roundFile]: { round: 3, season: 2026, modelVersion: "a", generatedAt: "t", games: [] }
      }
    });

    expect(loadRoundTips(3)?.modelVersion).toBe("a");
  });

  it("falls back to newest *_round_N.json when round_N.json missing", () => {
    const archiveDir = path.join(process.cwd(), "data", "archive");
    const f1 = path.join(archiveDir, "2026-04-01_round_8.json");
    const f2 = path.join(archiveDir, "2026-04-20_round_8.json");
    setFsState({
      exists: [archiveDir, f1, f2],
      dirs: {
        [archiveDir]: ["2026-04-01_round_8.json", "2026-04-20_round_8.json", "other.json"]
      },
      files: {
        [f1]: { round: 8, season: 2026, modelVersion: "old", generatedAt: "t1", games: [] },
        [f2]: { round: 8, season: 2026, modelVersion: "new", generatedAt: "t2", games: [] }
      }
    });

    expect(loadRoundTips(8)?.modelVersion).toBe("new");
  });
});

