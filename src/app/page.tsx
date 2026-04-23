import Link from "next/link";
import { Ladder } from "@/components/Ladder";
import { MarginSelector } from "@/components/MarginSelector";
import { RoundInteractive } from "@/components/RoundInteractive";
import { RoundSelector } from "@/components/RoundSelector";
import { loadAvailableRoundNumbers } from "@/lib/loadArchive";
import { loadCurrentRoundTips, loadLadder, loadLastUpdateMeta } from "@/lib/loadTips";

export default function HomePage() {
  const tips = loadCurrentRoundTips();
  const lastUpdate = loadLastUpdateMeta();
  const ladder = loadLadder();
  const availableRounds = loadAvailableRoundNumbers(tips.season);

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "32px 16px" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: "0 0 8px" }}>NRL Tipping</h1>
          <p style={{ margin: "0 0 8px", color: "#57606a" }}>
            Round {tips.round} ({tips.season}) - model {tips.modelVersion}
          </p>
          <p style={{ margin: "0 0 24px", color: "#57606a" }}>
            Last update: {new Date(lastUpdate.lastSuccessfulUpdateAt).toLocaleString("en-AU")}
          </p>
        </div>

        <RoundSelector rounds={availableRounds} selectedRound={tips.round} />
      </div>
      <p style={{ margin: "0 0 24px" }}>
        <Link href="/archive">View baked-data archive</Link>
      </p>

      <MarginSelector games={tips.games} suggestedGameId={tips.marginGameId} />
      <RoundInteractive round={tips.round} season={tips.season} games={tips.games} showPicks />
      <Ladder ladder={ladder} />
    </main>
  );
}
