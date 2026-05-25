"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import Image from "next/image";
import type { RoundGameTip } from "@/lib/types";
import { getTeamIdentity } from "@/lib/teamData";

interface TipCardProps {
  game: RoundGameTip;
  mode: "current" | "archive";
  disableInteractions?: boolean;
}

export type ConfidenceLevel = "high" | "medium" | "low";

export function getConfidenceLevel(score: number): ConfidenceLevel {
  if (score > 70) return "high";
  if (score >= 55) return "medium";
  return "low";
}

const confidenceStyles: Record<ConfidenceLevel, string> = {
  high: "font-bold text-foreground",
  medium: "font-semibold text-foreground/90",
  low: "font-medium text-foreground/70"
};

const nonPredictedStyles = "font-normal text-muted-foreground";

function hexToRgb(hex: string): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return "128,128,128";
  return `${r},${g},${b}`;
}

function getBackgroundOpacity(level: ConfidenceLevel): number {
  if (level === "high") return 0.15;
  if (level === "medium") return 0.10;
  return 0.05;
}

interface TeamLogoProps {
  team: string;
  logoPath: string;
  primary: string;
  shortName: string;
}

function TeamLogo({ team, logoPath, primary, shortName }: TeamLogoProps) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <span
        aria-label={`${team} logo`}
        className="inline-flex shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white w-8 h-8 sm:w-10 sm:h-10"
        style={{ backgroundColor: primary }}
      >
        {shortName.slice(0, 1)}
      </span>
    );
  }

  return (
    <Image
      src={logoPath}
      alt={`${team} logo`}
      width={40}
      height={40}
      className="shrink-0 object-contain w-8 h-8 sm:w-10 sm:h-10"
      onError={() => setHasError(true)}
    />
  );
}

export function TipCard({ game, mode: _mode, disableInteractions: _disableInteractions = false }: TipCardProps) {
  const [overrideTip, setOverrideTip] = useState<string | null>(game.tipOverride?.tipTeam ?? null);
  const [overrideReason, setOverrideReason] = useState<string | null>(game.tipOverride?.reason ?? null);
  const [barMounted, setBarMounted] = useState(false);

  const withinPreKickoffWindow = useMemo(() => {
    const kickoffMs = new Date(game.kickoffAt).getTime();
    const now = Date.now();
    const tenMinutes = 10 * 60 * 1000;
    return now >= kickoffMs - tenMinutes && now < kickoffMs;
  }, [game.kickoffAt]);

  // Trigger confidence bar CSS transition after mount
  useEffect(() => {
    setBarMounted(true);
  }, []);

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

  // confidence is 0–1 in the data; convert to 0–100 for display and level calculation
  const confidenceScore = Math.round(game.confidence * 100);
  const confidenceLevel = getConfidenceLevel(confidenceScore);

  const isHomePredicted = finalTipTeam === game.homeTeam;
  const predictedTeamIdentity = isHomePredicted ? homeTeam : awayTeam;

  // Home win probability for the bar: if home is predicted, use confidence; otherwise 100 - confidence
  const homePct = isHomePredicted ? confidenceScore : 100 - confidenceScore;
  const awayPct = 100 - homePct;

  // Background tint for the predicted team section
  const tintOpacity = getBackgroundOpacity(confidenceLevel);
  const tintRgb = hexToRgb(predictedTeamIdentity.primary);
  const tintStyle = `rgba(${tintRgb}, ${tintOpacity})`;

  const teamVars = {
    "--home-color": homeTeam.primary,
    "--away-color": awayTeam.primary
  } as CSSProperties;

  return (
    <div className="rounded-md border bg-card shadow-sm" style={teamVars}>
      {/* Game metadata */}
      <div className="px-3.5 pt-3 text-sm text-muted-foreground">
        {kickoff} · {game.venue}
      </div>

      {/* Teams row — vertical on mobile, horizontal on sm+ */}
      <div className="mt-2 flex flex-col gap-2 px-3.5 sm:flex-row sm:items-center sm:gap-3">
        {/* Home team */}
        <div
          className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2.5 py-2"
          style={isHomePredicted ? { backgroundColor: tintStyle } : undefined}
          data-predicted={isHomePredicted ? "true" : "false"}
        >
          <TeamLogo
            team={game.homeTeam}
            logoPath={homeTeam.logoPath}
            primary={homeTeam.primary}
            shortName={homeTeam.shortName}
          />
          <div className="min-w-0">
            <span
              className={`block truncate text-sm ${isHomePredicted ? confidenceStyles[confidenceLevel] : nonPredictedStyles}`}
              data-confidence={isHomePredicted ? confidenceLevel : undefined}
            >
              {game.homeTeam}
              {isHomePredicted && (
                <span className="ml-1.5 text-xs font-normal tabular-nums text-muted-foreground">
                  {confidenceScore}%
                </span>
              )}
            </span>
            <span className="text-xs text-muted-foreground">{homeTeam.shortName}</span>
          </div>
        </div>

        {/* VS divider — only visible on sm+ */}
        <div className="hidden shrink-0 text-xs font-medium text-muted-foreground sm:block">vs</div>

        {/* Away team */}
        <div
          className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2.5 py-2 sm:flex-row-reverse sm:text-right"
          style={!isHomePredicted ? { backgroundColor: tintStyle } : undefined}
          data-predicted={!isHomePredicted ? "true" : "false"}
        >
          <TeamLogo
            team={game.awayTeam}
            logoPath={awayTeam.logoPath}
            primary={awayTeam.primary}
            shortName={awayTeam.shortName}
          />
          <div className="min-w-0 sm:text-right">
            <span
              className={`block truncate text-sm ${!isHomePredicted ? confidenceStyles[confidenceLevel] : nonPredictedStyles}`}
              data-confidence={!isHomePredicted ? confidenceLevel : undefined}
            >
              {game.awayTeam}
              {!isHomePredicted && (
                <span className="ml-1.5 text-xs font-normal tabular-nums text-muted-foreground">
                  {confidenceScore}%
                </span>
              )}
            </span>
            <span className="text-xs text-muted-foreground">{awayTeam.shortName}</span>
          </div>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="mt-2 px-3.5 pb-3">
        <div className="flex h-1.5 overflow-hidden rounded-full bg-muted">
          {/* Home side */}
          <div
            className="transition-[width] duration-700 ease-out"
            style={{
              width: barMounted ? `${homePct}%` : "0%",
              backgroundColor: homeTeam.primary
            }}
            aria-label={`${game.homeTeam} ${homePct}%`}
          />
          {/* Away side */}
          <div
            className="flex-1 transition-[width] duration-700 ease-out"
            style={{
              backgroundColor: awayTeam.primary,
              opacity: 0.6
            }}
            aria-label={`${game.awayTeam} ${awayPct}%`}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs tabular-nums text-muted-foreground">
          <span>{homePct}%</span>
          <span>{awayPct}%</span>
        </div>
      </div>

      {/* Live override notice */}
      {overrideTip ? (
        <p className="px-3.5 pb-3 text-xs text-violet-600">
          Live override: {overrideTip} ({overrideReason ?? "updated"})
        </p>
      ) : null}
    </div>
  );
}
