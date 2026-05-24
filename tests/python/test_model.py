"""Tests for the ensemble prediction model."""

from scripts.lib.model import run_model
from scripts.lib.types import Fixture


def _make_fixture(**overrides) -> Fixture:
    defaults = dict(
        game_id="2026-r01-g01",
        nrl_match_id=12345,
        nrl_slug="broncos-vs-storm",
        home_team="Broncos",
        away_team="Storm",
        venue="Suncorp Stadium",
        kickoff_at="2026-04-24T09:50:00Z",
        status="upcoming",
    )
    defaults.update(overrides)
    return Fixture(**defaults)


def test_run_model_returns_tip_results() -> None:
    fixtures = [_make_fixture(), _make_fixture(game_id="2026-r01-g02", home_team="Panthers", away_team="Eels")]
    results = run_model(fixtures)
    assert len(results) == 2
    for r in results:
        assert r.game_id is not None
        assert r.tip_team is not None


def test_finished_fixture_returns_na_tip() -> None:
    fixture = _make_fixture(status="finished", home_score=24, away_score=12, actual_winner="Broncos", actual_margin=12)
    results = run_model([fixture])
    assert len(results) == 1
    assert results[0].tip_team == "N/A"
    assert results[0].confidence == 0.0


def test_predict_fixture_keeps_nrl_mapping_fields() -> None:
    fixture = _make_fixture(
        nrl_match_id=9876,
        nrl_slug="broncos-vs-storm",
        status="finished",
    )
    results = run_model([fixture])
    result = results[0]
    assert result.nrl_match_id == 9876
    assert result.nrl_slug == "broncos-vs-storm"
    assert result.tip_team == "N/A"


def test_ensemble_confidence_between_0_and_1() -> None:
    fixtures = [
        _make_fixture(home_team="Panthers", away_team="Dragons"),
        _make_fixture(game_id="g2", home_team="Storm", away_team="Eels"),
        _make_fixture(game_id="g3", home_team="Warriors", away_team="Titans"),
    ]
    results = run_model(fixtures)
    for r in results:
        assert 0.0 <= r.confidence <= 1.0, f"Confidence {r.confidence} out of range for {r.game_id}"


def test_upcoming_fixture_has_real_tip() -> None:
    fixture = _make_fixture(home_team="Panthers", away_team="Dragons")
    results = run_model([fixture])
    result = results[0]
    assert result.tip_team in ("Panthers", "Dragons")
    assert result.confidence > 0.0
    assert result.predicted_margin >= 0
