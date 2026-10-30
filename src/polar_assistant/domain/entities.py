from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExerciseSession:
    exercise_id: str
    start_time: str
    device: str | None
    sport: str | None
    duration_seconds: float | None
    heart_rate_average: float | None
    heart_rate_maximum: float | None
    heart_rate_zones: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    heart_rate_samples: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BiometricMetrics:
    mean_hr_bpm: float | None
    max_hr_bpm: float | None
    cardiac_drift_pct: float | None
    zone_seconds: dict[str, float]
    fatigue_signal: bool
    data_quality: str


@dataclass(frozen=True)
class SessionComparison:
    reference_session_id: str
    candidate_session_id: str
    reference_start_time: str
    candidate_start_time: str
    reference_sport: str | None
    candidate_sport: str | None
    duration_delta_seconds: float | None
    duration_delta_percent: float | None
    average_hr_delta_bpm: float | None
    average_hr_delta_percent: float | None
    maximum_hr_delta_bpm: float | None
    zone_seconds_delta: dict[str, float]
    comparable_for_load_trend: bool
    comparison_warnings: tuple[str, ...]
    data_quality: str
