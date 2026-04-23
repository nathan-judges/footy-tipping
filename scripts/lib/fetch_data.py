"""Data fetch helpers for fixtures, ladder, and optional odds."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path

from .types import Fixture, OddsSnapshot

NRL_DRAW_ENDPOINT = "https://www.nrl.com/draw/data?competition=111&round={round_number}&season={season}"
NRL_LADDER_ENDPOINT = "https://www.nrl.com/ladder/data?competition=111&season={season}"
USER_AGENT = "FootyTippingBot/1.0"


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


def _request_text(url: str, headers: dict[str, str] | None = None, retries: int = 3) -> str:
    headers = headers or {}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url=url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Unreachable retry path")


def _fixture_status(raw_state: str | None, raw_mode: str | None) -> str:
    state = (raw_state or "").lower()
    mode = (raw_mode or "").lower()
    if state in {"fulltime", "post"} or mode == "post":
        return "finished"
    if state in {"live", "inprogress", "halftime"} or mode == "live":
        return "live"
    return "upcoming"


def _extract_slug(match_centre_url: str | None) -> str | None:
    if not match_centre_url:
        return None
    parts = [part for part in match_centre_url.split("/") if part]
    return parts[-1] if parts else None


def _extract_match_id(fixture_entry: dict) -> int | None:
    direct_candidates = [
        fixture_entry.get("matchId"),
        fixture_entry.get("id"),
    ]
    for candidate in direct_candidates:
        if isinstance(candidate, int):
            return candidate
        if isinstance(candidate, str) and candidate.isdigit():
            return int(candidate)

    for candidate in [fixture_entry.get("matchCentreUrl"), fixture_entry.get("callToAction", {}).get("url")]:
        if not isinstance(candidate, str):
            continue
        match = re.search(r"/match(?:es)?/(\d+)", candidate)
        if match:
            return int(match.group(1))
    return None


def parse_draw_fixtures(payload: dict, season: int, round_number: int) -> list[Fixture]:
    fixtures: list[Fixture] = []
    fixture_entries = payload.get("fixtures", [])
    for index, entry in enumerate(fixture_entries):
        if entry.get("type") != "Match":
            continue

        home = entry.get("homeTeam", {})
        away = entry.get("awayTeam", {})
        home_team = home.get("nickName")
        away_team = away.get("nickName")
        kickoff = entry.get("clock", {}).get("kickOffTimeLong")
        venue = entry.get("venue")
        if not all(isinstance(value, str) and value for value in [home_team, away_team, kickoff, venue]):
            continue

        status = _fixture_status(raw_state=entry.get("matchState"), raw_mode=entry.get("matchMode"))
        home_score = home.get("score")
        away_score = away.get("score")
        if status != "finished":
            home_score = None
            away_score = None

        actual_winner = None
        actual_margin = None
        if isinstance(home_score, int) and isinstance(away_score, int) and home_score != away_score:
            actual_winner = home_team if home_score > away_score else away_team
            actual_margin = abs(home_score - away_score)

        fixtures.append(
            Fixture(
                game_id=f"{season}-r{round_number:02d}-g{index + 1:02d}",
                nrl_match_id=_extract_match_id(entry),
                nrl_slug=_extract_slug(entry.get("matchCentreUrl")),
                home_team=home_team,
                away_team=away_team,
                venue=venue,
                kickoff_at=kickoff,
                status=status,  # type: ignore[arg-type]
                home_score=home_score if isinstance(home_score, int) else None,
                away_score=away_score if isinstance(away_score, int) else None,
                actual_winner=actual_winner,
                actual_margin=actual_margin,
            )
        )
    return fixtures


def fetch_round_fixtures(season: int, round_number: int) -> list[Fixture]:
    """Fetch all fixtures for a round from NRL draw API."""
    url = NRL_DRAW_ENDPOINT.format(season=season, round_number=round_number)
    payload = _request_json(url, headers={"User-Agent": USER_AGENT})
    return parse_draw_fixtures(payload=payload, season=season, round_number=round_number)


def fetch_ladder(season: int) -> dict:
    """Fetch and normalize ladder rows from NRL ladder API."""
    payload = _request_json(NRL_LADDER_ENDPOINT.format(season=season), headers={"User-Agent": USER_AGENT})
    positions = payload.get("positions", [])
    rows: list[dict] = []
    for index, entry in enumerate(positions):
        stats = entry.get("stats", {})
        team = entry.get("teamNickname")
        if not isinstance(team, str):
            continue

        rows.append(
            {
                "rank": index + 1,
                "team": team,
                "played": int(stats.get("played", 0)),
                "wins": int(stats.get("wins", 0)),
                "losses": int(stats.get("lost", 0)),
                "pointsFor": int(stats.get("points for", 0)),
                "pointsAgainst": int(stats.get("points against", 0)),
                "pointsDiff": int(stats.get("points difference", 0)),
                "competitionPoints": int(stats.get("points", 0)),
            }
        )
    return {"rows": rows}


def scrape_fixtures_html(season: int, round_number: int) -> list[Fixture]:
    """Fallback scraper that parses the embedded JSON blob from draw HTML."""
    url = f"https://www.nrl.com/draw/?competition=111&round={round_number}&season={season}"
    html = _request_text(url, headers={"User-Agent": USER_AGENT})
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">([\s\S]*?)</script>',
        html,
    )
    if not next_data_match:
        return []
    payload = json.loads(next_data_match.group(1))
    page_props = (
        payload.get("props", {}).get("pageProps", {}).get("draw")
        or payload.get("props", {}).get("pageProps", {})
    )
    if not isinstance(page_props, dict):
        return []
    return parse_draw_fixtures(payload=page_props, season=season, round_number=round_number)


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
                home_score=game.get("homeScore"),
                away_score=game.get("awayScore"),
                actual_winner=game.get("actualWinner"),
                actual_margin=game.get("actualMargin"),
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
