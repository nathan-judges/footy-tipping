"""Tests for feature caching system."""

import json
import tempfile
from pathlib import Path

import pytest

from scripts.lib.feature_cache import (
    FEATURE_VERSION,
    CachedFeatures,
    extract_features_with_cache,
    load_features,
    save_features,
)
from scripts.lib.features import FeatureSet


class TestFeatureCache:
    """Test suite for feature caching functionality."""

    def test_save_and_load_features(self, tmp_path: Path) -> None:
        """Test basic save and load cycle."""
        game_id = "2026-r01-g01"
        features = FeatureSet(
            elo_diff=50.0,
            elo_home=1550.0,
            elo_away=1500.0,
            form_home_5=0.6,
            form_away_5=0.4,
        )

        # Save features
        save_features(game_id, features, cache_dir=tmp_path)

        # Verify file was created
        cache_file = tmp_path / f"{game_id}.json"
        assert cache_file.exists()

        # Load features
        loaded = load_features(game_id, cache_dir=tmp_path)
        assert loaded is not None
        assert loaded.elo_diff == 50.0
        assert loaded.elo_home == 1550.0
        assert loaded.elo_away == 1500.0
        assert loaded.form_home_5 == 0.6
        assert loaded.form_away_5 == 0.4

    def test_load_nonexistent_cache(self, tmp_path: Path) -> None:
        """Test loading from nonexistent cache returns None."""
        result = load_features("nonexistent-game", cache_dir=tmp_path)
        assert result is None

    def test_version_mismatch_returns_none(self, tmp_path: Path) -> None:
        """Test that version mismatch causes cache miss."""
        game_id = "2026-r01-g02"
        cache_file = tmp_path / f"{game_id}.json"

        # Create cache with wrong version
        cache_data = {
            "game_id": game_id,
            "features": {
                "elo_diff": 30.0,
                "elo_home": 1530.0,
                "elo_away": 1500.0,
            },
            "computed_at": "2026-04-15T10:00:00Z",
            "feature_version": "v1.0",  # Wrong version
        }
        cache_file.write_text(json.dumps(cache_data))

        # Load should return None due to version mismatch
        result = load_features(game_id, cache_dir=tmp_path)
        assert result is None

    def test_malformed_json_returns_none(self, tmp_path: Path) -> None:
        """Test that malformed JSON is handled gracefully."""
        game_id = "2026-r01-g03"
        cache_file = tmp_path / f"{game_id}.json"

        # Write invalid JSON
        cache_file.write_text("{ invalid json }")

        # Load should return None
        result = load_features(game_id, cache_dir=tmp_path)
        assert result is None

    def test_missing_features_field_returns_none(self, tmp_path: Path) -> None:
        """Test that missing 'features' field is handled gracefully."""
        game_id = "2026-r01-g04"
        cache_file = tmp_path / f"{game_id}.json"

        # Create cache without 'features' field
        cache_data = {
            "game_id": game_id,
            "computed_at": "2026-04-15T10:00:00Z",
            "feature_version": FEATURE_VERSION,
        }
        cache_file.write_text(json.dumps(cache_data))

        # Load should return None
        result = load_features(game_id, cache_dir=tmp_path)
        assert result is None

    def test_cached_features_dataclass(self) -> None:
        """Test CachedFeatures dataclass structure."""
        features = FeatureSet(elo_diff=25.0)
        cached = CachedFeatures(
            game_id="2026-r01-g05",
            features=features,
            computed_at="2026-04-15T10:00:00Z",
            feature_version=FEATURE_VERSION,
        )

        assert cached.game_id == "2026-r01-g05"
        assert cached.features.elo_diff == 25.0
        assert cached.computed_at == "2026-04-15T10:00:00Z"
        assert cached.feature_version == FEATURE_VERSION

    def test_save_creates_directory(self) -> None:
        """Test that save_features creates cache directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "nested" / "cache"
            assert not cache_dir.exists()

            game_id = "2026-r01-g06"
            features = FeatureSet(elo_diff=15.0)

            save_features(game_id, features, cache_dir=cache_dir)

            assert cache_dir.exists()
            assert (cache_dir / f"{game_id}.json").exists()

    def test_all_feature_fields_preserved(self, tmp_path: Path) -> None:
        """Test that all FeatureSet fields are preserved in cache."""
        game_id = "2026-r01-g07"
        features = FeatureSet(
            elo_diff=50.0,
            elo_home=1550.0,
            elo_away=1500.0,
            home_advantage=1.0,
            form_home_5=0.6,
            form_away_5=0.4,
            pd_per_game_home=5.5,
            pd_per_game_away=-2.3,
            ladder_pos_diff=-3,
            rest_days_home=7,
            rest_days_away=5,
            h2h_home_wins_recent=2,
            scoring_trend_home=22.5,
            scoring_trend_away=18.3,
            defensive_trend_home=16.2,
            defensive_trend_away=20.1,
            travel_distance_km=1200.5,
            short_turnaround_home=False,
            short_turnaround_away=True,
            state_of_origin_round=True,
            origin_affected_home=2,
            origin_affected_away=1,
            venue_win_rate_home=0.65,
            venue_win_rate_away=0.45,
            rivalry_game=True,
            finals_match=False,
            temperature_c=18.5,
            precipitation_mm=2.3,
            wind_speed_kmh=15.2,
            wet_weather=False,
            injury_impact_home=0.3,
            injury_impact_away=0.8,
            key_player_out_home=False,
            key_player_out_away=True,
        )

        save_features(game_id, features, cache_dir=tmp_path)
        loaded = load_features(game_id, cache_dir=tmp_path)

        assert loaded is not None
        # Check a representative sample of fields
        assert loaded.elo_diff == 50.0
        assert loaded.travel_distance_km == 1200.5
        assert loaded.short_turnaround_away is True
        assert loaded.state_of_origin_round is True
        assert loaded.rivalry_game is True
        assert loaded.temperature_c == 18.5
        assert loaded.injury_impact_away == 0.8
        assert loaded.key_player_out_away is True

    def test_cache_hit_avoids_recomputation(self, tmp_path: Path, monkeypatch) -> None:
        """Test that cache hit avoids calling extract_features."""
        from scripts.lib.features import extract_features
        
        # Create a mock fixture
        class MockFixture:
            game_id = "2026-r01-g08"
            home_team = "Panthers"
            away_team = "Storm"
            venue = "CommBank Stadium"
            kickoff_at = "2026-04-15T19:00:00Z"

        fixture = MockFixture()

        # Pre-populate cache
        features = FeatureSet(elo_diff=40.0)
        save_features(fixture.game_id, features, cache_dir=tmp_path)

        # Track if extract_features was called
        extract_called = False

        def mock_extract(*args, **kwargs):
            nonlocal extract_called
            extract_called = True
            return FeatureSet(elo_diff=999.0)  # Different value

        # Patch where extract_features is imported (inside the function)
        monkeypatch.setattr("scripts.lib.features.extract_features", mock_extract)

        # Call extract_features_with_cache
        result = extract_features_with_cache(
            fixture,
            None,  # elo_engine (not used due to cache hit)
            [],    # history
            {},    # ladder
            cache_dir=tmp_path,
        )

        # Should return cached value without calling extract_features
        assert result.elo_diff == 40.0
        assert not extract_called

    def test_cache_miss_computes_and_saves(self, tmp_path: Path, monkeypatch) -> None:
        """Test that cache miss computes features and saves them."""
        from scripts.lib.features import extract_features
        
        # Create a mock fixture
        class MockFixture:
            game_id = "2026-r01-g09"
            home_team = "Broncos"
            away_team = "Cowboys"
            venue = "Suncorp Stadium"
            kickoff_at = "2026-04-15T19:00:00Z"

        fixture = MockFixture()

        # Mock extract_features to return a known value
        def mock_extract(*args, **kwargs):
            return FeatureSet(elo_diff=75.0)

        # Patch where extract_features is imported (inside the function)
        monkeypatch.setattr("scripts.lib.features.extract_features", mock_extract)

        # Call extract_features_with_cache (cache miss)
        result = extract_features_with_cache(
            fixture,
            None,  # elo_engine
            [],    # history
            {},    # ladder
            cache_dir=tmp_path,
        )

        # Should return computed value
        assert result.elo_diff == 75.0

        # Verify it was saved to cache
        cache_file = tmp_path / f"{fixture.game_id}.json"
        assert cache_file.exists()

        # Verify we can load it back
        loaded = load_features(fixture.game_id, cache_dir=tmp_path)
        assert loaded is not None
        assert loaded.elo_diff == 75.0
