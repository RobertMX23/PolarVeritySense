from datetime import date

from polar_assistant.infrastructure.polar_dynamic import PolarDynamicApiClient


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"trainingSessions": [{"identifier": {"id": "one"}}]}


def test_lists_dynamic_sessions_with_requested_zone_feature(monkeypatch):
    captured = {}

    def fake_get(url, *, params, headers, timeout):
        captured.update(url=url, params=params, headers=headers, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr("polar_assistant.infrastructure.polar_dynamic.requests.get", fake_get)
    result = PolarDynamicApiClient("token-value").list_training_sessions(
        from_date=date(2026, 10, 28),
        to_date=date(2026, 10, 29),
        include_zones=True,
    )

    assert result == [{"identifier": {"id": "one"}}]
    assert captured["url"].endswith("/v4/data/training-sessions/list")
    assert captured["params"] == [("from", "2026-10-28"), ("to", "2026-10-29"), ("features", "zones")]
    assert captured["headers"]["Authorization"] == "Bearer token-value"
