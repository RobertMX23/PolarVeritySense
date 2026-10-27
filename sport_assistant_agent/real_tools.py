from __future__ import annotations

import re
from typing import Any

import requests
from google.adk.tools import ToolContext

from .config import ACCESSLINK_EXERCISES_URL
from .models import AccessLinkExerciseSummary


def _duration_seconds(value: Any) -> float | None:
    if not value:
        return None
    total = 0.0
    for number, unit in re.findall(r"([0-9.]+)([HMS])", str(value)):
        total += float(number) * {"H": 3600, "M": 60, "S": 1}[unit]
    return total or None


def fetch_real_exercise_tool(tool_context: ToolContext, exercise_id: str | None = None) -> dict[str, Any]:
    """Obtiene ejercicios reales y guarda la sesión seleccionada en el estado ADK."""
    import os

    token = os.getenv("POLAR_ACCESSLINK_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Falta POLAR_ACCESSLINK_ACCESS_TOKEN en .env.")
    response = requests.get(
        ACCESSLINK_EXERCISES_URL,
        params={"samples": "true", "zones": "true"},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    exercises = response.json() or []
    selected = next((item for item in exercises if not exercise_id or item.get("id") == exercise_id), None)
    if selected is None:
        raise ValueError("No se encontró la sesión solicitada en AccessLink.")
    samples = selected.get("samples") or []
    summary = AccessLinkExerciseSummary(
        exercise_id=str(selected.get("id")),
        start_time=str(selected.get("start_time")),
        upload_time=selected.get("upload_time"),
        device=selected.get("device"),
        sport=selected.get("sport"),
        duration_seconds=_duration_seconds(selected.get("duration")),
        heart_rate_average=(selected.get("heart_rate") or {}).get("average"),
        heart_rate_maximum=(selected.get("heart_rate") or {}).get("maximum"),
        heart_rate_zones=selected.get("heart_rate_zones") or [],
        sample_count=sum(len(str(s.get("data", "")).split(",")) for s in samples if str(s.get("sample_type", s.get("sample-type"))) == "0"),
    ).model_dump(mode="json")
    tool_context.state["raw_polar_accesslink_exercise"] = selected
    tool_context.state["accesslink_exercise_summary"] = summary
    return summary

