import Link from "next/link";
import { Ladder } from "@/components/Ladder";
import { MyPicksTab } from "@/components/MyPicksTab";
import { RoundInteractive } from "@/components/RoundInteractive";
import { RoundSelector } from "@/components/RoundSelector";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { loadAvailableRoundNumbers } from "@/lib/loadArchive";
import { loadCurrentRoundTips, loadLadder, loadLastUpdateMeta } from "@/lib/loadTips";

export default function HomePage() {
  const tips = loadCurrentRoundTips();
  const lastUpdate = loadLastUpdateMeta();
  const ladder = loadLadder();
  const availableRounds = loadAvailableRoundNumbers(tips.season);

  return (
    <main className="mx-auto max-w-[860px] px-4 pb-8 pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="mb-2">NRL Tipping</h1>
          <p className="mb-2 text-muted-foreground">
            Round {tips.round} ({tips.season}) - model {tips.modelVersion}
          </p>
          <p className="mb-2 text-muted-foreground">
            Updated {new Date(tips.lastUpdated ?? tips.generatedAt).toLocaleString("en-AU")}
          </p>
          <p className="mb-6 text-muted-foreground">
            Last update: {new Date(lastUpdate.lastSuccessfulUpdateAt).toLocaleString("en-AU")}
          </p>
        </div>

        <RoundSelector rounds={availableRounds} selectedRound={tips.round} currentRound={tips.round} />
      </div>
      <p className="mb-6">
        <Link href="/archive">View baked-data archive</Link>
      </p>

      <Tabs defaultValue="tips">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="tips">Tips</TabsTrigger>
          <TabsTrigger value="my-picks">My Picks</TabsTrigger>
          <TabsTrigger value="ladder">Ladder</TabsTrigger>
        </TabsList>

        <TabsContent value="tips">
          <RoundInteractive round={tips.round} season={tips.season} games={tips.games} />
        </TabsContent>

        <TabsContent value="my-picks">
          <MyPicksTab games={tips.games} round={tips.round} season={tips.season} suggestedMarginGameId={tips.marginGameId} />
        </TabsContent>

        <TabsContent value="ladder">
          <Ladder ladder={ladder} />
        </TabsContent>
      </Tabs>
    </main>
  );
}
