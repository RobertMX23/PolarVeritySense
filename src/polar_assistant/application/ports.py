from __future__ import annotations

from typing import Protocol

from polar_assistant.domain.entities import ExerciseSession


class ExerciseRepository(Protocol):
    def get_exercise(self, exercise_id: str | None = None) -> ExerciseSession: ...


class EventBus(Protocol):
    def publish(self, event: object) -> None: ...

