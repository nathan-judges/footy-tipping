import type { RoundGameTip } from "@/lib/types";
import { TipCard } from "./TipCard";

interface TipsListProps {
  games: RoundGameTip[];
}

export function TipsList({ games }: TipsListProps) {
  const upcomingGames = games.filter((game) => game.status === "upcoming");

  if (upcomingGames.length === 0) {
    return <p>No upcoming games available for tipping yet.</p>;
  }

  return (
    <section style={{ display: "grid", gap: 12 }}>
      {upcomingGames.map((game) => (
        <TipCard key={game.gameId} game={game} />
      ))}
    </section>
  );
}
