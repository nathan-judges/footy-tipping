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


# ---------------------------------------------------------------------------
# Cache hit / miss tests (Requirement 2.4)
# ---------------------------------------------------------------------------

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from scripts.lib.weather_api import (
    WeatherData,
    fetch_weather,
    get_venue_season_average,
)


class TestWeatherCache:
    """Tests for cache read/write behaviour in fetch_weather."""

    def _make_cache_entry(self) -> dict:
        """Return a valid serialised WeatherData dict for cache seeding."""
        return {
            "venue": "Suncorp Stadium",
            "timestamp": "2026-05-10T00:00:00Z",
            "temperature_c": 22.5,
            "precipitation_mm": 1.0,
            "wind_speed_kmh": 14.0,
            "conditions": "clear",
            "source": "open-meteo",
        }

    def test_cache_hit_returns_cached_data(self):
        """When a cache entry exists for venue|date, fetch_weather returns it without calling the API."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            cache_path = Path(f.name)
            json.dump({"Suncorp Stadium|2026-05-10": self._make_cache_entry()}, f)

        try:
            with patch(
                "scripts.lib.weather_api._fetch_from_open_meteo"
            ) as mock_api:
                result = fetch_weather(
                    "Suncorp Stadium",
                    "2026-05-10T19:30:00Z",
                    use_cache=True,
                    cache_path=cache_path,
                )

            # API must NOT have been called
            mock_api.assert_not_called()
            assert result is not None
            assert result.temperature_c == 22.5
            assert result.precipitation_mm == 1.0
            assert result.wind_speed_kmh == 14.0
            assert result.cached is True
        finally:
            cache_path.unlink(missing_ok=True)

    def test_cache_miss_calls_api_and_writes_cache(self):
        """On a cache miss, fetch_weather calls the API and writes the result to cache."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            cache_path = Path(f.name)
            json.dump({}, f)  # empty cache

        api_response = WeatherData(
            venue="Suncorp Stadium",
            timestamp="2026-05-10T00:00:00Z",
            temperature_c=24.0,
            precipitation_mm=0.5,
            wind_speed_kmh=12.0,
            conditions="clear",
            source="open-meteo",
            cached=False,
        )

        try:
            with patch(
                "scripts.lib.weather_api._fetch_from_open_meteo",
                return_value=api_response,
            ) as mock_api:
                result = fetch_weather(
                    "Suncorp Stadium",
                    "2026-05-10T19:30:00Z",
                    use_cache=True,
                    cache_path=cache_path,
                )

            # API must have been called once
            mock_api.assert_called_once()
            assert result is not None
            assert result.temperature_c == 24.0

            # Cache file must now contain the entry
            written = json.loads(cache_path.read_text())
            assert "Suncorp Stadium|2026-05-10" in written
        finally:
            cache_path.unlink(missing_ok=True)

    def test_cache_miss_when_different_date(self):
        """A cache entry for a different date does not satisfy a request for another date."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            cache_path = Path(f.name)
            # Cache has entry for 2026-05-09, not 2026-05-10
            json.dump({"Suncorp Stadium|2026-05-09": self._make_cache_entry()}, f)

        api_response = WeatherData(
            venue="Suncorp Stadium",
            timestamp="2026-05-10T00:00:00Z",
            temperature_c=18.0,
            precipitation_mm=6.0,
            wind_speed_kmh=20.0,
            conditions="rain",
            source="open-meteo",
            cached=False,
        )

        try:
            with patch(
                "scripts.lib.weather_api._fetch_from_open_meteo",
                return_value=api_response,
            ) as mock_api:
                result = fetch_weather(
                    "Suncorp Stadium",
                    "2026-05-10T19:30:00Z",
                    use_cache=True,
                    cache_path=cache_path,
                )

            # API must have been called because the date differs
            mock_api.assert_called_once()
            assert result is not None
            assert result.temperature_c == 18.0
        finally:
            cache_path.unlink(missing_ok=True)

    def test_use_cache_false_bypasses_cache(self):
        """When use_cache=False, the cache is ignored and the API is always called."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            cache_path = Path(f.name)
            json.dump({"Suncorp Stadium|2026-05-10": self._make_cache_entry()}, f)

        api_response = WeatherData(
            venue="Suncorp Stadium",
            timestamp="2026-05-10T00:00:00Z",
            temperature_c=30.0,
            precipitation_mm=0.0,
            wind_speed_kmh=8.0,
            conditions="clear",
            source="open-meteo",
            cached=False,
        )

        try:
            with patch(
                "scripts.lib.weather_api._fetch_from_open_meteo",
                return_value=api_response,
            ) as mock_api:
                result = fetch_weather(
                    "Suncorp Stadium",
                    "2026-05-10T19:30:00Z",
                    use_cache=False,
                    cache_path=cache_path,
                )

            # API must have been called even though cache had an entry
            mock_api.assert_called_once()
            assert result is not None
            assert result.temperature_c == 30.0
        finally:
            cache_path.unlink(missing_ok=True)

    def test_cache_key_format_is_venue_pipe_date(self):
        """Cache entries are keyed by '{venue}|{YYYY-MM-DD}'."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            cache_path = Path(f.name)
            json.dump({}, f)

        api_response = WeatherData(
            venue="AAMI Park",
            timestamp="2026-06-15T00:00:00Z",
            temperature_c=12.0,
            precipitation_mm=3.0,
            wind_speed_kmh=18.0,
            conditions="overcast",
            source="open-meteo",
            cached=False,
        )

        try:
            with patch(
                "scripts.lib.weather_api._fetch_from_open_meteo",
                return_value=api_response,
            ):
                fetch_weather(
                    "AAMI Park",
                    "2026-06-15T19:30:00Z",
                    use_cache=True,
                    cache_path=cache_path,
                )

            written = json.loads(cache_path.read_text())
            assert "AAMI Park|2026-06-15" in written
        finally:
            cache_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Fallback on API failure tests (Requirement 2.2)
# ---------------------------------------------------------------------------


class TestWeatherFallback:
    """Tests for fallback behaviour when the API is unavailable."""

    def test_fetch_weather_returns_none_on_api_failure(self):
        """fetch_weather returns None when the API call fails."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            cache_path = Path(f.name)
            json.dump({}, f)

        try:
            with patch(
                "scripts.lib.weather_api._fetch_from_open_meteo",
                return_value=None,
            ):
                result = fetch_weather(
                    "Suncorp Stadium",
                    "2026-05-10T19:30:00Z",
                    use_cache=True,
                    cache_path=cache_path,
                )

            assert result is None
        finally:
            cache_path.unlink(missing_ok=True)

    def test_get_venue_season_average_returns_weather_data(self):
        """get_venue_season_average returns a WeatherData with source='fallback'."""
        result = get_venue_season_average("Suncorp Stadium", 7)
        assert isinstance(result, WeatherData)
        assert result.source == "fallback"
        assert result.venue == "Suncorp Stadium"

    def test_get_venue_season_average_has_valid_values(self):
        """Fallback weather values are within plausible ranges."""
        for month in range(1, 13):
            result = get_venue_season_average("Suncorp Stadium", month)
            assert -10.0 <= result.temperature_c <= 50.0
            assert result.precipitation_mm >= 0.0
            assert result.wind_speed_kmh >= 0.0

    def test_get_venue_season_average_unknown_venue_uses_defaults(self):
        """Unknown venue falls back to default averages without raising."""
        result = get_venue_season_average("Unknown Stadium", 6)
        assert isinstance(result, WeatherData)
        assert result.source == "fallback"
        # Default averages are (20.0, 2.0, 12.0)
        assert result.temperature_c == 20.0
        assert result.precipitation_mm == 2.0
        assert result.wind_speed_kmh == 12.0

    def test_get_venue_season_average_all_months_covered(self):
        """All 12 months return valid fallback data for a known venue."""
        for month in range(1, 13):
            result = get_venue_season_average("AAMI Park", month)
            assert isinstance(result, WeatherData)
            assert result.temperature_c > 0.0

    def test_get_venue_season_average_aliased_venue(self):
        """Venues with climate aliases resolve to the primary venue's averages."""
        # CommBank Stadium is aliased to Accor Stadium
        result_alias = get_venue_season_average("CommBank Stadium", 7)
        result_primary = get_venue_season_average("Accor Stadium", 7)
        assert result_alias.temperature_c == result_primary.temperature_c
        assert result_alias.precipitation_mm == result_primary.precipitation_mm
        assert result_alias.wind_speed_kmh == result_primary.wind_speed_kmh
        # But the venue name in the result should be the original, not the alias
        assert result_alias.venue == "CommBank Stadium"

    def test_fetch_weather_unknown_venue_returns_none(self):
        """fetch_weather returns None for an unrecognised venue."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            cache_path = Path(f.name)
            json.dump({}, f)

        try:
            result = fetch_weather(
                "Unknown Stadium",
                "2026-05-10T19:30:00Z",
                use_cache=True,
                cache_path=cache_path,
            )
            assert result is None
        finally:
            cache_path.unlink(missing_ok=True)

    def test_fetch_weather_invalid_kickoff_returns_none(self):
        """fetch_weather returns None when the kickoff timestamp is unparseable."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            cache_path = Path(f.name)
            json.dump({}, f)

        try:
            result = fetch_weather(
                "Suncorp Stadium",
                "not-a-date",
                use_cache=True,
                cache_path=cache_path,
            )
            assert result is None
        finally:
            cache_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# wet_weather flag at 5mm threshold tests (Requirement 2.3)
# ---------------------------------------------------------------------------


class TestWetWeatherFlag:
    """Tests for the wet_weather boolean flag at the 5mm precipitation threshold."""

    def _make_weather(self, precipitation_mm: float) -> WeatherData:
        return WeatherData(
            venue="Suncorp Stadium",
            timestamp="2026-05-10T19:30:00Z",
            temperature_c=20.0,
            precipitation_mm=precipitation_mm,
            wind_speed_kmh=12.0,
            conditions="rain" if precipitation_mm > 5.0 else "clear",
            source="open-meteo",
            cached=False,
        )

    def test_wet_weather_false_below_threshold(self):
        """wet_weather is False when precipitation < 5mm."""
        from scripts.lib.features import extract_features, FeatureSet
        from scripts.lib.elo_ratings import EloEngine
        from scripts.lib.types import Fixture

        fixture = Fixture(
            game_id="2026-r05-g01",
            nrl_match_id=None,
            nrl_slug=None,
            home_team="Broncos",
            away_team="Storm",
            venue="Suncorp Stadium",
            kickoff_at="2026-05-10T19:30:00Z",
            status="upcoming",
        )
        engine = EloEngine()
        weather = self._make_weather(4.9)
        features = extract_features(fixture, engine, [], {}, weather_data=weather)
        assert features.wet_weather is False

    def test_wet_weather_false_at_exactly_5mm(self):
        """wet_weather is False when precipitation is exactly 5mm (threshold is > 5mm)."""
        from scripts.lib.features import extract_features
        from scripts.lib.elo_ratings import EloEngine
        from scripts.lib.types import Fixture

        fixture = Fixture(
            game_id="2026-r05-g01",
            nrl_match_id=None,
            nrl_slug=None,
            home_team="Broncos",
            away_team="Storm",
            venue="Suncorp Stadium",
            kickoff_at="2026-05-10T19:30:00Z",
            status="upcoming",
        )
        engine = EloEngine()
        weather = self._make_weather(5.0)
        features = extract_features(fixture, engine, [], {}, weather_data=weather)
        assert features.wet_weather is False

    def test_wet_weather_true_above_threshold(self):
        """wet_weather is True when precipitation > 5mm."""
        from scripts.lib.features import extract_features
        from scripts.lib.elo_ratings import EloEngine
        from scripts.lib.types import Fixture

        fixture = Fixture(
            game_id="2026-r05-g01",
            nrl_match_id=None,
            nrl_slug=None,
            home_team="Broncos",
            away_team="Storm",
            venue="Suncorp Stadium",
            kickoff_at="2026-05-10T19:30:00Z",
            status="upcoming",
        )
        engine = EloEngine()
        weather = self._make_weather(5.1)
        features = extract_features(fixture, engine, [], {}, weather_data=weather)
        assert features.wet_weather is True

    def test_wet_weather_true_heavy_rain(self):
        """wet_weather is True for heavy rainfall (e.g. 25mm)."""
        from scripts.lib.features import extract_features
        from scripts.lib.elo_ratings import EloEngine
        from scripts.lib.types import Fixture

        fixture = Fixture(
            game_id="2026-r05-g01",
            nrl_match_id=None,
            nrl_slug=None,
            home_team="Broncos",
            away_team="Storm",
            venue="Suncorp Stadium",
            kickoff_at="2026-05-10T19:30:00Z",
            status="upcoming",
        )
        engine = EloEngine()
        weather = self._make_weather(25.0)
        features = extract_features(fixture, engine, [], {}, weather_data=weather)
        assert features.wet_weather is True

    def test_wet_weather_false_no_rain(self):
        """wet_weather is False when there is no precipitation."""
        from scripts.lib.features import extract_features
        from scripts.lib.elo_ratings import EloEngine
        from scripts.lib.types import Fixture

        fixture = Fixture(
            game_id="2026-r05-g01",
            nrl_match_id=None,
            nrl_slug=None,
            home_team="Broncos",
            away_team="Storm",
            venue="Suncorp Stadium",
            kickoff_at="2026-05-10T19:30:00Z",
            status="upcoming",
        )
        engine = EloEngine()
        weather = self._make_weather(0.0)
        features = extract_features(fixture, engine, [], {}, weather_data=weather)
        assert features.wet_weather is False

    def test_wet_weather_false_when_no_weather_data(self):
        """wet_weather defaults to False when weather_data is None."""
        from scripts.lib.features import extract_features, FeatureSet
        from scripts.lib.elo_ratings import EloEngine
        from scripts.lib.types import Fixture

        fixture = Fixture(
            game_id="2026-r05-g01",
            nrl_match_id=None,
            nrl_slug=None,
            home_team="Broncos",
            away_team="Storm",
            venue="Suncorp Stadium",
            kickoff_at="2026-05-10T19:30:00Z",
            status="upcoming",
        )
        engine = EloEngine()
        features = extract_features(fixture, engine, [], {}, weather_data=None)
        assert features.wet_weather is False
        assert features.precipitation_mm == 0.0

    def test_weather_fields_populated_from_weather_data(self):
        """All weather fields are correctly populated from a WeatherData object."""
        from scripts.lib.features import extract_features
        from scripts.lib.elo_ratings import EloEngine
        from scripts.lib.types import Fixture

        fixture = Fixture(
            game_id="2026-r05-g01",
            nrl_match_id=None,
            nrl_slug=None,
            home_team="Broncos",
            away_team="Storm",
            venue="Suncorp Stadium",
            kickoff_at="2026-05-10T19:30:00Z",
            status="upcoming",
        )
        engine = EloEngine()
        weather = WeatherData(
            venue="Suncorp Stadium",
            timestamp="2026-05-10T19:30:00Z",
            temperature_c=18.5,
            precipitation_mm=7.2,
            wind_speed_kmh=28.0,
            conditions="rain",
            source="open-meteo",
            cached=False,
        )
        features = extract_features(fixture, engine, [], {}, weather_data=weather)
        assert features.temperature_c == 18.5
        assert features.precipitation_mm == 7.2
        assert features.wind_speed_kmh == 28.0
        assert features.wet_weather is True  # 7.2 > 5.0
