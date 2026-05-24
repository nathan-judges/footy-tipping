"""Ensemble prediction model for NRL match tipping.

Combines three sub-models:
- ELO predictor (40% weight)
- Feature-based logistic model (35% weight)
- Market odds model (25% weight, redistributed when unavailable)

Replaces the previous hash-based placeholder with a genuine predictive
system built on historical data, real ELO ratings, and market signals.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from .elo_ratings import EloEngine, build_elo_from_history
from .features import FEATURE_NAMES, FeatureSet, extract_features, feature_vector
from .historical_data import MatchResult, load_all_history, normalize_team
from .odds_integration import OddsResult, fetch_match_odds
from .types import (
    Fixture,
    ModelDiagnostics,
    OddsSnapshot,
    SubPrediction,
    TipResult,
)

# ---------------------------------------------------------------------------
# Hand-tuned feature weights  (calibrated from NRL prediction research)
#
# These correspond to the features in features.FEATURE_NAMES:
#   elo_diff, home_advantage, form_diff, pd_per_game_diff,
#   ladder_pos_diff, rest_days_diff, h2h_advantage,
#   scoring_diff, defensive_diff
# ---------------------------------------------------------------------------

FEATURE_WEIGHTS: list[float] = [
    0.003,    # elo_diff — ~0.3% per ELO point
    0.30,     # home_advantage — significant boost
    1.20,     # form_diff — recent form differential
    0.05,     # pd_per_game_diff — points differential impact
    -0.08,    # ladder_pos_diff — negative because lower rank = better
    0.05,     # rest_days_diff — rest advantage
    0.15,     # h2h_advantage — head-to-head edge
    0.03,     # scoring_diff — scoring trend differential
    0.03,     # defensive_diff — defensive trend (already flipped in features.py)
]

# Sub-model weights
ELO_WEIGHT = 0.40
FEATURE_WEIGHT = 0.35
MARKET_WEIGHT = 0.25


# ---------------------------------------------------------------------------
# Sigmoid helper
# ---------------------------------------------------------------------------

def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid function."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    exp_x = math.exp(x)
    return exp_x / (1.0 + exp_x)


# ---------------------------------------------------------------------------
# Ensemble predictor
# ---------------------------------------------------------------------------

class EnsemblePredictor:
    """Three-model ensemble predictor for NRL fixtures.

    The predictor loads historical data, ELO ratings, and ladder data
    once and reuses them across all fixtures in a round.
    """

    def __init__(self) -> None:
        self.elo_engine: EloEngine | None = None
        self.history: list[MatchResult] = []
        self.ladder: dict = {}
        self._initialized = False

    def initialize(self) -> None:
        """Load all required data.  Safe to call multiple times."""
        if self._initialized:
            return

        # Load historical data
        try:
            self.history = load_all_history()
        except Exception:
            self.history = []

        # Load or build ELO
        elo_path = Path("data/elo_ratings.json")
        self.elo_engine = EloEngine()
        if elo_path.is_file():
            try:
                self.elo_engine.load(elo_path)
            except Exception:
                self.elo_engine = self._build_elo_fallback()
        elif self.history:
            self.elo_engine = build_elo_from_history(self.history)
        # else: fresh engine with default ratings

        # Load ladder
        ladder_path = Path("data/ladder.json")
        if ladder_path.is_file():
            try:
                self.ladder = json.loads(ladder_path.read_text(encoding="utf-8"))
            except Exception:
                self.ladder = {}

        self._initialized = True

    def _build_elo_fallback(self) -> EloEngine:
        """Build ELO from history when saved ratings are unavailable."""
        if self.history:
            return build_elo_from_history(self.history)
        return EloEngine()

    # -----------------------------------------------------------------
    # Sub-model 1: ELO predictor
    # -----------------------------------------------------------------

    def _elo_predict(
        self, fixture: Fixture
    ) -> tuple[str, float, int]:
        """Predict using ELO ratings."""
        assert self.elo_engine is not None
        return self.elo_engine.predict(fixture.home_team, fixture.away_team)

    # -----------------------------------------------------------------
    # Sub-model 2: Feature-based logistic model
    # -----------------------------------------------------------------

    def _feature_predict(
        self, fixture: Fixture
    ) -> tuple[str, float, FeatureSet]:
        """Predict using hand-weighted logistic regression on features."""
        assert self.elo_engine is not None

        features = extract_features(
            fixture, self.elo_engine, self.history, self.ladder
        )
        fv = feature_vector(features)

        # Dot product with weights
        logit = sum(w * x for w, x in zip(FEATURE_WEIGHTS, fv))
        home_prob = _sigmoid(logit)

        if home_prob >= 0.5:
            winner = fixture.home_team
            prob = home_prob
        else:
            winner = fixture.away_team
            prob = 1.0 - home_prob

        return winner, round(prob, 4), features

    # -----------------------------------------------------------------
    # Sub-model 3: Market odds
    # -----------------------------------------------------------------

    def _market_predict(
        self, fixture: Fixture
    ) -> tuple[str, float, OddsSnapshot | None] | None:
        """Predict using de-vigged market odds."""
        odds_result = fetch_match_odds(fixture)
        if odds_result is None:
            return None

        if odds_result.home_prob >= 0.5:
            winner = fixture.home_team
            prob = odds_result.home_prob
        else:
            winner = fixture.away_team
            prob = odds_result.away_prob

        # Create OddsSnapshot for backward compatibility
        snapshot = OddsSnapshot(
            home=round(odds_result.home_prob, 4),
            away=round(odds_result.away_prob, 4),
        )

        return winner, round(prob, 4), snapshot

    # -----------------------------------------------------------------
    # Ensemble
    # -----------------------------------------------------------------

    def predict_fixture(self, fixture: Fixture) -> TipResult:
        """Generate a prediction for a single fixture."""
        self.initialize()

        # Skip already-finished games
        if fixture.status != "upcoming":
            return TipResult(
                game_id=fixture.game_id,
                nrl_match_id=fixture.nrl_match_id,
                nrl_slug=fixture.nrl_slug,
                home_team=fixture.home_team,
                away_team=fixture.away_team,
                venue=fixture.venue,
                kickoff_at=fixture.kickoff_at,
                status=fixture.status,
                tip_team="N/A",
                confidence=0.0,
                predicted_margin=0,
                odds=None,
                home_score=fixture.home_score,
                away_score=fixture.away_score,
                actual_winner=fixture.actual_winner,
                actual_margin=fixture.actual_margin,
            )

        # Run sub-models
        elo_tip, elo_prob, elo_margin = self._elo_predict(fixture)
        feat_tip, feat_prob, features = self._feature_predict(fixture)
        market_result = self._market_predict(fixture)

        # Build sub-predictions for diagnostics
        sub_preds: list[SubPrediction] = []

        # Determine weights and ensemble probability
        if market_result is not None:
            mkt_tip, mkt_prob, odds_snapshot = market_result
            w_elo, w_feat, w_mkt = ELO_WEIGHT, FEATURE_WEIGHT, MARKET_WEIGHT
        else:
            mkt_tip, mkt_prob, odds_snapshot = None, None, None
            # Redistribute market weight
            w_elo = ELO_WEIGHT + MARKET_WEIGHT * (ELO_WEIGHT / (ELO_WEIGHT + FEATURE_WEIGHT))
            w_feat = FEATURE_WEIGHT + MARKET_WEIGHT * (FEATURE_WEIGHT / (ELO_WEIGHT + FEATURE_WEIGHT))
            w_mkt = 0.0

        # Convert to home-team probabilities for consistent averaging
        elo_home_prob = elo_prob if elo_tip == fixture.home_team else (1.0 - elo_prob)
        feat_home_prob = feat_prob if feat_tip == fixture.home_team else (1.0 - feat_prob)

        ensemble_home_prob = w_elo * elo_home_prob + w_feat * feat_home_prob

        sub_preds.append(SubPrediction(
            model_name="elo",
            tip_team=elo_tip,
            confidence=round(elo_prob, 4),
            weight=round(w_elo, 4),
        ))
        sub_preds.append(SubPrediction(
            model_name="features",
            tip_team=feat_tip,
            confidence=round(feat_prob, 4),
            weight=round(w_feat, 4),
        ))

        if market_result is not None and mkt_tip is not None and mkt_prob is not None:
            mkt_home_prob = mkt_prob if mkt_tip == fixture.home_team else (1.0 - mkt_prob)
            ensemble_home_prob += w_mkt * mkt_home_prob
            sub_preds.append(SubPrediction(
                model_name="market",
                tip_team=mkt_tip,
                confidence=round(mkt_prob, 4),
                weight=round(w_mkt, 4),
            ))

        # Final tip
        if ensemble_home_prob >= 0.5:
            final_tip = fixture.home_team
            final_confidence = ensemble_home_prob
        else:
            final_tip = fixture.away_team
            final_confidence = 1.0 - ensemble_home_prob

        # Build diagnostics
        assert self.elo_engine is not None
        diagnostics = ModelDiagnostics(
            elo_home=round(self.elo_engine.get_rating(fixture.home_team), 1),
            elo_away=round(self.elo_engine.get_rating(fixture.away_team), 1),
            sub_predictions=tuple(sub_preds),
            feature_summary={
                "elo_diff": round(features.elo_diff, 1),
                "form_diff": round(features.form_home_5 - features.form_away_5, 3),
                "ladder_pos_diff": features.ladder_pos_diff,
                "rest_days_diff": features.rest_days_home - features.rest_days_away,
                "h2h_home_wins": features.h2h_home_wins_recent,
            },
        )

        return TipResult(
            game_id=fixture.game_id,
            nrl_match_id=fixture.nrl_match_id,
            nrl_slug=fixture.nrl_slug,
            home_team=fixture.home_team,
            away_team=fixture.away_team,
            venue=fixture.venue,
            kickoff_at=fixture.kickoff_at,
            status=fixture.status,
            tip_team=final_tip,
            confidence=round(final_confidence, 4),
            predicted_margin=elo_margin,
            odds=odds_snapshot,
            diagnostics=diagnostics,
        )


# ---------------------------------------------------------------------------
# Backward-compatible entry point
# ---------------------------------------------------------------------------

def run_model(fixtures: list[Fixture]) -> list[TipResult]:
    """Generate predictions for all fixtures in a round.

    This preserves the original ``run_model`` interface so the rest of
    the pipeline continues to work without changes.
    """
    predictor = EnsemblePredictor()
    return [predictor.predict_fixture(f) for f in fixtures]
