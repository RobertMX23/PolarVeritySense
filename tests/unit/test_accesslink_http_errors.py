import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from polar_assistant.infrastructure import polar
from polar_assistant.infrastructure.polar import (
    AccessLinkAuthenticationError,
    AccessLinkExerciseNotFoundError,
    AccessLinkExerciseRepository,
    AccessLinkNoExercisesError,
)


class FakeResponse:
    def __init__(self, status_code: int, payload=None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_expired_token_returns_actionable_authentication_error(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return FakeResponse(401)

    monkeypatch.setattr(polar.requests, "get", fake_get)
    repository = AccessLinkExerciseRepository("expired-test-token")

    with pytest.raises(AccessLinkAuthenticationError, match="vuelve a autorizar"):
        repository.get_exercise()

    assert captured["headers"]["Authorization"] == "Bearer expired-test-token"
    assert captured["params"] == {"samples": "true", "zones": "true"}


def test_http_404_identifies_the_requested_exercise(monkeypatch):
    monkeypatch.setattr(polar.requests, "get", lambda *args, **kwargs: FakeResponse(404))
    repository = AccessLinkExerciseRepository("test-token")

    with pytest.raises(AccessLinkExerciseNotFoundError, match="missing-session"):
        repository.get_exercise("missing-session")


def test_empty_exercise_list_stops_without_selecting_a_session(monkeypatch):
    monkeypatch.setattr(polar.requests, "get", lambda *args, **kwargs: FakeResponse(200, []))
    repository = AccessLinkExerciseRepository("test-token")

    with pytest.raises(AccessLinkNoExercisesError, match="no devolvió ejercicios"):
        repository.get_exercise()


def test_requested_id_absent_from_successful_list_is_not_found(monkeypatch):
    payload = [{"id": "available-session", "start_time": "2026-10-22T10:00:00"}]
    monkeypatch.setattr(polar.requests, "get", lambda *args, **kwargs: FakeResponse(200, payload))
    repository = AccessLinkExerciseRepository("test-token")

    with pytest.raises(AccessLinkExerciseNotFoundError, match="missing-session"):
        repository.get_exercise("missing-session")
