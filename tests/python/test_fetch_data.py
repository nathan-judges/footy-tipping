from scripts.lib.fetch_data import parse_draw_fixtures


def test_parse_draw_fixtures_maps_finished_scores_and_slug() -> None:
    payload = {
        "fixtures": [
            {
                "type": "Match",
                "matchMode": "Post",
                "matchState": "FullTime",
                "venue": "Test Stadium",
                "matchCentreUrl": "/draw/nrl-premiership/2026/round-8/alpha-v-beta/",
                "clock": {"kickOffTimeLong": "2026-04-24T09:50:00Z"},
                "homeTeam": {"nickName": "Alpha", "score": 24},
                "awayTeam": {"nickName": "Beta", "score": 12},
            }
        ]
    }

    fixtures = parse_draw_fixtures(payload=payload, season=2026, round_number=8)

    assert len(fixtures) == 1
    fixture = fixtures[0]
    assert fixture.game_id == "2026-r08-g01"
    assert fixture.nrl_slug == "alpha-v-beta"
    assert fixture.status == "finished"
    assert fixture.home_score == 24
    assert fixture.away_score == 12
    assert fixture.actual_winner == "Alpha"
    assert fixture.actual_margin == 12


def test_parse_draw_fixtures_maps_upcoming_without_scores() -> None:
    payload = {
        "fixtures": [
            {
                "type": "Match",
                "matchMode": "Pre",
                "matchState": "Upcoming",
                "venue": "Test Stadium",
                "matchCentreUrl": "/draw/nrl-premiership/2026/round-8/alpha-v-beta/",
                "clock": {"kickOffTimeLong": "2026-04-24T09:50:00Z"},
                "homeTeam": {"nickName": "Alpha"},
                "awayTeam": {"nickName": "Beta"},
            }
        ]
    }

    fixtures = parse_draw_fixtures(payload=payload, season=2026, round_number=8)

    assert len(fixtures) == 1
    fixture = fixtures[0]
    assert fixture.status == "upcoming"
    assert fixture.home_score is None
    assert fixture.away_score is None
