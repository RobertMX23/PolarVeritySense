from __future__ import annotations

from .entities import BiometricMetrics, ExerciseSession


def _zone_seconds(zones: tuple[dict, ...]) -> dict[str, float]:
    result: dict[str, float] = {}
    for zone in zones:
        index = zone.get("index")
        duration = zone.get("in_zone", zone.get("in-zone"))
        seconds = 0.0
        if isinstance(duration, str) and duration.startswith("PT"):
            value = duration[2:]
            minutes = 0.0
            if "H" in value:
                hours, value = value.split("H", 1); minutes += float(hours) * 60
            if "M" in value:
                mins, value = value.split("M", 1); minutes += float(mins)
            if "S" in value: seconds = minutes * 60 + float(value[:-1])
            else: seconds = minutes * 60
        result[f"zone_{index}"] = round(seconds, 2)
    return result


def calculate_metrics(session: ExerciseSession) -> BiometricMetrics:
    samples = [float(x) for x in session.heart_rate_samples if 30 <= float(x) <= 240]
    first = samples[: len(samples) // 2]
    second = samples[len(samples) // 2 :]
    drift = None
    if len(first) >= 10 and len(second) >= 10:
        first_avg = sum(first) / len(first)
        second_avg = sum(second) / len(second)
        if first_avg:
            drift = round((second_avg - first_avg) / first_avg * 100, 2)
    quality = "HIGH" if samples else "SUMMARY_ONLY"
    return BiometricMetrics(
        mean_hr_bpm=session.heart_rate_average,
        max_hr_bpm=session.heart_rate_maximum,
        cardiac_drift_pct=drift,
        zone_seconds=_zone_seconds(session.heart_rate_zones),
        fatigue_signal=bool(drift is not None and drift > 5),
        data_quality=quality,
    )

