import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { loadArchiveRounds } from "@/lib/loadArchive";

export const metadata = {
  title: "Archive | Footy Tipping",
  description: "Historical baked-data snapshots by NRL round."
};

export default function ArchivePage() {
  const rounds = loadArchiveRounds();

  return (
    <main className="mx-auto max-w-[860px] px-4 pb-8 pt-6">
      <h1 className="mb-2">Baked Data Archive</h1>
      <p className="mb-5 text-muted-foreground">
        Historical snapshots from committed baked JSON. Latest rounds appear first.
      </p>
      <p className="mb-6">
        <Link href="/">Back to current round</Link>
      </p>

      <section className="grid gap-2.5">
        {rounds.map((entry) => (
          <Card key={entry.id}>
            <CardContent>
              <h2 className="mb-1.5 text-lg">
                {entry.season} Round {entry.round}
              </h2>
              <p className="mb-1 text-sm text-muted-foreground">
                Generated: {new Date(entry.generatedAt).toLocaleString("en-AU")}
              </p>
              <p className="mb-1 text-sm text-muted-foreground">
                Model: {entry.modelVersion}
              </p>
              <p className="text-sm text-muted-foreground">
                Games: {entry.gameCount}
                {entry.marginGameId ? ` - margin suggestion game: ${entry.marginGameId}` : ""}
              </p>
            </CardContent>
          </Card>
        ))}
      </section>
    </main>
  );
}
