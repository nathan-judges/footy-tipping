"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import Image from "next/image";
import type { RoundGameTip } from "@/lib/types";
import { isModelCorrect, isUserCorrect, resolveActualWinner } from "@/lib/accuracyHelpers";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { getTeamIdentity } from "@/lib/teamData";

interface TipCardProps {
  game: RoundGameTip;
  userPick?: string;
  onPickChange?: (gameId: string, pick: string) => void;
}

export function TipCard({ game, userPick, onPickChange }: TipCardProps) {
  const [overrideTip, setOverrideTip] = useState<string | null>(game.tipOverride?.tipTeam ?? null);
  const [overrideReason, setOverrideReason] = useState<string | null>(game.tipOverride?.reason ?? null);
  const isLocked = new Date(game.kickoffAt).getTime() <= Date.now();

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
  const actualWinner = resolveActualWinner(game);
  const modelCorrect = game.status === "finished" ? isModelCorrect({ ...game, tipTeam: finalTipTeam }) : null;
  const userCorrect = game.status === "finished" ? isUserCorrect(game, userPick) : null;

  const homeTeam = getTeamIdentity(game.homeTeam);
  const awayTeam = getTeamIdentity(game.awayTeam);
  const tipConfidencePct = Math.round(game.confidence * 100);
  const homePct = finalTipTeam === game.homeTeam ? tipConfidencePct : 100 - tipConfidencePct;
  const awayPct = 100 - homePct;
  const teamVars = {
    "--team-primary": homeTeam.primary,
    "--home-color": homeTeam.primary,
    "--away-color": awayTeam.primary,
    "--split": `${homePct}%`
  } as CSSProperties;
  const selectedPick = userPick ?? "";

  return (
    <Card className="overflow-hidden" style={teamVars}>
      <div className="h-[3px] bg-[var(--team-primary)]" />
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="text-center text-lg font-semibold text-foreground/80">{kickoff}</p>
          <div className="flex items-center gap-1.5">
            {isLocked ? <Badge variant="outline">🔒 Locked</Badge> : null}
            {!isLocked && userPick ? <Badge variant="secondary">✅ Saved</Badge> : null}
          </div>
        </div>

        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
          <div className="justify-self-start text-center">
            <button
              type="button"
              disabled={isLocked || !onPickChange}
              aria-label={`Pick ${game.homeTeam}`}
              className={`mb-2 h-7 w-7 rounded-full border-2 ${
                selectedPick === game.homeTeam ? "border-black bg-black" : "border-black bg-white"
              }`}
              onClick={() => onPickChange?.(game.gameId, game.homeTeam)}
            />
            <Image
              src={homeTeam.logoPath}
              alt={game.homeTeam}
              width={44}
              height={44}
              className="mx-auto mb-1 h-11 w-11 object-contain"
            />
            <p className="text-sm font-semibold">{game.homeTeam}</p>
            <p className="text-xs text-muted-foreground">{homeTeam.shortName}</p>
          </div>

          <div className="min-w-[124px] text-center">
            <div className="mb-1 flex items-center justify-center gap-2 text-3xl font-bold">
              <span>{homePct}%</span>
              <div
                className="grid h-14 w-14 place-items-center rounded-full"
                style={{
                  background: "conic-gradient(var(--home-color) 0 var(--split), var(--away-color) var(--split) 100%)"
                }}
              >
                <div className="grid h-10 w-10 place-items-center rounded-full bg-white text-[10px] font-bold leading-tight text-black">
                  <span>VIEW</span>
                  <span>STATS</span>
                </div>
              </div>
              <span>{awayPct}%</span>
            </div>
          </div>

          <div className="justify-self-end text-center">
            <button
              type="button"
              disabled={isLocked || !onPickChange}
              aria-label={`Pick ${game.awayTeam}`}
              className={`mb-2 h-7 w-7 rounded-full border-2 ${
                selectedPick === game.awayTeam ? "border-black bg-black" : "border-black bg-white"
              }`}
              onClick={() => onPickChange?.(game.gameId, game.awayTeam)}
            />
            <Image
              src={awayTeam.logoPath}
              alt={game.awayTeam}
              width={44}
              height={44}
              className="mx-auto mb-1 h-11 w-11 object-contain"
            />
            <p className="text-sm font-semibold">{game.awayTeam}</p>
            <p className="text-xs text-muted-foreground">{awayTeam.shortName}</p>
          </div>
        </div>

        <p className="text-center text-[13px] text-muted-foreground">{game.venue}</p>

        {game.status === "finished" && typeof game.homeScore === "number" && typeof game.awayScore === "number" ? (
          <p className="text-center text-lg font-bold">
            Final: {game.homeScore} - {game.awayScore}
          </p>
        ) : null}

        <p>
          Model tip: <strong>{finalTipTeam}</strong> ({Math.round(game.confidence * 100)}%)
          {game.status === "finished" && actualWinner ? (
            <span className={`ml-2 ${modelCorrect ? "text-green-700" : "text-red-600"}`}>
              {modelCorrect ? "✓" : "✕"}
            </span>
          ) : null}
        </p>

        {userPick ? (
          <p>
            Your pick: <strong>{userPick}</strong>
            {game.status === "finished" && actualWinner ? (
              <span className={`ml-2 ${userCorrect ? "text-green-700" : "text-red-600"}`}>
                {userCorrect ? "✓" : "✕"}
              </span>
            ) : null}
          </p>
        ) : null}

        {!isLocked && onPickChange ? (
          <label className="block">
            <span className="mb-1.5 block text-[13px] text-muted-foreground">Your pick</span>
            <select
              className="w-full rounded-md border bg-background px-2.5 py-2"
              value={userPick ?? ""}
              onChange={(event) => {
                const next = event.target.value;
                if (!next) return;
                onPickChange(game.gameId, next);
              }}
            >
              <option value="">Select your pick</option>
              <option value={game.homeTeam}>{game.homeTeam}</option>
              <option value={game.awayTeam}>{game.awayTeam}</option>
            </select>
          </label>
        ) : null}

        <p className="text-muted-foreground">Predicted margin: {game.predictedMargin}</p>
        {overrideTip ? (
          <p className="mt-2 text-xs text-violet-600">
            Live override: {overrideTip} ({overrideReason ?? "updated"})
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
