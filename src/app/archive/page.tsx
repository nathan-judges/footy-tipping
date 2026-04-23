import Link from "next/link";
import { loadArchiveRounds } from "@/lib/loadArchive";

export const metadata = {
  title: "Archive | Footy Tipping",
  description: "Historical baked-data snapshots by NRL round."
};

export default function ArchivePage() {
  const rounds = loadArchiveRounds();

  return (
    <main style={{ maxWidth: 920, margin: "0 auto", padding: "32px 16px" }}>
      <h1 style={{ margin: "0 0 8px" }}>Baked Data Archive</h1>
      <p style={{ margin: "0 0 20px", color: "#57606a" }}>
        Historical snapshots from committed baked JSON. Latest rounds appear first.
      </p>
      <p style={{ margin: "0 0 24px" }}>
        <Link href="/">Back to current round</Link>
      </p>

      <section style={{ display: "grid", gap: 10 }}>
        {rounds.map((entry) => (
          <article
            key={entry.id}
            style={{
              background: "#fff",
              border: "1px solid #d0d7de",
              borderRadius: 10,
              padding: 14
            }}
          >
            <h2 style={{ margin: "0 0 6px", fontSize: 18 }}>
              {entry.season} Round {entry.round}
            </h2>
            <p style={{ margin: "0 0 4px", color: "#57606a", fontSize: 14 }}>
              Generated: {new Date(entry.generatedAt).toLocaleString("en-AU")}
            </p>
            <p style={{ margin: "0 0 4px", color: "#57606a", fontSize: 14 }}>
              Model: {entry.modelVersion}
            </p>
            <p style={{ margin: 0, color: "#57606a", fontSize: 14 }}>
              Games: {entry.gameCount}
              {entry.marginGameId ? ` - margin suggestion game: ${entry.marginGameId}` : ""}
            </p>
          </article>
        ))}
      </section>
    </main>
  );
}
