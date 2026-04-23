import Link from "next/link";
import { RoundView } from "@/components/RoundView";
import { RoundSelector } from "@/components/RoundSelector";
import { loadAvailableRoundNumbers, loadRoundTips } from "@/lib/loadArchive";
import { loadCurrentRoundTips, loadLadder, loadLastUpdateMeta, loadSeasonMeta } from "@/lib/loadTips";
import { Ladder } from "@/components/Ladder";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface RoundPageProps {
  params: Promise<{ round: string }>;
}

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

export default async function RoundPage({ params }: RoundPageProps) {
  const { round: roundParam } = await params;
  const round = Number(roundParam);

  const current = loadCurrentRoundTips();
  const ladder = loadLadder();
  const seasonMeta = loadSeasonMeta();
  const lastUpdate = loadLastUpdateMeta();
  const freshness = computeFreshness(lastUpdate.lastSuccessfulUpdateAt);

  const tips = Number.isFinite(round) ? loadRoundTips(round) : null;
  const bakedRounds = loadAvailableRoundNumbers(current.season);
  const selectedRound = tips?.round ?? current.round;
  const isFuture = tips != null && tips.round > current.round;

  return (
    <main className="mx-auto max-w-[860px] px-4 pb-8 pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="mb-2">NRL Tipping</h1>
          {tips ? (
            <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-muted-foreground">
              <p className="m-0">
                Round {selectedRound} ({current.season}) · Updated {formatRoundUpdatedLabel(tips.lastUpdated ?? tips.generatedAt)}
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
          ) : <p className="mb-2 text-muted-foreground">Round {selectedRound} ({current.season})</p>}
        </div>

        <RoundSelector
          totalRounds={seasonMeta.totalRegularRounds}
          bakedRounds={bakedRounds}
          selectedRound={selectedRound}
          currentRound={current.round}
        />
      </div>

      <p className="mb-6 mt-2">
        <Link href="/">Back to current round</Link>
        {" · "}
        <Link href="/archive">View baked-data archive</Link>
      </p>

      {!tips ? (
        <p className="rounded-md border bg-card p-3.5">
          No baked snapshot found for round <strong>{roundParam}</strong>.
        </p>
      ) : (
        <>
          {isFuture ? (
            <div className="mb-4 rounded-md border-l-4 border-amber-400 bg-amber-50 p-3">
              <p className="text-sm text-amber-800">
                ⚠️ You&apos;re viewing a future round. Predictions are preliminary and may change as team lists and late mail
                are announced.
              </p>
            </div>
          ) : null}

          <Tabs defaultValue="round">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="round">Round {tips.round}</TabsTrigger>
              <TabsTrigger value="ladder">Ladder</TabsTrigger>
            </TabsList>
            <TabsContent value="round">
              <RoundView
              games={tips.games}
              round={tips.round}
              season={tips.season}
              suggestedMarginGameId={tips.marginGameId}
                mode="all"
                disableInteractions={isFuture}
            />
            </TabsContent>
            <TabsContent value="ladder">
              <Ladder ladder={ladder} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </main>
  );
}

