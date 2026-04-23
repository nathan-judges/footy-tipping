from scripts.lib.model import _calibrate_tip, predict_fixture
from scripts.lib.types import Fixture, OddsSnapshot


def test_calibrate_tip_prefers_market_when_low_confidence() -> None:
    fixture = Fixture(
        game_id="2026-r01-g01",
        nrl_match_id=12345,
        nrl_slug="broncos-vs-storm",
        home_team="Broncos",
        away_team="Storm",
        venue="Suncorp",
        kickoff_at="2026-04-24T09:50:00Z",
        status="upcoming",
    )
    calibrated = _calibrate_tip(
        fixture=fixture,
        base_tip="Broncos",
        base_confidence=0.55,
        odds=OddsSnapshot(home=2.1, away=1.8),
    )
    assert calibrated == "Storm"


def test_predict_fixture_keeps_nrl_mapping_fields() -> None:
    fixture = Fixture(
        game_id="2026-r01-g01",
        nrl_match_id=9876,
        nrl_slug="broncos-vs-storm",
        home_team="Broncos",
        away_team="Storm",
        venue="Suncorp",
        kickoff_at="2026-04-24T09:50:00Z",
        status="finished",
    )
    result = predict_fixture(fixture)
    assert result.nrl_match_id == 9876
    assert result.nrl_slug == "broncos-vs-storm"
    assert result.tip_team == "N/A"
