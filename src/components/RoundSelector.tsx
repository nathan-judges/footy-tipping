"use client";

import { useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";

interface RoundSelectorProps {
  rounds: number[];
  selectedRound: number;
  currentRound: number;
  label?: string;
}

export function RoundSelector({ rounds, selectedRound, currentRound, label = "Round" }: RoundSelectorProps) {
  const router = useRouter();
  const pathname = usePathname();

  const normalizedRounds = useMemo(() => Array.from(new Set(rounds)).sort((a, b) => a - b), [rounds]);

  return (
    <label className="inline-flex items-center gap-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <select
        className="rounded-md border bg-background px-2 py-1"
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
        {normalizedRounds.map((round) => {
          const labelSuffix =
            round < currentRound ? "Past" : round === currentRound ? "Current" : "Future (Preliminary)";
          const isFuture = round > currentRound;
          return (
            <option key={round} value={round} className={isFuture ? "text-muted-foreground italic" : undefined}>
              {round} — {labelSuffix}
            </option>
          );
        })}
      </select>
    </label>
  );
}

