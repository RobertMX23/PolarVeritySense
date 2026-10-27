from __future__ import annotations

from dataclasses import asdict

from polar_assistant.domain.comparison import compare_sessions
from polar_assistant.domain.entities import ExerciseSession
from polar_assistant.domain.metrics import calculate_metrics

from .events import DomainEvent
from .ports import EventBus, ExerciseRepository


class AnalyzeExercise:
    def __init__(self, repository: ExerciseRepository, event_bus: EventBus) -> None:
        self.repository = repository
        self.event_bus = event_bus

    def execute(self, exercise_id: str | None = None) -> dict:
        session = self.repository.get_exercise(exercise_id)
        self.event_bus.publish(DomainEvent("ExerciseFetched", session.exercise_id, {"start_time": session.start_time}))
        metrics = calculate_metrics(session)
        payload = asdict(metrics)
        self.event_bus.publish(DomainEvent("MetricsCalculated", session.exercise_id, payload))
        if metrics.fatigue_signal:
            self.event_bus.publish(DomainEvent("RiskSignalDetected", session.exercise_id, {"reason": "cardiac_drift_above_threshold"}))
        return {"session": asdict(session), "metrics": payload}


class CompareSessions:
    """Application use case for deterministic, context-limited session comparison."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def execute(self, reference: ExerciseSession, candidate: ExerciseSession) -> dict:
        reference_metrics = calculate_metrics(reference)
        candidate_metrics = calculate_metrics(candidate)
        comparison = asdict(compare_sessions(reference, candidate, reference_metrics, candidate_metrics))
        self.event_bus.publish(
            DomainEvent("SessionsCompared", candidate.exercise_id, comparison)
        )
        if comparison["comparison_warnings"]:
            self.event_bus.publish(
                DomainEvent(
                    "ComparisonLimitedByContext",
                    candidate.exercise_id,
                    {"warnings": comparison["comparison_warnings"]},
                )
            )
        return {
            "reference_session": asdict(reference),
            "candidate_session": asdict(candidate),
            "reference_metrics": asdict(reference_metrics),
            "candidate_metrics": asdict(candidate_metrics),
            "comparison": comparison,
        }
