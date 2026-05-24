"""Weather data integration for NRL match prediction.

Provides weather data fetching, caching, and fallback mechanisms for
match venue conditions that affect gameplay and scoring patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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

    # Fuzzy fallback: check if the query is a substring of a known venue
    # or vice-versa (handles truncated/abbreviated names)
    for known_venue, coords in VENUE_COORDINATES.items():
        known_lower = known_venue.lower()
        if venue_lower in known_lower or known_lower in venue_lower:
            return coords

    return None
