from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from sport_assistant_agent.agent import route_dispatcher
from sport_assistant_agent.routing_agent import (
    DeterministicMessageAgent,
    WorkflowRouteDispatcher,
)
from polar_assistant.application.events import InMemoryEventBus
from polar_assistant.application.use_cases import CompareSessions
from polar_assistant.domain.entities import ExerciseSession


def _state(*, critical_safety_flag: bool = False) -> dict:
    return {
        "biometric_metrics": {
            "mean_hr_bpm": 120,
            "max_hr_bpm": 150,
            "cardiac_drift_pct": 1.0,
            "zone_seconds": {"zone_1": 600.0},
            "fatigue_signal": False,
            "data_quality": "HIGH",
            "critical_safety_flag": critical_safety_flag,
        },
        "session_comparison": {
            "reference_session_id": "reference",
            "candidate_session_id": "candidate",
            "reference_start_time": "2026-10-20T10:00:00",
            "candidate_start_time": "2026-10-21T10:00:00",
            "reference_sport": "RUNNING",
            "candidate_sport": "RUNNING",
            "duration_delta_seconds": 0.0,
            "duration_delta_percent": 0.0,
            "average_hr_delta_bpm": 0.0,
            "average_hr_delta_percent": 0.0,
            "maximum_hr_delta_bpm": 0.0,
            "zone_seconds_delta": {},
            "comparable_for_load_trend": True,
            "comparison_warnings": (),
            "data_quality": "HIGH",
        },
    }


def test_dispatcher_executes_only_the_safety_branch_without_llm():
    service = InMemorySessionService()
    session = service.create_session_sync(
        app_name="route_dispatcher_test",
        user_id="test_user",
        session_id="critical_safety_route",
        state=_state(critical_safety_flag=True),
    )
    runner = Runner(
        app_name="route_dispatcher_test",
        agent=route_dispatcher,
        session_service=service,
    )

    events = list(
        runner.run(
            user_id="test_user",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="evaluar")]),
        )
    )
    persisted = service.get_session_sync(
        app_name="route_dispatcher_test",
        user_id="test_user",
        session_id=session.id,
    )

    assert [event.author for event in events] == [
        "WorkflowRouteDispatcher",
        "SafetyEscalationResponse",
    ]
    assert persisted.state["workflow_decision"]["route"] == "SAFETY_ESCALATION"
    assert "proposed_adjustment" not in persisted.state


def _running_session(identifier: str, start_time: str, average_hr: float) -> ExerciseSession:
    """Build a controlled same-sport fixture with full, stable HR samples."""
    return ExerciseSession(
        exercise_id=identifier,
        start_time=start_time,
        device="synthetic-test-fixture",
        sport="RUNNING",
        duration_seconds=1800.0,
        heart_rate_average=average_hr,
        heart_rate_maximum=average_hr + 20,
        heart_rate_zones=({"index": 1, "in_zone": "PT30M"},),
        heart_rate_samples=tuple([average_hr] * 40),
    )


def test_same_sport_sessions_execute_comparable_route_without_calling_llm():
    reference = _running_session("run-reference", "2026-10-20T10:00:00", 120.0)
    candidate = _running_session("run-candidate", "2026-10-21T10:00:00", 124.0)
    comparison_result = CompareSessions(InMemoryEventBus()).execute(reference, candidate)
    assert comparison_result["comparison"]["comparable_for_load_trend"] is True
    assert comparison_result["candidate_metrics"]["fatigue_signal"] is False

    state = {
        "biometric_metrics": comparison_result["candidate_metrics"],
        "session_comparison": comparison_result["comparison"],
    }
    dispatcher = WorkflowRouteDispatcher(
        name="ComparableRouteDispatcher",
        sub_agents=[
            DeterministicMessageAgent(name="SafetyEscalationResponse", message="safety"),
            DeterministicMessageAgent(name="DataQualityReviewResponse", message="quality"),
            DeterministicMessageAgent(name="RecommendationAndApproval", message="recommendation stub"),
        ],
    )
    service = InMemorySessionService()
    session = service.create_session_sync(
        app_name="comparable_route_test",
        user_id="test_user",
        session_id="same_sport_route",
        state=state,
    )
    runner = Runner(
        app_name="comparable_route_test",
        agent=dispatcher,
        session_service=service,
    )

    events = list(
        runner.run(
            user_id="test_user",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="evaluar")]),
        )
    )
    persisted = service.get_session_sync(
        app_name="comparable_route_test",
        user_id="test_user",
        session_id=session.id,
    )

    assert [event.author for event in events] == [
        "ComparableRouteDispatcher",
        "RecommendationAndApproval",
    ]
    assert persisted.state["workflow_decision"] == {
        "route": "COMPARABLE_TREND_RECOMMENDATION",
        "llm_analysis_required": True,
        "plan_update_allowed": False,
        "reason": "validated_comparable_sessions_without_fatigue_signal",
    }
    assert "proposed_adjustment" not in persisted.state
