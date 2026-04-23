import Link from "next/link";
import { Ladder } from "@/components/Ladder";
import { RoundView } from "@/components/RoundView";
import { RoundSelector } from "@/components/RoundSelector";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { loadAvailableRoundNumbers } from "@/lib/loadArchive";
import { loadCurrentRoundTips, loadLadder, loadLastUpdateMeta, loadSeasonMeta } from "@/lib/loadTips";

function formatRoundUpdatedLabel(timestamp: string): string {
  return new Date(timestamp).toLocaleString("en-AU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function computeFreshness(lastSuccessfulUpdateAt: string): { label: string; variant: "fresh" | "stale" } {
  const updatedMs = new Date(lastSuccessfulUpdateAt).getTime();
  const ageMs = Date.now() - updatedMs;
  const sixHours = 6 * 60 * 60 * 1000;
  return ageMs <= sixHours ? { label: "Fresh", variant: "fresh" } : { label: "Stale", variant: "stale" };
}

export default function HomePage() {
  const tips = loadCurrentRoundTips();
  const ladder = loadLadder();
  const bakedRounds = loadAvailableRoundNumbers(tips.season);
  const seasonMeta = loadSeasonMeta();
  const lastUpdate = loadLastUpdateMeta();
  const freshness = computeFreshness(lastUpdate.lastSuccessfulUpdateAt);

  return (
    <main className="mx-auto max-w-[860px] px-4 pb-8 pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="mb-2">NRL Tipping</h1>
          <div className="mb-6 flex flex-wrap items-center gap-x-2 gap-y-1 text-muted-foreground">
            <p className="m-0">
              Round {tips.round} ({tips.season}) · Updated {formatRoundUpdatedLabel(tips.lastUpdated ?? tips.generatedAt)}
            </p>
            <span
              className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${
                freshness.variant === "fresh" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"
              }`}
              title={`Last successful update: ${new Date(lastUpdate.lastSuccessfulUpdateAt).toLocaleString("en-AU")} (${lastUpdate.source})`}
            >
              {freshness.label}
            </span>
          </div>
        </div>

        <RoundSelector
          totalRounds={seasonMeta.totalRegularRounds}
          bakedRounds={bakedRounds}
          selectedRound={tips.round}
          currentRound={tips.round}
        />
      </div>
      <p className="mb-6">
        <Link href="/archive">View baked-data archive</Link>
      </p>

      <Tabs defaultValue="round">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="round">Round {tips.round}</TabsTrigger>
          <TabsTrigger value="ladder">Ladder</TabsTrigger>
        </TabsList>

        <TabsContent value="round">
          <RoundView round={tips.round} season={tips.season} games={tips.games} suggestedMarginGameId={tips.marginGameId} />
        </TabsContent>

        <TabsContent value="ladder">
          <Ladder ladder={ladder} />
        </TabsContent>
      </Tabs>
    </main>
  );
}
