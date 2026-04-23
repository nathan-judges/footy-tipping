import type { LadderData } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface LadderProps {
  ladder: LadderData;
}

export function Ladder({ ladder }: LadderProps) {
  return (
    <section className="mt-[18px]">
      <Card>
        <CardHeader>
          <h2>Ladder</h2>
        </CardHeader>
        <CardContent className="overflow-x-auto pt-2.5">
          <table className="w-full border-collapse text-sm">
            <thead>
            <tr>
              <th className="p-2.5 text-left">#</th>
              <th className="p-2.5 text-left">Team</th>
              <th className="p-2.5 text-left">P</th>
              <th className="p-2.5 text-left">W</th>
              <th className="p-2.5 text-left">L</th>
              <th className="p-2.5 text-left">+/-</th>
              <th className="p-2.5 text-left">Pts</th>
            </tr>
            </thead>
            <tbody>
            {ladder.rows.map((row) => (
              <tr key={row.team} className="border-t">
                <td className="p-2.5">{row.rank}</td>
                <td className="p-2.5">{row.team}</td>
                <td className="p-2.5">{row.played}</td>
                <td className="p-2.5">{row.wins}</td>
                <td className="p-2.5">{row.losses}</td>
                <td className="p-2.5">{row.pointsDiff}</td>
                <td className="p-2.5">{row.competitionPoints}</td>
              </tr>
            ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </section>
  );
}
