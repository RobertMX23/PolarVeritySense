"""Minimal HTTP boundary for Polar AccessLink Dynamic API v4."""

from __future__ import annotations

from datetime import date
from typing import Any

import requests


class PolarDynamicApiError(RuntimeError):
    """A sanitized error for a Dynamic API request."""


class PolarDynamicApiClient:
    """Lists training sessions without logging OAuth credentials or payloads."""

    base_url = "https://www.polaraccesslink.com/v4/data"

    def __init__(self, access_token: str, *, timeout_seconds: int = 30) -> None:
        if not access_token:
            raise ValueError("Se requiere un token Polar para consultar Dynamic API.")
        self._access_token = access_token
        self._timeout_seconds = timeout_seconds

    def list_training_sessions(
        self,
        *,
        from_date: date,
        to_date: date,
        include_zones: bool = False,
    ) -> list[dict[str, Any]]:
        params: list[tuple[str, str]] = [
            ("from", from_date.isoformat()),
            ("to", to_date.isoformat()),
        ]
        if include_zones:
            params.append(("features", "zones"))
        response = requests.get(
            f"{self.base_url}/training-sessions/list",
            params=params,
            headers={"Accept": "application/json", "Authorization": f"Bearer {self._access_token}"},
            timeout=self._timeout_seconds,
        )
        if response.status_code in {401, 403}:
            raise PolarDynamicApiError("Polar rechazó la autorización o el consentimiento requerido.")
        if response.status_code == 429:
            raise PolarDynamicApiError("Polar limitó temporalmente la consulta; reintenta más tarde.")
        try:
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as error:
            raise PolarDynamicApiError("No fue posible consultar sesiones en Polar Dynamic API.") from error
        except ValueError as error:
            raise PolarDynamicApiError("Polar devolvió una respuesta no JSON.") from error
        sessions = payload.get("trainingSessions") if isinstance(payload, dict) else None
        if not isinstance(sessions, list) or not all(isinstance(item, dict) for item in sessions):
            raise PolarDynamicApiError("Polar devolvió un formato de sesiones inesperado.")
        return sessions
