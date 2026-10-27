import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from polar_assistant.domain.entities import BiometricMetrics, SessionComparison
from polar_assistant.domain.routing import WorkflowRoute, select_workflow_route


def _metrics(*, quality: str = "HIGH", fatigue: bool = False) -> BiometricMetrics:
    return BiometricMetrics(
        mean_hr_bpm=120,
        max_hr_bpm=150,
        cardiac_drift_pct=8.0 if fatigue else 1.0,
        zone_seconds={"zone_1": 600.0},
        fatigue_signal=fatigue,
        data_quality=quality,
    )


def _comparison(*, comparable: bool = True) -> SessionComparison:
    return SessionComparison(
        reference_session_id="reference",
        candidate_session_id="candidate",
        reference_start_time="2026-10-20T10:00:00",
        candidate_start_time="2026-10-21T10:00:00",
        reference_sport="RUNNING",
        candidate_sport="RUNNING" if comparable else "HIIT",
        duration_delta_seconds=60.0,
        duration_delta_percent=10.0,
        average_hr_delta_bpm=4.0,
        average_hr_delta_percent=3.45,
        maximum_hr_delta_bpm=3.0,
        zone_seconds_delta={"zone_1": 60.0},
        comparable_for_load_trend=comparable,
        comparison_warnings=() if comparable else ("modalidades distintas",),
        data_quality="HIGH",
    )


def test_critical_flag_has_priority_over_all_other_routes():
    decision = select_workflow_route(_metrics(fatigue=True), _comparison(comparable=False), critical_safety_flag=True)
    assert decision.route is WorkflowRoute.SAFETY_ESCALATION
    assert decision.llm_analysis_required is False
    assert decision.plan_update_allowed is False


def test_summary_only_data_routes_to_data_quality_review():
    decision = select_workflow_route(_metrics(quality="SUMMARY_ONLY"), _comparison())
    assert decision.route is WorkflowRoute.DATA_QUALITY_REVIEW
    assert decision.llm_analysis_required is False


def test_fatigue_route_has_priority_over_comparison_context():
    decision = select_workflow_route(_metrics(fatigue=True), _comparison(comparable=False))
    assert decision.route is WorkflowRoute.RECOVERY_RECOMMENDATION
    assert decision.reason == "cardiac_drift_above_threshold"


def test_distinct_modalities_route_to_context_limited_analysis():
    decision = select_workflow_route(_metrics(), _comparison(comparable=False))
    assert decision.route is WorkflowRoute.CONTEXT_LIMITED_RECOMMENDATION
    assert decision.llm_analysis_required is True


def test_comparable_clean_sessions_route_to_trend_analysis():
    decision = select_workflow_route(_metrics(), _comparison())
    assert decision.route is WorkflowRoute.COMPARABLE_TREND_RECOMMENDATION
    assert decision.llm_analysis_required is True
    assert decision.plan_update_allowed is False
