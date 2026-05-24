"use client";

import { useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";

interface RoundSelectorProps {
  totalRounds: number;
  bakedRounds: number[];
  selectedRound: number;
  currentRound: number;
  label?: string;
}

export function RoundSelector({ totalRounds, bakedRounds, selectedRound, currentRound, label = "Round" }: RoundSelectorProps) {
  const router = useRouter();
  const pathname = usePathname();

  const bakedSet = useMemo(() => new Set(bakedRounds), [bakedRounds]);
  const rounds = useMemo(() => Array.from({ length: totalRounds }, (_, idx) => idx + 1), [totalRounds]);

  return (
    <label className="inline-flex w-full items-center gap-2 sm:w-auto">
      <span className="text-sm text-muted-foreground">{label}</span>
      <select
        className="w-full rounded-md border bg-background px-2 py-1 sm:w-auto"
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
        {rounds.map((round) => {
          const labelSuffix =
            round < currentRound ? "Past" : round === currentRound ? "Current" : "Future (Preliminary)";
          const isFuture = round > currentRound;
          const isBaked = bakedSet.has(round);
          const availability = isBaked ? "" : " · Not baked yet";
          return (
            <option key={round} value={round} className={isFuture ? "text-muted-foreground italic" : undefined}>
              {round} — {labelSuffix}
              {availability}
            </option>
          );
        })}
      </select>
    </label>
  );
}

