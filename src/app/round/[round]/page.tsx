import Link from "next/link";
import { RoundInteractive } from "@/components/RoundInteractive";
import { RoundSelector } from "@/components/RoundSelector";
import { loadAvailableRoundNumbers, loadRoundTips } from "@/lib/loadArchive";
import { loadCurrentRoundTips, loadLadder, loadLastUpdateMeta } from "@/lib/loadTips";
import { Ladder } from "@/components/Ladder";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface RoundPageProps {
  params: Promise<{ round: string }>;
}

export default async function RoundPage({ params }: RoundPageProps) {
  const { round: roundParam } = await params;
  const round = Number(roundParam);

  const current = loadCurrentRoundTips();
  const lastUpdate = loadLastUpdateMeta();
  const ladder = loadLadder();

  const tips = Number.isFinite(round) ? loadRoundTips(round) : null;
  const availableRounds = loadAvailableRoundNumbers(current.season);
  const selectedRound = tips?.round ?? current.round;

  return (
    <main className="mx-auto max-w-[860px] px-4 pb-8 pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="mb-2">NRL Tipping</h1>
          <p className="mb-2 text-muted-foreground">
            Round {selectedRound} ({current.season}) - model {tips?.modelVersion ?? current.modelVersion}
          </p>
          <p className="mb-2 text-muted-foreground">
            Last update: {new Date(lastUpdate.lastSuccessfulUpdateAt).toLocaleString("en-AU")}
          </p>
        </div>

        <RoundSelector rounds={availableRounds} selectedRound={selectedRound} />
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
        <Tabs defaultValue="tips">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="tips">Tips</TabsTrigger>
            <TabsTrigger value="ladder">Ladder</TabsTrigger>
          </TabsList>
          <TabsContent value="tips">
            <RoundInteractive round={tips.round} season={tips.season} games={tips.games} mode="all" />
          </TabsContent>
          <TabsContent value="ladder">
            <Ladder ladder={ladder} />
          </TabsContent>
        </Tabs>
      )}
    </main>
  );
}

