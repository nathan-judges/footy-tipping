"""Feature caching system for NRL prediction model.

Provides persistent caching of computed features to avoid redundant
calculations and ensure reproducibility across pipeline runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from .features import FeatureSet

# ---------------------------------------------------------------------------
# Feature cache data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CachedFeatures:
    """Cached feature set with metadata.
    
    Attributes:
        game_id: Unique identifier for the game (e.g., "2025-r01-g01")
        features: Complete feature set for the game
        computed_at: ISO-8601 timestamp when features were computed
        feature_version: Feature schema version for cache invalidation
    """

    game_id: str
    features: FeatureSet
    computed_at: str
    feature_version: str  # e.g., "v2.1"
