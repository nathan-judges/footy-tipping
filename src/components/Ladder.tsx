import type { LadderData } from "@/lib/types";

interface LadderProps {
  ladder: LadderData;
}

export function Ladder({ ladder }: LadderProps) {
  return (
    <section style={{ marginTop: 28 }}>
      <h2 style={{ marginBottom: 12 }}>Ladder</h2>
      <div style={{ overflowX: "auto", background: "#fff", border: "1px solid #d0d7de", borderRadius: 10 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 10 }}>#</th>
              <th style={{ textAlign: "left", padding: 10 }}>Team</th>
              <th style={{ textAlign: "left", padding: 10 }}>P</th>
              <th style={{ textAlign: "left", padding: 10 }}>W</th>
              <th style={{ textAlign: "left", padding: 10 }}>L</th>
              <th style={{ textAlign: "left", padding: 10 }}>+/-</th>
              <th style={{ textAlign: "left", padding: 10 }}>Pts</th>
            </tr>
          </thead>
          <tbody>
            {ladder.rows.map((row) => (
              <tr key={row.team} style={{ borderTop: "1px solid #d8dee4" }}>
                <td style={{ padding: 10 }}>{row.rank}</td>
                <td style={{ padding: 10 }}>{row.team}</td>
                <td style={{ padding: 10 }}>{row.played}</td>
                <td style={{ padding: 10 }}>{row.wins}</td>
                <td style={{ padding: 10 }}>{row.losses}</td>
                <td style={{ padding: 10 }}>{row.pointsDiff}</td>
                <td style={{ padding: 10 }}>{row.competitionPoints}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
