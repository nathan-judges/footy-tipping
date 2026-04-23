"use client";

import type { CSSProperties } from "react";
import { Badge } from "@/components/ui/badge";
import { getTeamIdentity } from "@/lib/teamData";

interface TeamBadgeProps {
  teamName: string;
}

export function TeamBadge({ teamName }: TeamBadgeProps) {
  const team = getTeamIdentity(teamName);
  const teamVars = { "--team-primary": team.primary } as CSSProperties;

  return (
    <Badge className="border-transparent bg-[var(--team-primary)] text-white" style={teamVars} title={teamName}>
      {team.shortName}
    </Badge>
  );
}
