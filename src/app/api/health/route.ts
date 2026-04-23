import { loadCurrentRoundTips, loadLastUpdateMeta } from "@/lib/loadTips";

export const runtime = "edge";

export async function GET() {
  const meta = loadLastUpdateMeta();
  const roundTips = loadCurrentRoundTips();
  const lastUpdateMs = new Date(meta.lastSuccessfulUpdateAt).getTime();
  const ageHours = Number(((Date.now() - lastUpdateMs) / (1000 * 60 * 60)).toFixed(2));
  const staleByAge = ageHours > 168;
  const staleBySource = meta.status === "stale" || meta.status === "error";
  const status = staleByAge || staleBySource ? "stale" : "ok";
  const nextKickoffAt = roundTips.games
    .filter((game) => game.status === "upcoming")
    .map((game) => game.kickoffAt)
    .sort((a, b) => new Date(a).getTime() - new Date(b).getTime())[0] ?? null;

  return Response.json({
    status,
    ageHours,
    sourceStatus: meta.status,
    lastSuccessfulUpdateAt: meta.lastSuccessfulUpdateAt,
    nextKickoffAt
  });
}
