"""Tests for scripts/lib/weather_api.py — venue coordinate mapping."""

from __future__ import annotations

import pytest

from scripts.lib.weather_api import VENUE_COORDINATES, get_venue_coordinates


class TestVenueCoordinates:
    """Tests for the VENUE_COORDINATES mapping."""

    def test_all_16_venues_present(self):
        """All 16 NRL venues must be in the mapping."""
        expected_venues = [
            "Accor Stadium",
            "Suncorp Stadium",
            "AAMI Park",
            "CommBank Stadium",
            "Allianz Stadium",
            "McDonald Jones Stadium",
            "Queensland Country Bank Stadium",
            "GIO Stadium",
            "Cbus Super Stadium",
            "PointsBet Stadium",
            "Brookvale Oval",
            "Leichhardt Oval",
            "Campbelltown Sports Stadium",
            "Mt Smart Stadium",
            "WIN Stadium",
            "Apollo Projects Stadium",
        ]
        for venue in expected_venues:
            assert venue in VENUE_COORDINATES, f"Missing venue: {venue}"

    def test_coordinates_are_tuples_of_floats(self):
        """Every coordinate entry must be a (float, float) tuple."""
        for venue, coords in VENUE_COORDINATES.items():
            assert isinstance(coords, tuple), f"{venue}: expected tuple, got {type(coords)}"
            assert len(coords) == 2, f"{venue}: expected 2 elements, got {len(coords)}"
            lat, lon = coords
            assert isinstance(lat, float), f"{venue}: lat must be float"
            assert isinstance(lon, float), f"{venue}: lon must be float"

    def test_latitudes_in_valid_range(self):
        """All latitudes must be in [-90, 90]."""
        for venue, (lat, _) in VENUE_COORDINATES.items():
            assert -90.0 <= lat <= 90.0, f"{venue}: lat {lat} out of range"

    def test_longitudes_in_valid_range(self):
        """All longitudes must be in [-180, 180]."""
        for venue, (_, lon) in VENUE_COORDINATES.items():
            assert -180.0 <= lon <= 180.0, f"{venue}: lon {lon} out of range"

    def test_australian_venues_have_negative_latitude(self):
        """Australian venues must be in the southern hemisphere (lat < 0)."""
        non_nz_venues = [v for v in VENUE_COORDINATES if "Smart" not in v]
        for venue in non_nz_venues:
            lat, _ = VENUE_COORDINATES[venue]
            assert lat < 0, f"{venue}: expected southern hemisphere latitude"

    def test_mt_smart_stadium_is_in_new_zealand(self):
        """Mt Smart Stadium (Auckland) must have a positive longitude ~174."""
        lat, lon = VENUE_COORDINATES["Mt Smart Stadium"]
        assert lat < 0, "Mt Smart Stadium should be in southern hemisphere"
        assert 170.0 <= lon <= 180.0, f"Mt Smart Stadium longitude {lon} not in NZ range"


class TestGetVenueCoordinates:
    """Tests for the get_venue_coordinates() function."""

    def test_exact_match_returns_coordinates(self):
        """Exact venue name lookup must return the correct coordinates."""
        result = get_venue_coordinates("Suncorp Stadium")
        assert result == (-27.4648, 153.0095)

    def test_case_insensitive_match(self):
        """Lookup must be case-insensitive."""
        assert get_venue_coordinates("suncorp stadium") == (-27.4648, 153.0095)
        assert get_venue_coordinates("SUNCORP STADIUM") == (-27.4648, 153.0095)
        assert get_venue_coordinates("Suncorp Stadium") == (-27.4648, 153.0095)

    def test_unknown_venue_returns_none(self):
        """An unrecognised venue name must return None."""
        assert get_venue_coordinates("Unknown Venue") is None
        assert get_venue_coordinates("") is None
        assert get_venue_coordinates("Totally Made Up Stadium") is None

    def test_all_known_venues_resolve(self):
        """Every venue in VENUE_COORDINATES must resolve via the function."""
        for venue, expected_coords in VENUE_COORDINATES.items():
            result = get_venue_coordinates(venue)
            assert result == expected_coords, f"Failed to resolve: {venue}"

    def test_return_type_is_tuple_or_none(self):
        """Return type must be tuple[float, float] or None."""
        result = get_venue_coordinates("AAMI Park")
        assert isinstance(result, tuple)
        assert len(result) == 2

        none_result = get_venue_coordinates("Nonexistent")
        assert none_result is None

    def test_fuzzy_match_partial_name(self):
        """Partial venue name should still resolve via fuzzy matching."""
        # "Suncorp" is a substring of "Suncorp Stadium"
        result = get_venue_coordinates("Suncorp")
        assert result == (-27.4648, 153.0095)

    def test_whitespace_is_stripped(self):
        """Leading/trailing whitespace in venue name should be handled."""
        result = get_venue_coordinates("  Suncorp Stadium  ")
        assert result == (-27.4648, 153.0095)
