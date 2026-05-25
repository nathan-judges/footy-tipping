"""Weather data integration for NRL match prediction.

Provides weather data fetching, caching, and fallback mechanisms for
match venue conditions that affect gameplay and scoring patterns.

Uses the Open-Meteo Archive API (https://archive-api.open-meteo.com/v1/archive)
which is free and requires no authentication.  Fetched data is cached to
``data/weather_cache.json`` keyed by ``"{venue}|{date}"`` to avoid redundant
API calls on subsequent pipeline runs.

When the API is unavailable or returns an error, ``fetch_weather`` returns
``None`` and callers should use ``get_venue_season_average`` as a fallback.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Path to the weather cache file (relative to project root / CWD)
_CACHE_PATH = Path("data/weather_cache.json")

# ---------------------------------------------------------------------------
# Weather data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeatherData:
    """Weather conditions for a match venue and time.
    
    Attributes:
        venue: NRL venue name (e.g., "Suncorp Stadium")
        timestamp: ISO-8601 timestamp of the match kickoff
        temperature_c: Temperature in Celsius
        precipitation_mm: Precipitation amount in millimeters
        wind_speed_kmh: Wind speed in kilometers per hour
        conditions: Human-readable weather description
        source: Data source identifier for tracking
        cached: Whether this data was loaded from cache
    """

    venue: str
    timestamp: str  # ISO-8601
    temperature_c: float
    precipitation_mm: float
    wind_speed_kmh: float
    conditions: str  # "clear", "rain", "overcast", etc.
    source: str  # "openweathermap", "weatherapi", "fallback"
    cached: bool = False


# ---------------------------------------------------------------------------
# Venue coordinate mapping
# ---------------------------------------------------------------------------

#: Latitude/longitude coordinates for all 16 NRL venues.
#: Used to fetch weather data from location-based APIs.
VENUE_COORDINATES: dict[str, tuple[float, float]] = {
    "Accor Stadium": (-33.8474, 151.0631),
    "Suncorp Stadium": (-27.4648, 153.0095),
    "AAMI Park": (-37.8250, 144.9834),
    "CommBank Stadium": (-33.8005, 150.9820),
    "Allianz Stadium": (-33.8886, 151.2250),
    "McDonald Jones Stadium": (-32.9167, 151.7500),
    "Queensland Country Bank Stadium": (-19.2590, 146.8169),
    "GIO Stadium": (-35.2533, 149.1028),
    "Cbus Super Stadium": (-28.0667, 153.3833),
    "PointsBet Stadium": (-34.0667, 151.1333),
    "Brookvale Oval": (-33.7667, 151.2667),
    "Leichhardt Oval": (-33.8833, 151.1500),
    "Campbelltown Sports Stadium": (-34.0667, 150.8167),
    "Mt Smart Stadium": (-36.9167, 174.7833),
    "WIN Stadium": (-34.4167, 150.8833),
    "Apollo Projects Stadium": (-27.5833, 153.0500),
}


def get_venue_coordinates(venue: str) -> tuple[float, float] | None:
    """Map an NRL venue name to its latitude/longitude coordinates.

    Performs an exact match first, then falls back to a case-insensitive
    substring search so that minor name variations (e.g. missing "Stadium"
    suffix) still resolve correctly.

    Args:
        venue: NRL venue name to look up.

    Returns:
        A ``(latitude, longitude)`` tuple, or ``None`` if the venue is not
        found in the mapping.

    Examples:
        >>> get_venue_coordinates("Suncorp Stadium")
        (-27.4648, 153.0095)
        >>> get_venue_coordinates("suncorp stadium")
        (-27.4648, 153.0095)
        >>> get_venue_coordinates("Unknown Venue")
        None
    """
    # Exact match (fast path)
    if venue in VENUE_COORDINATES:
        return VENUE_COORDINATES[venue]

    # Case-insensitive exact match
    venue_lower = venue.strip().lower()
    for known_venue, coords in VENUE_COORDINATES.items():
        if known_venue.lower() == venue_lower:
            return coords

    # Fuzzy fallback: check if the query is a non-empty substring of a known venue
    # or vice-versa (handles truncated/abbreviated names)
    if venue_lower:
        for known_venue, coords in VENUE_COORDINATES.items():
            known_lower = known_venue.lower()
            if venue_lower in known_lower or known_lower in venue_lower:
                return coords

    return None


# ---------------------------------------------------------------------------
# Venue season averages (fallback data)
# ---------------------------------------------------------------------------

#: Historical average weather conditions per venue per month.
#: Keyed by (venue, month) where month is 1-12.
#: Values are (temperature_c, precipitation_mm, wind_speed_kmh).
#: Based on typical Australian climate data for each city.
_VENUE_SEASON_AVERAGES: dict[tuple[str, int], tuple[float, float, float]] = {
    # Suncorp Stadium (Brisbane) — subtropical, warm and wet in summer
    ("Suncorp Stadium", 1): (29.0, 8.0, 12.0),
    ("Suncorp Stadium", 2): (28.5, 9.0, 11.0),
    ("Suncorp Stadium", 3): (27.0, 7.0, 11.0),
    ("Suncorp Stadium", 4): (24.0, 3.0, 12.0),
    ("Suncorp Stadium", 5): (21.0, 2.0, 13.0),
    ("Suncorp Stadium", 6): (18.5, 1.5, 14.0),
    ("Suncorp Stadium", 7): (18.0, 1.0, 14.0),
    ("Suncorp Stadium", 8): (19.0, 1.0, 15.0),
    ("Suncorp Stadium", 9): (22.0, 2.0, 14.0),
    ("Suncorp Stadium", 10): (25.0, 4.0, 13.0),
    ("Suncorp Stadium", 11): (27.0, 6.0, 12.0),
    ("Suncorp Stadium", 12): (28.5, 8.0, 12.0),
    # Accor Stadium (Sydney) — temperate, mild year-round
    ("Accor Stadium", 1): (26.0, 4.0, 15.0),
    ("Accor Stadium", 2): (25.5, 5.0, 14.0),
    ("Accor Stadium", 3): (24.0, 4.0, 14.0),
    ("Accor Stadium", 4): (21.0, 3.0, 14.0),
    ("Accor Stadium", 5): (18.0, 3.0, 15.0),
    ("Accor Stadium", 6): (15.5, 3.0, 16.0),
    ("Accor Stadium", 7): (15.0, 2.5, 16.0),
    ("Accor Stadium", 8): (16.0, 2.5, 17.0),
    ("Accor Stadium", 9): (18.5, 2.5, 16.0),
    ("Accor Stadium", 10): (21.0, 3.0, 15.0),
    ("Accor Stadium", 11): (23.0, 3.5, 15.0),
    ("Accor Stadium", 12): (25.0, 4.0, 15.0),
    # AAMI Park (Melbourne) — temperate oceanic, variable
    ("AAMI Park", 1): (25.0, 3.0, 18.0),
    ("AAMI Park", 2): (25.0, 3.0, 17.0),
    ("AAMI Park", 3): (22.0, 3.5, 17.0),
    ("AAMI Park", 4): (18.0, 3.5, 17.0),
    ("AAMI Park", 5): (14.5, 4.0, 18.0),
    ("AAMI Park", 6): (12.0, 4.5, 19.0),
    ("AAMI Park", 7): (11.5, 4.0, 19.0),
    ("AAMI Park", 8): (12.5, 4.0, 20.0),
    ("AAMI Park", 9): (15.0, 3.5, 19.0),
    ("AAMI Park", 10): (18.0, 3.0, 18.0),
    ("AAMI Park", 11): (21.0, 3.0, 18.0),
    ("AAMI Park", 12): (23.0, 3.0, 18.0),
    # GIO Stadium (Canberra) — continental, cold winters
    ("GIO Stadium", 1): (27.0, 2.5, 14.0),
    ("GIO Stadium", 2): (26.5, 3.0, 13.0),
    ("GIO Stadium", 3): (23.0, 3.0, 13.0),
    ("GIO Stadium", 4): (18.0, 2.5, 13.0),
    ("GIO Stadium", 5): (13.0, 2.0, 14.0),
    ("GIO Stadium", 6): (9.0, 2.0, 14.0),
    ("GIO Stadium", 7): (8.0, 1.5, 14.0),
    ("GIO Stadium", 8): (10.0, 1.5, 15.0),
    ("GIO Stadium", 9): (14.0, 2.0, 15.0),
    ("GIO Stadium", 10): (18.0, 2.5, 14.0),
    ("GIO Stadium", 11): (22.0, 2.5, 14.0),
    ("GIO Stadium", 12): (25.0, 2.5, 14.0),
    # Mt Smart Stadium (Auckland, NZ) — temperate maritime
    ("Mt Smart Stadium", 1): (23.0, 4.0, 16.0),
    ("Mt Smart Stadium", 2): (23.0, 4.5, 15.0),
    ("Mt Smart Stadium", 3): (21.0, 4.5, 15.0),
    ("Mt Smart Stadium", 4): (18.0, 4.0, 16.0),
    ("Mt Smart Stadium", 5): (15.0, 4.0, 17.0),
    ("Mt Smart Stadium", 6): (13.0, 4.5, 18.0),
    ("Mt Smart Stadium", 7): (12.0, 4.5, 18.0),
    ("Mt Smart Stadium", 8): (12.5, 4.0, 18.0),
    ("Mt Smart Stadium", 9): (14.0, 3.5, 17.0),
    ("Mt Smart Stadium", 10): (16.0, 3.5, 16.0),
    ("Mt Smart Stadium", 11): (18.5, 3.5, 16.0),
    ("Mt Smart Stadium", 12): (21.0, 4.0, 16.0),
    # Queensland Country Bank Stadium (Townsville) — tropical
    ("Queensland Country Bank Stadium", 1): (31.0, 12.0, 10.0),
    ("Queensland Country Bank Stadium", 2): (30.5, 13.0, 10.0),
    ("Queensland Country Bank Stadium", 3): (29.0, 10.0, 10.0),
    ("Queensland Country Bank Stadium", 4): (27.0, 4.0, 11.0),
    ("Queensland Country Bank Stadium", 5): (24.0, 1.5, 12.0),
    ("Queensland Country Bank Stadium", 6): (22.0, 0.5, 13.0),
    ("Queensland Country Bank Stadium", 7): (21.5, 0.5, 13.0),
    ("Queensland Country Bank Stadium", 8): (23.0, 0.5, 13.0),
    ("Queensland Country Bank Stadium", 9): (26.0, 1.0, 12.0),
    ("Queensland Country Bank Stadium", 10): (28.0, 3.0, 11.0),
    ("Queensland Country Bank Stadium", 11): (30.0, 7.0, 10.0),
    ("Queensland Country Bank Stadium", 12): (31.0, 11.0, 10.0),
    # Cbus Super Stadium (Gold Coast) — subtropical
    ("Cbus Super Stadium", 1): (28.5, 7.0, 14.0),
    ("Cbus Super Stadium", 2): (28.0, 8.0, 13.0),
    ("Cbus Super Stadium", 3): (27.0, 6.0, 13.0),
    ("Cbus Super Stadium", 4): (24.0, 3.0, 14.0),
    ("Cbus Super Stadium", 5): (21.0, 2.0, 15.0),
    ("Cbus Super Stadium", 6): (18.5, 1.5, 16.0),
    ("Cbus Super Stadium", 7): (18.0, 1.0, 16.0),
    ("Cbus Super Stadium", 8): (19.0, 1.0, 17.0),
    ("Cbus Super Stadium", 9): (22.0, 2.0, 16.0),
    ("Cbus Super Stadium", 10): (24.5, 3.5, 15.0),
    ("Cbus Super Stadium", 11): (26.5, 5.0, 14.0),
    ("Cbus Super Stadium", 12): (28.0, 7.0, 14.0),
}

#: Default average conditions used when a venue/month combination is not
#: found in _VENUE_SEASON_AVERAGES.
_DEFAULT_AVERAGES: tuple[float, float, float] = (20.0, 2.0, 12.0)

#: Venues that share climate data with a primary venue.
_VENUE_CLIMATE_ALIASES: dict[str, str] = {
    "CommBank Stadium": "Accor Stadium",       # Western Sydney — similar to Sydney
    "Allianz Stadium": "Accor Stadium",         # Eastern Sydney
    "PointsBet Stadium": "Accor Stadium",       # Southern Sydney
    "Brookvale Oval": "Accor Stadium",          # Northern Beaches, Sydney
    "Leichhardt Oval": "Accor Stadium",         # Inner West, Sydney
    "Campbelltown Sports Stadium": "Accor Stadium",  # South-West Sydney
    "McDonald Jones Stadium": "Accor Stadium",  # Newcastle — similar to Sydney
    "WIN Stadium": "Accor Stadium",             # Wollongong — similar to Sydney
    "Apollo Projects Stadium": "Suncorp Stadium",  # Brisbane area
}


def get_venue_season_average(venue: str, month: int) -> WeatherData:
    """Return average weather conditions for a venue in a given month.

    Used as a fallback when the Open-Meteo API is unavailable or returns
    an error.  Looks up pre-computed historical averages for the venue/month
    combination.  Falls back to a generic default when the venue is not in
    the averages table.

    Args:
        venue: NRL venue name (e.g. ``"Suncorp Stadium"``).
        month: Calendar month as an integer (1 = January, 12 = December).

    Returns:
        A :class:`WeatherData` instance with ``source="fallback"`` and
        ``cached=False``.
    """
    # Resolve climate alias if needed
    lookup_venue = _VENUE_CLIMATE_ALIASES.get(venue, venue)

    key = (lookup_venue, month)
    temp, precip, wind = _VENUE_SEASON_AVERAGES.get(key, _DEFAULT_AVERAGES)

    return WeatherData(
        venue=venue,
        timestamp=f"2000-{month:02d}-01T00:00:00Z",  # placeholder timestamp
        temperature_c=temp,
        precipitation_mm=precip,
        wind_speed_kmh=wind,
        conditions="fallback",
        source="fallback",
        cached=False,
    )


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _load_cache(cache_path: Path) -> dict[str, dict]:
    """Load the weather cache from disk.

    Returns an empty dict if the file does not exist or cannot be parsed.

    Args:
        cache_path: Path to the JSON cache file.

    Returns:
        Dict mapping ``"{venue}|{date}"`` keys to weather data dicts.
    """
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read weather cache from '%s': %s", cache_path, exc)
        return {}


def _save_cache(cache: dict[str, dict], cache_path: Path) -> None:
    """Persist the weather cache to disk.

    Creates parent directories if they do not exist.  Logs a warning on
    write failure but does not raise — a cache write failure is non-fatal.

    Args:
        cache: The full cache dict to write.
        cache_path: Path to the JSON cache file.
    """
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(cache, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Failed to write weather cache to '%s': %s", cache_path, exc)


def _cache_key(venue: str, date: str) -> str:
    """Build the cache key for a venue/date pair.

    Args:
        venue: NRL venue name.
        date: Date string in ``YYYY-MM-DD`` format.

    Returns:
        Cache key string in the form ``"{venue}|{date}"``.
    """
    return f"{venue}|{date}"


def _weather_data_from_dict(d: dict) -> WeatherData:
    """Reconstruct a :class:`WeatherData` from a cached dict.

    Args:
        d: Dict previously serialised from a :class:`WeatherData` instance.

    Returns:
        A :class:`WeatherData` with ``cached=True``.
    """
    return WeatherData(
        venue=d["venue"],
        timestamp=d["timestamp"],
        temperature_c=float(d["temperature_c"]),
        precipitation_mm=float(d["precipitation_mm"]),
        wind_speed_kmh=float(d["wind_speed_kmh"]),
        conditions=d.get("conditions", "unknown"),
        source=d.get("source", "open-meteo"),
        cached=True,
    )


def _weather_data_to_dict(wd: WeatherData) -> dict:
    """Serialise a :class:`WeatherData` to a plain dict for caching.

    Args:
        wd: The :class:`WeatherData` instance to serialise.

    Returns:
        A JSON-serialisable dict.
    """
    return {
        "venue": wd.venue,
        "timestamp": wd.timestamp,
        "temperature_c": wd.temperature_c,
        "precipitation_mm": wd.precipitation_mm,
        "wind_speed_kmh": wd.wind_speed_kmh,
        "conditions": wd.conditions,
        "source": wd.source,
    }


# ---------------------------------------------------------------------------
# Open-Meteo API integration
# ---------------------------------------------------------------------------

#: Open-Meteo Archive API endpoint.
_OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

#: Request timeout in seconds.
_REQUEST_TIMEOUT = 10


def _fetch_from_open_meteo(
    venue: str,
    date: str,
    lat: float,
    lon: float,
) -> WeatherData | None:
    """Call the Open-Meteo Archive API for a specific venue and date.

    Requests hourly temperature, precipitation, and wind speed for the
    given date, then averages the values across the day.

    Args:
        venue: NRL venue name (used to populate the returned dataclass).
        date: Date in ``YYYY-MM-DD`` format.
        lat: Latitude of the venue.
        lon: Longitude of the venue.

    Returns:
        A :class:`WeatherData` instance on success, or ``None`` on any
        network or parsing error.
    """
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "start_date": date,
        "end_date": date,
        "hourly": "temperature_2m,precipitation,wind_speed_10m",
        "timezone": "auto",
    }
    url = f"{_OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=_REQUEST_TIMEOUT) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Open-Meteo API request failed for %s on %s: %s", venue, date, exc)
        return None

    try:
        hourly = raw.get("hourly", {})
        temps: list[float] = [t for t in hourly.get("temperature_2m", []) if t is not None]
        precips: list[float] = [p for p in hourly.get("precipitation", []) if p is not None]
        winds: list[float] = [w for w in hourly.get("wind_speed_10m", []) if w is not None]

        if not temps or not precips or not winds:
            logger.warning(
                "Open-Meteo returned empty data for %s on %s", venue, date
            )
            return None

        avg_temp = sum(temps) / len(temps)
        total_precip = sum(precips)  # daily total precipitation
        avg_wind = sum(winds) / len(winds)

        # Determine conditions label
        if total_precip > 5.0:
            conditions = "rain"
        elif total_precip > 0.5:
            conditions = "light_rain"
        else:
            conditions = "clear"

        return WeatherData(
            venue=venue,
            timestamp=f"{date}T00:00:00Z",
            temperature_c=round(avg_temp, 1),
            precipitation_mm=round(total_precip, 1),
            wind_speed_kmh=round(avg_wind, 1),
            conditions=conditions,
            source="open-meteo",
            cached=False,
        )
    except (KeyError, TypeError, ZeroDivisionError) as exc:
        logger.warning(
            "Failed to parse Open-Meteo response for %s on %s: %s", venue, date, exc
        )
        return None


def fetch_weather(
    venue: str,
    kickoff_at: str,
    *,
    use_cache: bool = True,
    cache_path: Path | None = None,
) -> WeatherData | None:
    """Fetch weather data for a venue and kickoff time.

    Checks the local cache first (keyed by ``"{venue}|{date}"``).  On a
    cache miss, calls the Open-Meteo Archive API and writes the result back
    to the cache.

    Returns ``None`` when:
    - The venue is not in :data:`VENUE_COORDINATES`.
    - The kickoff timestamp cannot be parsed to extract a date.
    - The API call fails.

    Callers should use :func:`get_venue_season_average` as a fallback when
    this function returns ``None``.

    Args:
        venue: NRL venue name (e.g. ``"Suncorp Stadium"``).
        kickoff_at: ISO-8601 kickoff timestamp (e.g. ``"2026-05-10T19:30:00Z"``).
        use_cache: When ``True`` (default), read from and write to the local
            cache.  Set to ``False`` to always call the API.
        cache_path: Override the default cache file path
            (``data/weather_cache.json``).  Useful in tests.

    Returns:
        A :class:`WeatherData` instance, or ``None`` on failure.
    """
    resolved_cache_path = cache_path if cache_path is not None else _CACHE_PATH

    # Resolve venue coordinates
    coords = get_venue_coordinates(venue)
    if coords is None:
        logger.warning("Unknown venue '%s'; cannot fetch weather.", venue)
        return None

    # Extract date from kickoff timestamp
    try:
        date = kickoff_at[:10]  # "YYYY-MM-DD"
        if len(date) != 10 or date[4] != "-" or date[7] != "-":
            raise ValueError(f"Unexpected date format: {date!r}")
    except (IndexError, ValueError) as exc:
        logger.warning("Cannot parse date from kickoff_at=%r: %s", kickoff_at, exc)
        return None

    key = _cache_key(venue, date)

    # Cache read
    if use_cache:
        cache = _load_cache(resolved_cache_path)
        if key in cache:
            logger.debug("Weather cache hit for %s", key)
            try:
                return _weather_data_from_dict(cache[key])
            except (KeyError, TypeError) as exc:
                logger.warning("Corrupt cache entry for %s: %s; re-fetching.", key, exc)

    # API call
    lat, lon = coords
    weather = _fetch_from_open_meteo(venue, date, lat, lon)
    if weather is None:
        return None

    # Cache write
    if use_cache:
        cache = _load_cache(resolved_cache_path)
        cache[key] = _weather_data_to_dict(weather)
        _save_cache(cache, resolved_cache_path)

    return weather
