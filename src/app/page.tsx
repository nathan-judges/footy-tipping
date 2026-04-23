import Link from "next/link";
import { Ladder } from "@/components/Ladder";
import { RoundView } from "@/components/RoundView";
import { RoundSelector } from "@/components/RoundSelector";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { loadAvailableRoundNumbers } from "@/lib/loadArchive";
import { loadCurrentRoundTips, loadLadder } from "@/lib/loadTips";

function formatRoundUpdatedLabel(timestamp: string): string {
  return new Date(timestamp).toLocaleString("en-AU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

export default function HomePage() {
  const tips = loadCurrentRoundTips();
  const ladder = loadLadder();
  const availableRounds = loadAvailableRoundNumbers(tips.season);

  return (
    <main className="mx-auto max-w-[860px] px-4 pb-8 pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="mb-2">NRL Tipping</h1>
          <p className="mb-6 text-muted-foreground">
            Round {tips.round} ({tips.season}) · Updated {formatRoundUpdatedLabel(tips.lastUpdated ?? tips.generatedAt)}
          </p>
        </div>

        <RoundSelector rounds={availableRounds} selectedRound={tips.round} currentRound={tips.round} />
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
