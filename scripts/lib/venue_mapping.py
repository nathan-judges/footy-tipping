"""NRL venue coordinates and travel distance calculator.

Maps venues to geographic coordinates and computes great-circle travel
distances for contextual features (travel burden, home-ground advantage).
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Venue coordinates  (latitude, longitude)
# ---------------------------------------------------------------------------

VENUE_COORDS: dict[str, tuple[float, float]] = {
    # Sydney metro
    "Accor Stadium": (-33.8474, 151.0632),
    "Stadium Australia": (-33.8474, 151.0632),
    "ANZ Stadium": (-33.8474, 151.0632),
    "Allianz Stadium": (-33.8918, 151.2249),
    "Sydney Football Stadium": (-33.8918, 151.2249),
    "CommBank Stadium": (-33.8070, 151.0624),
    "Bankwest Stadium": (-33.8070, 151.0624),
    "Leichhardt Oval": (-33.8834, 151.1534),
    "Campbelltown Sports Stadium": (-34.0782, 150.8239),
    "4 Pines Park": (-33.7963, 151.2744),
    "Brookvale Oval": (-33.7963, 151.2744),
    "BlueBet Stadium": (-33.7506, 150.6880),
    "Panthers Stadium": (-33.7506, 150.6880),
    "Ocean Protect Stadium": (-34.0376, 151.1154),
    "Shark Park": (-34.0376, 151.1154),
    "PointsBet Stadium": (-34.0376, 151.1154),
    # Newcastle
    "McDonald Jones Stadium": (-32.9205, 151.7673),
    # Wollongong
    "WIN Stadium": (-34.4437, 150.8800),
    # Canberra
    "GIO Stadium": (-35.2540, 149.0992),
    # Brisbane / Gold Coast / Sunshine Coast
    "Suncorp Stadium": (-27.4647, 153.0094),
    "Lang Park": (-27.4647, 153.0094),
    "Cbus Super Stadium": (-28.0024, 153.4100),
    "Robina Stadium": (-28.0024, 153.4100),
    "Kayo Stadium": (-26.7962, 153.1174),
    "Sunshine Coast Stadium": (-26.7962, 153.1174),
    # Townsville
    "Queensland Country Bank Stadium": (-19.2587, 146.7866),
    "Townsville Stadium": (-19.2587, 146.7866),
    # Melbourne
    "AAMI Park": (-37.8253, 144.9832),
    "Melbourne Rectangular Stadium": (-37.8253, 144.9832),
    # New Zealand
    "Go Media Stadium": (-36.8910, 174.7170),
    "Mt Smart Stadium": (-36.8910, 174.7170),
    "Hnry Stadium": (-36.8910, 174.7170),
    # Darwin
    "TIO Stadium": (-12.4091, 130.8727),
    # Perth
    "Optus Stadium": (-31.9512, 115.8891),
    # Jubilee (Kogarah)
    "St George Venues Jubilee Stadium": (-33.9655, 151.1150),
    "Jubilee Oval": (-33.9655, 151.1150),
    # Allegiant (Las Vegas)
    "Allegiant Stadium": (36.0908, -115.1833),
    # Mudgee / regional
    "Glen Willow Regional Sports Stadium": (-32.5886, 149.5810),
    # Bathurst
    "Carrington Park": (-33.4150, 149.5870),
}


# ---------------------------------------------------------------------------
# Team home venues (primary listed first)
# ---------------------------------------------------------------------------

TEAM_HOME_VENUES: dict[str, list[str]] = {
    "Broncos": ["Suncorp Stadium"],
    "Bulldogs": ["Accor Stadium", "CommBank Stadium"],
    "Cowboys": ["Queensland Country Bank Stadium"],
    "Dolphins": ["Suncorp Stadium", "Kayo Stadium"],
    "Dragons": ["WIN Stadium", "St George Venues Jubilee Stadium"],
    "Eels": ["CommBank Stadium"],
    "Knights": ["McDonald Jones Stadium"],
    "Panthers": ["BlueBet Stadium"],
    "Rabbitohs": ["Accor Stadium"],
    "Raiders": ["GIO Stadium"],
    "Roosters": ["Allianz Stadium"],
    "Sea Eagles": ["4 Pines Park"],
    "Sharks": ["Ocean Protect Stadium"],
    "Storm": ["AAMI Park"],
    "Titans": ["Cbus Super Stadium"],
    "Warriors": ["Go Media Stadium", "Hnry Stadium"],
    "Wests Tigers": ["Leichhardt Oval", "Campbelltown Sports Stadium", "CommBank Stadium"],
}


# ---------------------------------------------------------------------------
# Distance calculation
# ---------------------------------------------------------------------------

_EARTH_RADIUS_KM = 6371.0


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two geographic points."""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    return _EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fuzzy_lookup(venue: str) -> tuple[float, float] | None:
    """Look up venue coords with case-insensitive fuzzy matching."""
    # Exact match first
    if venue in VENUE_COORDS:
        return VENUE_COORDS[venue]
    # Case-insensitive
    lower = venue.lower()
    for name, coords in VENUE_COORDS.items():
        if name.lower() == lower:
            return coords
    # Substring containment
    for name, coords in VENUE_COORDS.items():
        if lower in name.lower() or name.lower() in lower:
            return coords
    return None


def travel_distance_km(venue_a: str, venue_b: str) -> float:
    """Great-circle distance in km between two venues.

    Returns ``0.0`` if either venue is unknown.
    """
    coords_a = _fuzzy_lookup(venue_a)
    coords_b = _fuzzy_lookup(venue_b)
    if coords_a is None or coords_b is None:
        return 0.0
    return round(_haversine(*coords_a, *coords_b), 1)


def team_travel_km(team: str, venue: str) -> float:
    """Distance from *team*'s primary home ground to *venue*.

    Returns ``0.0`` if the venue is the team's home ground or if
    coordinates are unknown.
    """
    if is_home_ground(team, venue):
        return 0.0
    home_venues = TEAM_HOME_VENUES.get(team, [])
    if not home_venues:
        return 0.0
    primary_home = home_venues[0]
    return travel_distance_km(primary_home, venue)


def is_home_ground(team: str, venue: str) -> bool:
    """Check whether *venue* is one of *team*'s home grounds.

    Uses case-insensitive substring matching to handle venue name
    variations.
    """
    home_venues = TEAM_HOME_VENUES.get(team, [])
    venue_lower = venue.lower()
    for hv in home_venues:
        if hv.lower() == venue_lower or hv.lower() in venue_lower or venue_lower in hv.lower():
            return True
    return False
