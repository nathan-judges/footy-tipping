from scripts.lib.serialize import build_round_payload
from scripts.lib.types import TipResult


def test_build_round_payload_includes_nrl_mapping_and_margin_pick() -> None:
    tips = [
        TipResult(
            game_id="game-1",
            nrl_match_id=111,
            nrl_slug="alpha-vs-beta",
            home_team="Alpha",
            away_team="Beta",
            venue="A Park",
            kickoff_at="2026-04-24T09:50:00Z",
            status="upcoming",
            tip_team="Alpha",
            confidence=0.6,
            predicted_margin=4,
        ),
        TipResult(
            game_id="game-2",
            nrl_match_id=222,
            nrl_slug="gamma-vs-delta",
            home_team="Gamma",
            away_team="Delta",
            venue="B Park",
            kickoff_at="2026-04-25T09:50:00Z",
            status="upcoming",
            tip_team="Gamma",
            confidence=0.7,
            predicted_margin=12,
        ),
    ]
    payload = build_round_payload(tips=tips, round_number=8, season=2026, model_version="test-v1")
    assert payload["marginGameId"] == "game-2"
    assert payload["games"][0]["nrlMatchId"] == 111
    assert payload["games"][1]["nrlSlug"] == "gamma-vs-delta"


def test_build_round_payload_includes_result_fields_when_present() -> None:
    tips = [
        TipResult(
            game_id="game-1",
            nrl_match_id=None,
            nrl_slug=None,
            home_team="Alpha",
            away_team="Beta",
            venue="A Park",
            kickoff_at="2026-04-24T09:50:00Z",
            status="finished",
            tip_team="Alpha",
            confidence=0.6,
            predicted_margin=4,
            home_score=18,
            away_score=10,
            actual_winner="Alpha",
            actual_margin=8,
        )
    ]

    payload = build_round_payload(tips=tips, round_number=8, season=2026, model_version="test-v1")
    game = payload["games"][0]
    assert game["homeScore"] == 18
    assert game["awayScore"] == 10
    assert game["actualWinner"] == "Alpha"
    assert game["actualMargin"] == 8


def test_build_round_payload_omits_result_fields_when_none() -> None:
    tips = [
        TipResult(
            game_id="game-1",
            nrl_match_id=None,
            nrl_slug=None,
            home_team="Alpha",
            away_team="Beta",
            venue="A Park",
            kickoff_at="2026-04-24T09:50:00Z",
            status="finished",
            tip_team="Alpha",
            confidence=0.6,
            predicted_margin=4,
        )
    ]

    payload = build_round_payload(tips=tips, round_number=8, season=2026, model_version="test-v1")
    game = payload["games"][0]
    assert "homeScore" not in game
    assert "awayScore" not in game
    assert "actualWinner" not in game
    assert "actualMargin" not in game
