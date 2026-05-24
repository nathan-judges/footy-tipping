"""Robust odds integration with de-vigging and team name matching.

Wraps the existing odds API fetch with proper overround removal,
fuzzy team name matching, and result caching.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .types import Fixture

# ---------------------------------------------------------------------------
# Team name normalisation for odds APIs
# ---------------------------------------------------------------------------

_ODDS_NAME_MAP: dict[str, list[str]] = {
    "Broncos": ["broncos", "brisbane broncos", "brisbane"],
    "Bulldogs": ["bulldogs", "canterbury bulldogs", "canterbury-bankstown bulldogs", "canterbury"],
    "Cowboys": ["cowboys", "north queensland cowboys", "north queensland"],
    "Dolphins": ["dolphins", "redcliffe dolphins", "the dolphins"],
    "Dragons": ["dragons", "st george illawarra dragons", "st george illawarra", "st george"],
    "Eels": ["eels", "parramatta eels", "parramatta"],
    "Knights": ["knights", "newcastle knights", "newcastle"],
    "Panthers": ["panthers", "penrith panthers", "penrith"],
    "Rabbitohs": ["rabbitohs", "south sydney rabbitohs", "south sydney", "souths"],
    "Raiders": ["raiders", "canberra raiders", "canberra"],
    "Roosters": ["roosters", "sydney roosters", "sydney"],
    "Sea Eagles": ["sea eagles", "manly sea eagles", "manly-warringah sea eagles", "manly"],
    "Sharks": ["sharks", "cronulla sharks", "cronulla-sutherland sharks", "cronulla"],
    "Storm": ["storm", "melbourne storm", "melbourne"],
    "Titans": ["titans", "gold coast titans", "gold coast"],
    "Warriors": ["warriors", "new zealand warriors", "nz warriors"],
    "Wests Tigers": ["wests tigers", "western suburbs", "tigers"],
}

# Build reverse lookup
_REVERSE_ODDS_MAP: dict[str, str] = {}
for _canonical, _variants in _ODDS_NAME_MAP.items():
    for _v in _variants:
        _REVERSE_ODDS_MAP[_v] = _canonical


def normalize_team_name_for_odds(name: str) -> str:
    """Map an odds-API team name to the canonical NRL nickname."""
    lower = name.strip().lower()
    if lower in _REVERSE_ODDS_MAP:
        return _REVERSE_ODDS_MAP[lower]
    # Partial match
    for variant, canonical in _REVERSE_ODDS_MAP.items():
        if variant in lower or lower in variant:
            return canonical
    return name.strip()


# ---------------------------------------------------------------------------
# De-vigging (overround removal)
# ---------------------------------------------------------------------------

def de_vig(home_odds: float, away_odds: float) -> tuple[float, float]:
    """Remove bookmaker overround using the multiplicative method.

    Parameters are *decimal* odds (e.g. 1.80, 2.10).
    Returns ``(home_fair_prob, away_fair_prob)`` summing to 1.0.
    """
    if home_odds <= 1.0 or away_odds <= 1.0:
        return 0.5, 0.5

    raw_home = 1.0 / home_odds
    raw_away = 1.0 / away_odds
    total = raw_home + raw_away

    if total <= 0:
        return 0.5, 0.5

    return raw_home / total, raw_away / total


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OddsResult:
    """De-vigged match probabilities from the betting market."""

    home_prob: float
    away_prob: float
    source: str
    fetched_at: str


# ---------------------------------------------------------------------------
# Simple in-memory cache
# ---------------------------------------------------------------------------

_odds_cache: dict[str, OddsResult | None] = {}


def _cache_key(fixture: Fixture) -> str:
    return f"{fixture.home_team}:{fixture.away_team}:{fixture.kickoff_at}"


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_match_odds(
    fixture: Fixture,
    api_key: str | None = None,
) -> OddsResult | None:
    """Fetch and de-vig match odds for *fixture*.

    Uses ``ODDS_API_KEY`` env var if *api_key* is not provided.
    Returns ``None`` when odds are unavailable.  Results are cached
    in-memory to avoid redundant API calls.
    """
    key = _cache_key(fixture)
    if key in _odds_cache:
        return _odds_cache[key]

    api_key = api_key or os.getenv("ODDS_API_KEY")
    if not api_key:
        _odds_cache[key] = None
        return None

    try:
        result = _fetch_from_api(fixture, api_key)
    except Exception:
        result = None

    _odds_cache[key] = result
    return result


def _fetch_from_api(fixture: Fixture, api_key: str) -> OddsResult | None:
    """Internal: hit the-odds-api.com and extract match odds."""
    url = (
        "https://api.the-odds-api.com/v4/sports/rugbyleague_nrl/odds/"
        f"?apiKey={api_key}&regions=au&markets=h2h"
    )
    req = urllib.request.Request(url=url, headers={"User-Agent": "FootyTippingBot/2.0"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    if not isinstance(data, list):
        return None

    home_norm = normalize_team_name_for_odds(fixture.home_team)
    away_norm = normalize_team_name_for_odds(fixture.away_team)

    for event in data:
        # Try to match event teams to fixture teams
        event_teams = event.get("teams", [])
        if not event_teams:
            # Try home/away team objects
            h = event.get("home_team", "")
            a = event.get("away_team", "")
            event_teams = [h, a] if h and a else []

        mapped = {normalize_team_name_for_odds(t) for t in event_teams}
        if home_norm not in mapped or away_norm not in mapped:
            continue

        # Average across bookmakers for robustness
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        home_prices: list[float] = []
        away_prices: list[float] = []

        for bk in bookmakers:
            for market in bk.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                outcomes = {
                    normalize_team_name_for_odds(o.get("name", "")): o.get("price", 0)
                    for o in market.get("outcomes", [])
                }
                hp = outcomes.get(home_norm)
                ap = outcomes.get(away_norm)
                if hp and ap and hp > 1 and ap > 1:
                    home_prices.append(float(hp))
                    away_prices.append(float(ap))

        if not home_prices or not away_prices:
            continue

        avg_home = sum(home_prices) / len(home_prices)
        avg_away = sum(away_prices) / len(away_prices)
        home_prob, away_prob = de_vig(avg_home, avg_away)

        return OddsResult(
            home_prob=round(home_prob, 4),
            away_prob=round(away_prob, 4),
            source="the-odds-api",
            fetched_at=datetime.now(tz=timezone.utc).isoformat(),
        )

    return None
