from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sport_assistant_agent.agent import full_workflow_agent, root_agent
from sport_assistant_agent.clean_adk_tools import analyze_exercise_tool


def test_root_agent_uses_clean_analysis_adapter():
    assert root_agent.name == "SportAssistantRoot"
    assert analyze_exercise_tool.__name__ == "analyze_exercise_tool"


def test_full_workflow_contains_deterministic_route_dispatcher():
    dispatcher = full_workflow_agent.find_agent("WorkflowRouteDispatcher")
    assert dispatcher is not None
    assert full_workflow_agent.find_agent("SafetyEscalationResponse") is not None
    assert full_workflow_agent.find_agent("DataQualityReviewResponse") is not None


def test_demo_fit_files_can_be_mounted_outside_the_application(monkeypatch, tmp_path):
    from sport_assistant_agent import clean_adk_tools

    paths = []
    monkeypatch.setenv("POLAR_FIT_DIR", str(tmp_path))

    def load_mounted(path, **kwargs):
        paths.append(path)
        return kwargs["exercise_id"]

    monkeypatch.setattr(clean_adk_tools, "load_fit_session", load_mounted)
    reference, candidate = clean_adk_tools._load_demo_sessions()
    assert paths == [tmp_path / f"{reference}.fit", tmp_path / f"{candidate}.fit"]
    assert (reference, candidate) == (
        clean_adk_tools.DEMO_REFERENCE_EXERCISE_ID,
        clean_adk_tools.DEMO_CANDIDATE_EXERCISE_ID,
    )
