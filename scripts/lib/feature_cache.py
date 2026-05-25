"""Feature caching system for NRL match prediction.

Persists computed features to JSON files to avoid redundant calculations
during model training and backtesting. Each cached feature set includes
a version identifier to ensure compatibility when the feature schema evolves.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .features import FeatureSet

logger = logging.getLogger(__name__)

#: Current feature version identifier.
#: Increment when FeatureSet schema changes to invalidate old cache entries.
FEATURE_VERSION = "v2.1"


@dataclass
class CachedFeatures:
    """Cached feature set with metadata.

    Attributes:
        game_id: Unique identifier for the fixture (e.g. "2026-r01-g01").
        features: The computed :class:`FeatureSet` for the fixture.
        computed_at: ISO-8601 timestamp when features were computed.
        feature_version: Version identifier (e.g. "v2.1") for schema compatibility.
    """

    game_id: str
    features: FeatureSet
    computed_at: str
    feature_version: str


def save_features(
    game_id: str,
    features: FeatureSet,
    cache_dir: Path | None = None,
) -> None:
    """Persist computed features to the cache.

    Creates a JSON file at ``{cache_dir}/{game_id}.json`` containing the
    feature set and metadata. The cache directory is created if it doesn't
    exist.

    Args:
        game_id: Unique identifier for the fixture (e.g. "2026-r01-g01").
        features: The computed :class:`FeatureSet` to cache.
        cache_dir: Directory for cached feature files. Defaults to
            ``data/features/`` if not specified.

    Example:
        >>> from scripts.lib.features import FeatureSet
        >>> features = FeatureSet(elo_diff=50.0, elo_home=1550.0, elo_away=1500.0)
        >>> save_features("2026-r01-g01", features)
    """
    cache_dir = cache_dir or Path("data/features")
    cache_dir.mkdir(parents=True, exist_ok=True)

    cached = CachedFeatures(
        game_id=game_id,
        features=features,
        computed_at=datetime.now(timezone.utc).isoformat(),
        feature_version=FEATURE_VERSION,
    )

    # Convert to dict for JSON serialization
    # Use asdict recursively to handle nested dataclasses
    cache_data: dict[str, Any] = {
        "game_id": cached.game_id,
        "features": asdict(cached.features),
        "computed_at": cached.computed_at,
        "feature_version": cached.feature_version,
    }

    path = cache_dir / f"{game_id}.json"
    try:
        path.write_text(json.dumps(cache_data, indent=2))
        logger.debug(
            "Cached features for game_id=%r to %s (version=%s)",
            game_id,
            path,
            FEATURE_VERSION,
        )
    except (OSError, TypeError) as e:
        logger.warning(
            "Failed to save features for game_id=%r: %s",
            game_id,
            e,
        )


def load_features(
    game_id: str,
    cache_dir: Path | None = None,
) -> FeatureSet | None:
    """Load cached features if available and valid.

    Returns ``None`` when:
    - The cache file does not exist
    - The cached feature version does not match the current version
    - The cache file contains invalid JSON or missing fields

    Args:
        game_id: Unique identifier for the fixture (e.g. "2026-r01-g01").
        cache_dir: Directory for cached feature files. Defaults to
            ``data/features/`` if not specified.

    Returns:
        The cached :class:`FeatureSet` if valid, otherwise ``None``.

    Example:
        >>> features = load_features("2026-r01-g01")
        >>> if features is not None:
        ...     print(f"Cache hit: elo_diff={features.elo_diff}")
        ... else:
        ...     print("Cache miss: need to compute features")
    """
    cache_dir = cache_dir or Path("data/features")
    path = cache_dir / f"{game_id}.json"

    if not path.exists():
        logger.debug("Cache miss for game_id=%r: file not found", game_id)
        return None

    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(
            "Failed to load cache for game_id=%r: %s",
            game_id,
            e,
        )
        return None

    # Validate feature version
    cached_version = data.get("feature_version")
    if cached_version != FEATURE_VERSION:
        logger.debug(
            "Cache version mismatch for game_id=%r: cached=%r, current=%r",
            game_id,
            cached_version,
            FEATURE_VERSION,
        )
        return None

    # Reconstruct FeatureSet from dict
    try:
        features_dict = data["features"]
        features = FeatureSet(**features_dict)
        logger.debug("Cache hit for game_id=%r", game_id)
        return features
    except (KeyError, TypeError) as e:
        logger.warning(
            "Invalid cache data for game_id=%r: %s",
            game_id,
            e,
        )
        return None


def extract_features_with_cache(
    fixture: Any,
    elo_engine: Any,
    history: list[Any],
    ladder: dict,
    weather_data: Any | None = None,
    injury_data: dict[str, Any] | None = None,
    cache_dir: Path | None = None,
) -> FeatureSet:
    """Extract features with caching layer.

    Attempts to load features from cache first. If cache miss or invalid,
    computes features using :func:`~scripts.lib.features.extract_features`,
    saves to cache, and returns the result.

    This function is the recommended entry point for feature extraction during
    model training and backtesting, as it avoids redundant computation for
    fixtures that have already been processed.

    Args:
        fixture: The upcoming or historical fixture to compute features for.
            Must have a ``game_id`` attribute.
        elo_engine: Trained ELO engine instance with current ratings.
        history: Chronologically sorted list of completed match results.
        ladder: Current ladder dict used for ladder position features.
        weather_data: Optional weather data for the fixture's venue and time.
        injury_data: Optional mapping of team name to injury status.
        cache_dir: Directory for cached feature files. Defaults to
            ``data/features/`` if not specified.

    Returns:
        A fully populated :class:`FeatureSet` for the fixture.

    Example:
        >>> from scripts.lib.elo import EloEngine
        >>> from scripts.lib.features import extract_features_with_cache
        >>> elo_engine = EloEngine()
        >>> features = extract_features_with_cache(
        ...     fixture, elo_engine, history, ladder,
        ...     weather_data=weather, injury_data=injuries
        ... )
        >>> # Second call for same fixture will use cache
        >>> features_cached = extract_features_with_cache(
        ...     fixture, elo_engine, history, ladder,
        ...     weather_data=weather, injury_data=injuries
        ... )
    """
    # Import here to avoid circular dependency
    from .features import extract_features

    # Try cache first
    cached = load_features(fixture.game_id, cache_dir=cache_dir)
    if cached is not None:
        return cached

    # Cache miss: compute fresh features
    logger.debug("Computing features for game_id=%r", fixture.game_id)
    features = extract_features(
        fixture=fixture,
        elo_engine=elo_engine,
        history=history,
        ladder=ladder,
        weather_data=weather_data,
        injury_data=injury_data,
    )

    # Save to cache for future use
    save_features(fixture.game_id, features, cache_dir=cache_dir)

    return features
