import Link from "next/link";
import { RoundView } from "@/components/RoundView";
import { RoundSelector } from "@/components/RoundSelector";
import { RoundSummaryWrapper } from "@/components/RoundSummaryWrapper";
import { loadAvailableRoundNumbers, loadRoundTips } from "@/lib/loadArchive";
import { loadCurrentRoundTips, loadLadder, loadLastUpdateMeta, loadSeasonMeta } from "@/lib/loadTips";
import { Ladder } from "@/components/Ladder";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { computeFreshness, formatRoundUpdatedLabel } from "@/lib/utils";

interface RoundPageProps {
  params: Promise<{ round: string }>;
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
    <main className="mx-auto max-w-[920px] px-4 pb-10 pt-6">
      <section className="mb-5 rounded-2xl border bg-gradient-to-br from-slate-50 to-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="mb-1 text-2xl font-semibold tracking-tight">NRL Tipping</h1>
            {tips ? (
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
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
            ) : <p className="text-sm text-muted-foreground">Round {selectedRound} ({current.season})</p>}
            <p className="mt-2 text-sm">
              <Link href="/" className="text-foreground/80 underline-offset-4 hover:underline">Back to current round</Link>
              {" · "}
              <Link href="/archive" className="text-foreground/80 underline-offset-4 hover:underline">View baked-data archive</Link>
            </p>
          </div>
          <div className="w-full sm:w-auto">
            <RoundSelector
              totalRounds={seasonMeta.totalRegularRounds}
              bakedRounds={bakedRounds}
              selectedRound={selectedRound}
              currentRound={current.round}
            />
          </div>
        </div>
      </section>

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
              <TabsTrigger value="round">Tipping</TabsTrigger>
              <TabsTrigger value="ladder">Ladder</TabsTrigger>
            </TabsList>
            <TabsContent value="round">
              <RoundSummaryWrapper round={tips.round} season={tips.season} games={tips.games} />
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

