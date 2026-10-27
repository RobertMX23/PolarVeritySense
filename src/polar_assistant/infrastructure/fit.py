from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fitparse import FitFile

from polar_assistant.domain.entities import ExerciseSession


def load_fit_session(
    fit_path: Path,
    *,
    exercise_id: str,
    sport: str,
    zone_limits: Iterable[tuple[int, int, int]],
) -> ExerciseSession:
    """Load a local FIT file into the domain model without external calls."""
    records = []
    for message in FitFile(str(fit_path)).get_messages("record"):
        values = {field.name: field.value for field in message if field.value is not None}
        if isinstance(values.get("heart_rate"), (int, float)):
            records.append(float(values["heart_rate"]))
    session_values = {}
    for message in FitFile(str(fit_path)).get_messages("session"):
        session_values = {field.name: field.value for field in message if field.value is not None}
        break
    start_time = str(session_values.get("start_time") or "")
    duration = float(session_values.get("total_elapsed_time") or len(records))
    zones = []
    for index, lower, upper in zone_limits:
        seconds = sum(1 for hr in records if lower <= hr < upper)
        zones.append({"index": index, "lower_limit": lower, "upper_limit": upper,
                      "in_zone": f"PT{seconds}S"})
    return ExerciseSession(
        exercise_id=exercise_id,
        start_time=start_time,
        device="Polar Flow app",
        sport=sport,
        duration_seconds=duration,
        heart_rate_average=round(sum(records) / len(records), 2) if records else None,
        heart_rate_maximum=max(records) if records else None,
        heart_rate_zones=tuple(zones),
        heart_rate_samples=tuple(records),
    )
