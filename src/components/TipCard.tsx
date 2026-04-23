"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import type { RoundGameTip } from "@/lib/types";
import { getTeamIdentity } from "@/lib/teamData";
import { getNrlMatchUrl } from "@/lib/nrlLinks";

interface TipCardProps {
  round: number;
  season: number;
  game: RoundGameTip;
  userPick?: string;
  onPickChange?: (gameId: string, team: string) => void;
  disablePicks?: boolean;
}

export function TipCard({ game, round, season, userPick, onPickChange, disablePicks = false }: TipCardProps) {
  const [overrideTip, setOverrideTip] = useState<string | null>(game.tipOverride?.tipTeam ?? null);
  const [overrideReason, setOverrideReason] = useState<string | null>(game.tipOverride?.reason ?? null);

  const withinPreKickoffWindow = useMemo(() => {
    const kickoffMs = new Date(game.kickoffAt).getTime();
    const now = Date.now();
    const tenMinutes = 10 * 60 * 1000;
    return now >= kickoffMs - tenMinutes && now < kickoffMs;
  }, [game.kickoffAt]);

  useEffect(() => {
    if (!withinPreKickoffWindow || game.status !== "upcoming") return;
    let cancelled = false;
    const pollIntervalMs = 60_000;

    console.info(`[live-override] monitoring ${game.gameId} (${game.homeTeam} vs ${game.awayTeam})`);

    async function checkLiveOverride() {
      try {
        const response = await fetch(`/api/live-tips?gameId=${encodeURIComponent(game.gameId)}`, {
          cache: "no-store"
        });
        if (!response.ok) {
          console.warn(`[live-override] ${game.gameId} check failed with HTTP ${response.status}`);
          return;
        }
        const payload = (await response.json()) as {
          tipOverride?: { tipTeam?: string; reason?: string } | null;
          reason?: string;
          source?: string;
        };

        if (cancelled) return;
        if (!payload.tipOverride?.tipTeam) {
          console.info(
            `[live-override] ${game.gameId} no override (${payload.source ?? "unknown source"}): ${payload.reason ?? "none"}`
          );
          return;
        }

        setOverrideTip(payload.tipOverride.tipTeam);
        setOverrideReason(payload.tipOverride.reason ?? payload.reason ?? "live update");
        console.warn(
          `[live-override] OVERRIDE APPLIED ${game.gameId}: ${payload.tipOverride.tipTeam} (${payload.tipOverride.reason ?? payload.reason ?? "updated"})`
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : "unknown error";
        console.error(`[live-override] ${game.gameId} check threw: ${message}`);
      }
    }

    checkLiveOverride().catch(() => undefined);
    const intervalId = window.setInterval(() => {
      checkLiveOverride().catch(() => undefined);
    }, pollIntervalMs);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      console.info(`[live-override] stopped monitoring ${game.gameId}`);
    };
  }, [game.awayTeam, game.gameId, game.homeTeam, game.status, withinPreKickoffWindow]);

  const kickoff = new Date(game.kickoffAt).toLocaleString("en-AU", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  });

  const finalTipTeam = overrideTip ?? game.tipTeam;

  const homeTeam = getTeamIdentity(game.homeTeam);
  const awayTeam = getTeamIdentity(game.awayTeam);
  const tipConfidencePct = Math.round(game.confidence * 100);
  const homePct = finalTipTeam === game.homeTeam ? tipConfidencePct : 100 - tipConfidencePct;
  const awayPct = 100 - homePct;
  const selectedPick = userPick ?? "";
  const teamVars = {
    "--team-primary": homeTeam.primary,
    "--home-color": homeTeam.primary,
    "--away-color": awayTeam.primary,
    "--split": `${homePct}%`
  } as CSSProperties;

  return (
    <div className="rounded-md border bg-card p-3.5" style={teamVars}>
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <div className="text-sm text-muted-foreground">
          {kickoff} · {game.venue}
        </div>
        <a
          className="text-sm font-semibold text-foreground/80 underline-offset-4 hover:underline"
          href={getNrlMatchUrl(game, season, round)}
          target="_blank"
          rel="noreferrer"
        >
          VIEW STATS →
        </a>
      </div>

      <div className="mt-2 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <div className="min-w-0">
          <button
            type="button"
            className="inline-flex max-w-full items-center gap-1 rounded-md border px-2.5 py-1 text-sm font-semibold"
            disabled={!onPickChange || disablePicks}
            style={
              selectedPick === game.homeTeam
                ? { backgroundColor: homeTeam.primary, color: "#fff", borderColor: homeTeam.primary }
                : undefined
            }
            onClick={() => onPickChange?.(game.gameId, game.homeTeam)}
          >
            <span className="truncate">{game.homeTeam}</span>
            <span className={selectedPick === game.homeTeam ? "text-white/85" : "text-muted-foreground"}>({homeTeam.shortName})</span>
          </button>
        </div>

        <div className="min-w-[140px]">
          <div className="flex items-center justify-center gap-2 text-sm font-semibold tabular-nums">
            <span className="text-muted-foreground">{homePct}%</span>
            <div className="relative h-2 w-[84px] overflow-hidden rounded-full bg-muted">
              <div className="absolute inset-0" style={{ background: "linear-gradient(90deg, var(--home-color) 0 var(--split), var(--away-color) var(--split) 100%)" }} />
            </div>
            <span className="text-muted-foreground">{awayPct}%</span>
          </div>
        </div>

        <div className="min-w-0 text-right">
          <button
            type="button"
            className="ml-auto inline-flex max-w-full items-center gap-1 rounded-md border px-2.5 py-1 text-sm font-semibold"
            disabled={!onPickChange || disablePicks}
            style={
              selectedPick === game.awayTeam
                ? { backgroundColor: awayTeam.primary, color: "#fff", borderColor: awayTeam.primary }
                : undefined
            }
            onClick={() => onPickChange?.(game.gameId, game.awayTeam)}
          >
            <span className={selectedPick === game.awayTeam ? "text-white/85" : "text-muted-foreground"}>({awayTeam.shortName})</span>
            <span className="truncate">{game.awayTeam}</span>
          </button>
        </div>
      </div>

      {overrideTip ? (
        <p className="mt-2 text-xs text-violet-600">
          Live override: {overrideTip} ({overrideReason ?? "updated"})
        </p>
      ) : null}
    </div>
  );
}
