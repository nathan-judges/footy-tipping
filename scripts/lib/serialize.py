"""Serialize model outputs into baked JSON artifacts."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from .types import TipResult


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_round_payload(
    tips: list[TipResult], round_number: int, season: int, model_version: str
) -> dict:
    games: list[dict] = []
    for tip in tips:
        game = {
            "gameId": tip.game_id,
            "homeTeam": tip.home_team,
            "awayTeam": tip.away_team,
            "venue": tip.venue,
            "kickoffAt": tip.kickoff_at,
            "status": tip.status,
            "tipTeam": tip.tip_team,
            "confidence": tip.confidence,
            "predictedMargin": tip.predicted_margin,
        }
        if tip.nrl_match_id is not None:
            game["nrlMatchId"] = tip.nrl_match_id
        if tip.nrl_slug is not None:
            game["nrlSlug"] = tip.nrl_slug
        if tip.odds is not None:
            game["odds"] = asdict(tip.odds)
        if tip.home_score is not None:
            game["homeScore"] = tip.home_score
        if tip.away_score is not None:
            game["awayScore"] = tip.away_score
        if tip.actual_winner is not None:
            game["actualWinner"] = tip.actual_winner
        if tip.actual_margin is not None:
            game["actualMargin"] = tip.actual_margin
        games.append(game)

    margin_game_id = _suggest_margin_game_id(tips)
    return {
        "round": round_number,
        "season": season,
        "modelVersion": model_version,
        "generatedAt": _utc_now_iso(),
        "marginGameId": margin_game_id,
        "games": games,
    }


def build_last_update_payload(source: str, status: str = "ok") -> dict:
    return {
        "lastSuccessfulUpdateAt": _utc_now_iso(),
        "source": source,
        "status": status,
    }


def build_ladder_payload(seed_ladder: dict, season: int, round_number: int) -> dict:
    """Normalize ladder payload into canonical baked shape."""
    return {
        "season": season,
        "round": round_number,
        "generatedAt": _utc_now_iso(),
        "rows": seed_ladder.get("rows", []),
    }


def _suggest_margin_game_id(tips: list[TipResult]) -> str | None:
    upcoming = [tip for tip in tips if tip.status == "upcoming"]
    if not upcoming:
        return None
    best = max(upcoming, key=lambda tip: abs(tip.predicted_margin))
    return best.game_id
