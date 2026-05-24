"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import type { RoundGameTip } from "@/lib/types";
import { TeamMark } from "@/components/TeamMark";
import { getTeamIdentity } from "@/lib/teamData";
import { getNrlMatchUrl } from "@/lib/nrlLinks";

interface TipCardProps {
  round: number;
  season: number;
  game: RoundGameTip;
  userPick?: string;
  onPickChange?: (gameId: string, team: string) => void;
  disablePicks?: boolean;
  isMarginGame?: boolean;
  modelMargin?: number;
  marginPoints?: number;
  onSetMarginGame?: () => void;
  onMarginPointsChange?: (points: number | undefined) => void;
}

export function TipCard({
  game,
  round,
  season,
  userPick,
  onPickChange,
  disablePicks = false,
  isMarginGame = false,
  modelMargin,
  marginPoints,
  onSetMarginGame,
  onMarginPointsChange
}: TipCardProps) {
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

  const isUpcoming = game.status === "upcoming";

  return (
    <div className="rounded-md border bg-card p-3.5" style={teamVars}>
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <div className="text-sm text-muted-foreground">
          {kickoff} · {game.venue}
        </div>
        <div className="flex items-center gap-2">
          {isUpcoming ? (
            <button
              type="button"
              className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${
                isMarginGame ? "bg-black text-white" : "bg-background"
              }`}
              disabled={disablePicks || !onSetMarginGame}
              onClick={() => onSetMarginGame?.()}
              title="Set as margin game"
            >
              Margin
            </button>
          ) : null}
          <a
            className="text-sm font-semibold text-foreground/80 underline-offset-4 hover:underline"
            href={getNrlMatchUrl(game, season, round)}
            target="_blank"
            rel="noreferrer"
          >
            VIEW STATS →
          </a>
        </div>
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
            <TeamMark
              team={game.homeTeam}
              shortCode={homeTeam.shortName}
              logoPath={homeTeam.logoPath}
              primary={homeTeam.primary}
              size={16}
            />
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
            <TeamMark
              team={game.awayTeam}
              shortCode={awayTeam.shortName}
              logoPath={awayTeam.logoPath}
              primary={awayTeam.primary}
              size={16}
            />
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

      {isMarginGame && isUpcoming ? (
        <div className="mt-3 rounded-md border bg-background p-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div>
              <span className="text-xs text-muted-foreground">Model spread</span>
              <div className="mt-1.5 rounded-md border bg-card px-2.5 py-2 text-sm tabular-nums">
                {typeof modelMargin === "number"
                  ? `${modelMargin >= 0 ? "+" : ""}${modelMargin}`
                  : "—"}
              </div>
            </div>
            <label className="block md:col-span-2">
              <span className="text-xs text-muted-foreground">Your margin</span>
              <input
                type="number"
                className="mt-1.5 w-full rounded-md border bg-card px-2.5 py-2"
                value={marginPoints ?? ""}
                disabled={disablePicks || !onMarginPointsChange}
                onChange={(event) =>
                  onMarginPointsChange?.(
                    event.target.value === "" ? undefined : Number(event.target.value)
                  )
                }
              />
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
}
