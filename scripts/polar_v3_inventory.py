"""Read-only, minimized inventory of sessions available to the existing v3 client."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from polar_assistant.infrastructure.polar import duration_seconds

URL = "https://www.polaraccesslink.com/v3/exercises"


def minimized_zones(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": value.get("index"),
            "duration_seconds": duration_seconds(value.get("in_zone")),
        }
        for value in values
    ]


def minimize(exercise: dict[str, Any]) -> dict[str, Any]:
    heart_rate = exercise.get("heart_rate") or {}
    return {
        "day": str(exercise.get("start_time") or "")[:10],
        "provider_session_id": exercise.get("id"),
        "sport": exercise.get("detailed_sport_info") or exercise.get("sport"),
        "duration_seconds": duration_seconds(exercise.get("duration")),
        "heart_rate_average_bpm": heart_rate.get("average"),
        "heart_rate_maximum_bpm": heart_rate.get("maximum"),
        "heart_rate_zones": minimized_zones(exercise.get("heart_rate_zones") or []),
    }


def fetch_exercises(token: str) -> list[dict[str, Any]]:
    response = requests.get(
        URL,
        params={"samples": "false", "zones": "true"},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )
    if response.status_code in {401, 403}:
        raise PermissionError(response.status_code)
    response.raise_for_status()
    payload = response.json() or []
    if not isinstance(payload, list):
        raise RuntimeError("AccessLink v3 devolvió una lista de ejercicios inválida.")
    return [item for item in payload if isinstance(item, dict)]


def main() -> int:
    token = str(dotenv_values(ROOT / ".env").get("POLAR_ACCESSLINK_ACCESS_TOKEN") or "")
    if not token:
        print("Falta POLAR_ACCESSLINK_ACCESS_TOKEN en .env; no se hizo ninguna llamada.")
        return 2
    try:
        exercises = fetch_exercises(token)
    except PermissionError as error:
        print(json.dumps({"status": "AUTHORIZATION_REJECTED", "http_status": error.args[0]}))
        return 3
    sessions = [minimize(item) for item in exercises]
    print(json.dumps({
        "status": "OK",
        "source": "polar_accesslink_v3",
        "available_days": sorted({item["day"] for item in sessions if item["day"]}),
        "sessions": sessions,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
