import type { LadderData } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { getTeamIdentity } from "@/lib/teamData";

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
                <td className="p-2.5">
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: getTeamIdentity(row.team).primary }}
                    />
                    <span className="font-medium">{row.team}</span>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">
                      {getTeamIdentity(row.team).shortName}
                    </span>
                  </div>
                </td>
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
