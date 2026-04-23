"""Data fetch helpers for fixtures and optional odds."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path

from .types import Fixture, OddsSnapshot


def _request_json(url: str, headers: dict[str, str] | None = None, retries: int = 3) -> dict:
    headers = headers or {}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url=url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Unreachable retry path")


def load_seed_fixtures() -> list[Fixture]:
    """Load fixtures from the checked-in baked data file."""
    data_path = Path("data/current_round_tips.json")
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    fixtures: list[Fixture] = []
    for game in payload.get("games", []):
        fixtures.append(
            Fixture(
                game_id=game["gameId"],
                nrl_match_id=game.get("nrlMatchId"),
                nrl_slug=game.get("nrlSlug"),
                home_team=game["homeTeam"],
                away_team=game["awayTeam"],
                venue=game["venue"],
                kickoff_at=game["kickoffAt"],
                status=game.get("status", "upcoming"),
            )
        )
    return fixtures


def fetch_odds_for_fixture(fixture: Fixture) -> OddsSnapshot | None:
    """Fetch odds for one fixture if ODDS_API_KEY is configured."""
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        return None

    # Placeholder endpoint. Replace with selected odds provider endpoint.
    odds_url = (
        "https://api.the-odds-api.com/v4/sports/rugby_league_nrl/odds/"
        f"?apiKey={api_key}&regions=au&markets=h2h"
    )
    data = _request_json(odds_url)
    if not isinstance(data, list):
        return None

    home_key = fixture.home_team.lower()
    away_key = fixture.away_team.lower()
    for event in data:
        teams = [t.lower() for t in event.get("teams", [])]
        if home_key in teams and away_key in teams:
            bookmakers = event.get("bookmakers", [])
            if not bookmakers:
                return None
            markets = bookmakers[0].get("markets", [])
            if not markets:
                return None
            outcomes = markets[0].get("outcomes", [])
            prices = {o["name"].lower(): o["price"] for o in outcomes if "name" in o and "price" in o}
            home_price = prices.get(home_key)
            away_price = prices.get(away_key)
            if home_price and away_price:
                return OddsSnapshot(home=float(home_price), away=float(away_price))
    return None


def materialize_raw_inputs() -> dict:
    """Return a serializable snapshot of raw inputs used by the model."""
    fixtures = load_seed_fixtures()
    return {"fixtures": [asdict(f) for f in fixtures]}


def load_seed_ladder() -> dict:
    """Load ladder artifact seed until external ladder source is wired."""
    data_path = Path("data/ladder.json")
    return json.loads(data_path.read_text(encoding="utf-8"))
