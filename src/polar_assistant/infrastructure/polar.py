from __future__ import annotations

import re
from typing import Any

import requests

from polar_assistant.domain.entities import ExerciseSession


class AccessLinkError(RuntimeError):
    """Base error for failures at the Polar AccessLink boundary."""


class AccessLinkAuthenticationError(AccessLinkError):
    """The OAuth token is absent, expired, revoked, or otherwise rejected."""


class AccessLinkExerciseNotFoundError(AccessLinkError):
    """The requested exercise is not available to the AccessLink client."""


class AccessLinkNoExercisesError(AccessLinkError):
    """AccessLink returned a valid response with no available exercises."""


def duration_seconds(value: Any) -> float | None:
    if not value:
        return None
    total = 0.0
    for number, unit in re.findall(r"([0-9.]+)([HMS])", str(value)):
        total += float(number) * {"H": 3600, "M": 60, "S": 1}[unit]
    return total or None


class AccessLinkExerciseRepository:
    def __init__(self, token: str, base_url: str = "https://www.polaraccesslink.com/v3/exercises") -> None:
        self.token = token
        self.base_url = base_url

    def get_exercise(self, exercise_id: str | None = None) -> ExerciseSession:
        response = requests.get(self.base_url, params={"samples": "true", "zones": "true"}, headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"}, timeout=30)
        if response.status_code == 401:
            raise AccessLinkAuthenticationError(
                "AccessLink rechazó el token OAuth2; vuelve a autorizar la aplicación."
            )
        if response.status_code == 404:
            requested = exercise_id or "más reciente"
            raise AccessLinkExerciseNotFoundError(
                f"AccessLink no encontró el ejercicio solicitado: {requested}."
            )
        response.raise_for_status()
        items = response.json() or []
        if not isinstance(items, list):
            raise AccessLinkError("AccessLink devolvió un formato inesperado para la lista de ejercicios.")
        if not items:
            raise AccessLinkNoExercisesError(
                "AccessLink no devolvió ejercicios disponibles para este cliente y usuario."
            )
        item = select_exercise(items, exercise_id)
        if item is None:
            raise AccessLinkExerciseNotFoundError(
                f"El ejercicio {exercise_id} no está disponible en la lista de AccessLink."
            )
        samples = []
        for sample in item.get("samples") or []:
            sample_type = str(sample.get("sample_type", sample.get("sample-type")))
            if sample_type == "0":
                samples.extend(float(x) for x in str(sample.get("data", "")).split(",") if x.strip().replace(".", "", 1).isdigit())
        hr = item.get("heart_rate") or {}
        return ExerciseSession(str(item.get("id")), str(item.get("start_time")), item.get("device"), item.get("sport"), duration_seconds(item.get("duration")), hr.get("average"), hr.get("maximum"), tuple(item.get("heart_rate_zones") or []), tuple(samples))


def select_exercise(items: list[dict[str, Any]], exercise_id: str | None = None) -> dict[str, Any] | None:
    """Return an explicit ID, or the latest session when no ID was requested."""
    if exercise_id:
        return next((item for item in items if item.get("id") == exercise_id), None)
    return max(items, key=lambda item: str(item.get("start_time") or ""), default=None)
