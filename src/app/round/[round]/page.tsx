import Link from "next/link";
import { RoundInteractive } from "@/components/RoundInteractive";
import { RoundSelector } from "@/components/RoundSelector";
import { loadAvailableRoundNumbers, loadRoundTips } from "@/lib/loadArchive";
import { loadCurrentRoundTips, loadLadder, loadLastUpdateMeta } from "@/lib/loadTips";
import { Ladder } from "@/components/Ladder";

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
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "32px 16px" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: "0 0 8px" }}>NRL Tipping</h1>
          <p style={{ margin: "0 0 8px", color: "#57606a" }}>
            Round {selectedRound} ({current.season}) - model {tips?.modelVersion ?? current.modelVersion}
          </p>
          <p style={{ margin: "0 0 8px", color: "#57606a" }}>
            Last update: {new Date(lastUpdate.lastSuccessfulUpdateAt).toLocaleString("en-AU")}
          </p>
        </div>

        <RoundSelector rounds={availableRounds} selectedRound={selectedRound} />
      </div>

      <p style={{ margin: "8px 0 24px" }}>
        <Link href="/">Back to current round</Link>
        {" · "}
        <Link href="/archive">View baked-data archive</Link>
      </p>

      {!tips ? (
        <p style={{ background: "#fff", border: "1px solid #d0d7de", borderRadius: 10, padding: 14 }}>
          No baked snapshot found for round <strong>{roundParam}</strong>.
        </p>
      ) : (
        <>
          <RoundInteractive round={tips.round} season={tips.season} games={tips.games} mode="all" />
          <Ladder ladder={ladder} />
        </>
      )}
    </main>
  );
}

