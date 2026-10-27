from __future__ import annotations

import os
from typing import Any

import requests


def fetch_accesslink_session(session_id: str) -> dict[str, Any]:
    """Consulta una sesión de Polar AccessLink usando un token OAuth2 existente.

    La URL es configurable porque AccessLink puede entregar una transacción que
    luego debe resolverse a un ejercicio concreto según el flujo de la cuenta.
    """
    token = os.getenv("POLAR_ACCESSLINK_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Falta POLAR_ACCESSLINK_ACCESS_TOKEN en el archivo .env.")
    template = os.getenv(
        "POLAR_ACCESSLINK_SESSION_URL",
        "https://www.polaraccesslink.com/v3/exercises/{session_id}",
    )
    url = template.format(session_id=session_id)
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=15,
    )
    if response.status_code == 401:
        raise RuntimeError("AccessLink rechazó el token OAuth2; debe renovarse o autorizarse de nuevo.")
    if response.status_code == 404:
        raise RuntimeError(f"AccessLink no encontró la sesión {session_id}.")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("AccessLink devolvió un payload JSON inesperado.")
    return payload
