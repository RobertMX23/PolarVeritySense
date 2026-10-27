import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from polar_assistant.application.events import InMemoryEventBus
from polar_assistant.application.use_cases import AnalyzeExercise
from polar_assistant.domain.entities import ExerciseSession


class FakeRepository:
    def get_exercise(self, exercise_id=None):
        return ExerciseSession("x", "2026-05-19T08:42:46", "Polar Verity Sense", "OTHER", 5532, 112, 158, ({"index": 0, "in_zone": "PT34M10S"},), tuple([100.0] * 20 + [120.0] * 20))


def test_analyze_exercise_is_independent_from_adk_and_http():
    bus = InMemoryEventBus()
    result = AnalyzeExercise(FakeRepository(), bus).execute("x")
    assert result["metrics"]["cardiac_drift_pct"] == 20.0
    assert [event.event_type for event in bus.events] == ["ExerciseFetched", "MetricsCalculated", "RiskSignalDetected"]

