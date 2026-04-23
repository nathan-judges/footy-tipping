"use client";

import { useEffect, useMemo, useState } from "react";
import type { RoundGameTip } from "@/lib/types";

interface TipCardProps {
  game: RoundGameTip;
}

export function TipCard({ game }: TipCardProps) {
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

  return (
    <article
      style={{
        border: "1px solid #d0d7de",
        borderRadius: 10,
        padding: 16,
        background: "#fff"
      }}
    >
      <p style={{ margin: 0, fontSize: 12, color: "#57606a" }}>{kickoff}</p>
      <h3 style={{ margin: "8px 0 4px" }}>
        {game.homeTeam} vs {game.awayTeam}
      </h3>
      <p style={{ margin: "0 0 8px", color: "#57606a" }}>{game.venue}</p>
      <p style={{ margin: "0 0 8px" }}>
        Tip: <strong>{overrideTip ?? game.tipTeam}</strong> ({Math.round(game.confidence * 100)}%)
      </p>
      <p style={{ margin: 0, color: "#57606a" }}>Predicted margin: {game.predictedMargin}</p>
      {overrideTip ? (
        <p style={{ margin: "8px 0 0", color: "#8250df", fontSize: 12 }}>
          Live override: {overrideTip} ({overrideReason ?? "updated"})
        </p>
      ) : null}
    </article>
  );
}
