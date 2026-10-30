from scripts.polar_v3_inventory import minimize


def test_minimize_v3_exercise_keeps_zone_periods_and_excludes_samples():
    result = minimize({
        "id": "polar-1",
        "start_time": "2026-10-29T08:00:00",
        "sport": "RUNNING",
        "duration": "PT40M",
        "heart_rate": {"average": 141, "maximum": 164},
        "heart_rate_zones": [
            {"index": 2, "in_zone": "PT22M"},
            {"index": 3, "in_zone": "PT10M"},
        ],
        "samples": [{"data": "141,142"}],
    })

    assert result == {
        "day": "2026-10-29",
        "provider_session_id": "polar-1",
        "sport": "RUNNING",
        "duration_seconds": 2400.0,
        "heart_rate_average_bpm": 141,
        "heart_rate_maximum_bpm": 164,
        "heart_rate_zones": [
            {"index": 2, "duration_seconds": 1320.0},
            {"index": 3, "duration_seconds": 600.0},
        ],
    }
