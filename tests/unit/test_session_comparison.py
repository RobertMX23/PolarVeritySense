import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from polar_assistant.domain.comparison import compare_sessions
from polar_assistant.domain.entities import ExerciseSession
from polar_assistant.domain.metrics import calculate_metrics


def _session(identifier: str, sport: str, duration: float, average: float, maximum: float) -> ExerciseSession:
    return ExerciseSession(
        identifier,
        "2026-10-22T10:00:00",
        "device",
        sport,
        duration,
        average,
        maximum,
        ({"index": 0, "in_zone": "PT10S"},),
        tuple([average] * 20),
    )


def test_comparison_marks_distinct_modalities_as_limited():
    reference = _session("hiit", "HIIT", 100, 80, 110)
    candidate = _session("run", "TREADMILL_RUNNING", 200, 100, 140)
    result = compare_sessions(reference, candidate, calculate_metrics(reference), calculate_metrics(candidate))
    assert result.duration_delta_seconds == 100
    assert result.average_hr_delta_bpm == 20
    assert result.average_hr_delta_percent == 25.0
    assert result.comparable_for_load_trend is False
    assert result.comparison_warnings


def test_comparison_handles_missing_reference_values_without_division_error():
    reference = _session("a", "RUNNING", 0, 0, 110)
    candidate = _session("b", "RUNNING", 10, 100, 140)
    result = compare_sessions(reference, candidate, calculate_metrics(reference), calculate_metrics(candidate))
    assert result.duration_delta_percent is None
    assert result.average_hr_delta_percent is None
    assert result.comparable_for_load_trend is False
