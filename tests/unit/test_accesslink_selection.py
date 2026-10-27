import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from polar_assistant.infrastructure.polar import select_exercise


def test_selects_requested_exercise_id():
    items = [{"id": "old", "start_time": "2026-10-21T18:18:45"}, {"id": "new", "start_time": "2026-10-22T13:33:34"}]
    assert select_exercise(items, "old")["id"] == "old"


def test_selects_latest_exercise_when_id_is_omitted():
    items = [{"id": "old", "start_time": "2026-10-21T18:18:45"}, {"id": "new", "start_time": "2026-10-22T13:33:34"}]
    assert select_exercise(items)["id"] == "new"
