from __future__ import annotations

from .entities import BiometricMetrics, ExerciseSession, SessionComparison


def _percent_delta(reference: float | None, candidate: float | None) -> float | None:
    if reference in (None, 0) or candidate is None:
        return None
    return round((candidate - reference) / reference * 100, 2)


def compare_sessions(
    reference: ExerciseSession,
    candidate: ExerciseSession,
    reference_metrics: BiometricMetrics,
    candidate_metrics: BiometricMetrics,
) -> SessionComparison:
    """Compare two validated sessions without inferring medical causality."""
    warnings: list[str] = []
    same_sport = bool(reference.sport and candidate.sport and reference.sport == candidate.sport)
    if not same_sport:
        warnings.append("Las modalidades son distintas; la comparación no prueba equivalencia de carga fisiológica.")
    if reference_metrics.data_quality != "HIGH" or candidate_metrics.data_quality != "HIGH":
        warnings.append("Al menos una sesión no tiene muestras completas de frecuencia cardíaca.")

    zones = set(reference_metrics.zone_seconds) | set(candidate_metrics.zone_seconds)
    zone_delta = {
        zone: round(candidate_metrics.zone_seconds.get(zone, 0.0) - reference_metrics.zone_seconds.get(zone, 0.0), 2)
        for zone in sorted(zones)
    }
    duration_delta = None
    if reference.duration_seconds is not None and candidate.duration_seconds is not None:
        duration_delta = round(candidate.duration_seconds - reference.duration_seconds, 2)

    return SessionComparison(
        reference_session_id=reference.exercise_id,
        candidate_session_id=candidate.exercise_id,
        reference_start_time=reference.start_time,
        candidate_start_time=candidate.start_time,
        reference_sport=reference.sport,
        candidate_sport=candidate.sport,
        duration_delta_seconds=duration_delta,
        duration_delta_percent=_percent_delta(reference.duration_seconds, candidate.duration_seconds),
        average_hr_delta_bpm=(
            round(candidate.heart_rate_average - reference.heart_rate_average, 2)
            if candidate.heart_rate_average is not None and reference.heart_rate_average is not None
            else None
        ),
        average_hr_delta_percent=_percent_delta(reference.heart_rate_average, candidate.heart_rate_average),
        maximum_hr_delta_bpm=(
            round(candidate.heart_rate_maximum - reference.heart_rate_maximum, 2)
            if candidate.heart_rate_maximum is not None and reference.heart_rate_maximum is not None
            else None
        ),
        zone_seconds_delta=zone_delta,
        comparable_for_load_trend=same_sport and not warnings,
        comparison_warnings=tuple(warnings),
        data_quality="HIGH" if reference_metrics.data_quality == candidate_metrics.data_quality == "HIGH" else "LIMITED",
    )
