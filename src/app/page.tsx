import Link from "next/link";
import { Ladder } from "@/components/Ladder";
import { MarginSelector } from "@/components/MarginSelector";
import { MyPicks } from "@/components/MyPicks";
import { TipsList } from "@/components/TipsList";
import { loadCurrentRoundTips, loadLadder, loadLastUpdateMeta } from "@/lib/loadTips";

export default function HomePage() {
  const tips = loadCurrentRoundTips();
  const lastUpdate = loadLastUpdateMeta();
  const ladder = loadLadder();

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "32px 16px" }}>
      <h1 style={{ margin: "0 0 8px" }}>NRL Tipping</h1>
      <p style={{ margin: "0 0 8px", color: "#57606a" }}>
        Round {tips.round} ({tips.season}) - model {tips.modelVersion}
      </p>
      <p style={{ margin: "0 0 24px", color: "#57606a" }}>
        Last update: {new Date(lastUpdate.lastSuccessfulUpdateAt).toLocaleString("en-AU")}
      </p>
      <p style={{ margin: "0 0 24px" }}>
        <Link href="/archive">View baked-data archive</Link>
      </p>

      <MarginSelector games={tips.games} suggestedGameId={tips.marginGameId} />
      <TipsList games={tips.games} />
      <MyPicks games={tips.games} />
      <Ladder ladder={ladder} />
    </main>
  );
}
