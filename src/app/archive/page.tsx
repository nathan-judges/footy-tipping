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
          <Link key={entry.id} href={`/round/${entry.round}`} className="block no-underline">
            <Card className="transition-colors hover:bg-muted/40">
              <CardContent>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
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
                      {entry.marginGameId ? ` · margin game: ${entry.marginGameId}` : ""}
                    </p>
                  </div>
                  {entry.modelAccuracy ? (
                    <div className="rounded-md border bg-card px-3 py-2 text-center">
                      <p className="text-xs text-muted-foreground">Model accuracy</p>
                      <p className="text-lg font-semibold tabular-nums">
                        {entry.modelAccuracy.correct}/{entry.modelAccuracy.total}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {Math.round((entry.modelAccuracy.correct / entry.modelAccuracy.total) * 100)}%
                      </p>
                    </div>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </section>
    </main>
  );
}
