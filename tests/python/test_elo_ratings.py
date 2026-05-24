"""Tests for the ELO rating engine."""

from pathlib import Path
import tempfile

from scripts.lib.elo_ratings import EloEngine, EloRating, build_elo_from_history
from scripts.lib.historical_data import MatchResult


def _make_result(**overrides) -> MatchResult:
    defaults = dict(
        season=2026,
        round_number=1,
        game_id="test-g01",
        home_team="Panthers",
        away_team="Dragons",
        venue="BlueBet Stadium",
        home_score=24,
        away_score=12,
        winner="Panthers",
        margin=12,
        kickoff_at="2026-03-06T09:00:00Z",
    )
    defaults.update(overrides)
    return MatchResult(**defaults)


def test_initial_rating_is_1500() -> None:
    engine = EloEngine()
    assert engine.get_rating("Panthers") == 1500.0
    assert engine.get_rating("SomeNewTeam") == 1500.0


def test_update_moves_ratings() -> None:
    engine = EloEngine()
    delta_h, delta_a = engine.update("Panthers", "Dragons", 24, 12)
    # Winner's rating goes up
    assert engine.get_rating("Panthers") > 1500.0
    # Loser's rating goes down
    assert engine.get_rating("Dragons") < 1500.0
    # Deltas are symmetric
    assert abs(delta_h + delta_a) < 0.001


def test_home_advantage_favours_home() -> None:
    engine = EloEngine(home_advantage=40.0)
    # At equal base ratings, home team should be favoured
    winner, prob, margin = engine.predict("TeamA", "TeamB")
    assert winner == "TeamA"
    assert prob > 0.5


def test_margin_multiplier_scales_with_blowout() -> None:
    engine = EloEngine()
    # A blowout win should change ratings more than a narrow win
    engine_narrow = EloEngine()
    engine_blowout = EloEngine()

    delta_narrow, _ = engine_narrow.update("TeamA", "TeamB", 20, 18)
    delta_blowout, _ = engine_blowout.update("TeamA", "TeamB", 40, 6)

    assert abs(delta_blowout) > abs(delta_narrow)


def test_regress_to_mean_moves_toward_1500() -> None:
    engine = EloEngine()
    engine.update("Panthers", "Dragons", 30, 0)

    pre_panther = engine.get_rating("Panthers")
    assert pre_panther > 1500.0

    engine.regress_to_mean(factor=1 / 3)
    post_panther = engine.get_rating("Panthers")

    # Should move closer to 1500
    assert abs(post_panther - 1500) < abs(pre_panther - 1500)


def test_save_load_roundtrip() -> None:
    engine = EloEngine()
    engine.update("Panthers", "Dragons", 24, 12)
    engine.update("Storm", "Eels", 30, 6)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "elo.json"
        engine.save(path)

        loaded = EloEngine()
        loaded.load(path)

        assert abs(loaded.get_rating("Panthers") - engine.get_rating("Panthers")) < 0.01
        assert abs(loaded.get_rating("Storm") - engine.get_rating("Storm")) < 0.01


def test_build_elo_from_history() -> None:
    results = [
        _make_result(round_number=1, home_team="Panthers", away_team="Dragons", home_score=24, away_score=12, winner="Panthers"),
        _make_result(round_number=2, game_id="g02", home_team="Storm", away_team="Eels", home_score=30, away_score=6, winner="Storm", kickoff_at="2026-03-13T09:00:00Z"),
        _make_result(round_number=3, game_id="g03", home_team="Dragons", away_team="Storm", home_score=18, away_score=14, winner="Dragons", kickoff_at="2026-03-20T09:00:00Z"),
    ]
    engine = build_elo_from_history(results)

    # Panthers won, so they should be above 1500
    assert engine.get_rating("Panthers") > 1500.0
    # Eels lost badly, should be well below 1500
    assert engine.get_rating("Eels") < 1500.0
    # All teams should have diverged from 1500
    ratings = engine.get_ratings()
    assert len(ratings) == 4
