"use client";

import { useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";

interface RoundSelectorProps {
  rounds: number[];
  selectedRound: number;
  label?: string;
}

export function RoundSelector({ rounds, selectedRound, label = "Round" }: RoundSelectorProps) {
  const router = useRouter();
  const pathname = usePathname();

  const normalizedRounds = useMemo(() => Array.from(new Set(rounds)).sort((a, b) => a - b), [rounds]);

  return (
    <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span style={{ color: "#57606a", fontSize: 14 }}>{label}</span>
      <select
        aria-label="Select round"
        value={selectedRound}
        onChange={(event) => {
          const nextRound = Number(event.target.value);
          if (!Number.isFinite(nextRound)) return;
          const nextHref = `/round/${nextRound}`;
          if (pathname === nextHref) return;
          router.push(nextHref);
        }}
      >
        {normalizedRounds.map((round) => (
          <option key={round} value={round}>
            {round}
          </option>
        ))}
      </select>
    </label>
  );
}

