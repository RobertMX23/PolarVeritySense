"""ADK adapters: telemetry preparation runs Python, never an LLM."""

import asyncio
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
from typing import Literal

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions

from .clean_adk_tools import (
    _load_demo_sessions, _session_summary, analyze_exercise_tool,
    select_workflow_decision_from_state,
)
from polar_assistant.domain.comparison import compare_sessions
from polar_assistant.domain.entities import BiometricMetrics, ExerciseSession
from polar_assistant.domain.metrics import calculate_metrics


def _synthetic_cloud_demo_sessions() -> tuple[ExerciseSession, ExerciseSession]:
    """Return non-personal evidence when Cloud Run has no approved FIT mount."""
    reference = ExerciseSession(
        exercise_id="synthetic-reference-hiit",
        start_time="2026-01-01T08:00:00Z",
        device="Polar Verity Sense (synthetic demo)",
        sport="HIIT",
        duration_seconds=1_800,
        heart_rate_average=144,
        heart_rate_maximum=171,
        heart_rate_zones=(
            {"index": 2, "in_zone": "PT12M"},
            {"index": 3, "in_zone": "PT14M"},
            {"index": 4, "in_zone": "PT4M"},
        ),
        heart_rate_samples=tuple([132] * 20 + [145] * 20 + [151] * 20),
    )
    candidate = ExerciseSession(
        exercise_id="synthetic-candidate-treadmill",
        start_time="2026-01-02T08:00:00Z",
        device="Polar Verity Sense (synthetic demo)",
        sport="TREADMILL_RUNNING",
        duration_seconds=2_400,
        heart_rate_average=141,
        heart_rate_maximum=164,
        heart_rate_zones=(
            {"index": 1, "in_zone": "PT8M"},
            {"index": 2, "in_zone": "PT22M"},
            {"index": 3, "in_zone": "PT10M"},
        ),
        heart_rate_samples=tuple([135] * 20 + [141] * 20 + [147] * 20),
    )
    return reference, candidate


def _load_demo_sessions_for_runtime() -> tuple[ExerciseSession, ExerciseSession, str]:
    """Prefer approved local FIT evidence; keep Cloud Run usable without it."""
    try:
        reference, candidate = _load_demo_sessions()
        return reference, candidate, "local_real_fit"
    except FileNotFoundError:
        reference, candidate = _synthetic_cloud_demo_sessions()
        return reference, candidate, "synthetic_cloud_demo"


def prepare_ingestion(state: dict, source: str) -> dict:
    work = SimpleNamespace(state={})
    if source == "accesslink":
        analyze_exercise_tool(state.get("requested_exercise_id"), work)
    else:
        _, candidate, demo_source = _load_demo_sessions_for_runtime()
        summary = _session_summary(candidate)
        if demo_source == "synthetic_cloud_demo":
            summary["source"] = demo_source
        work.state = {
            "raw_polar_telemetry": summary,
            "biometric_metrics": asdict(calculate_metrics(candidate)),
            "domain_events": [{"event_type": "MetricsCalculated", "session_id": candidate.exercise_id}],
            "demo_mode": {
                "enabled": True,
                "network_called": False,
                "source": demo_source,
                "contains_personal_telemetry": False if demo_source == "synthetic_cloud_demo" else None,
            },
        }
    # This is an upstream, validated flag, NOT a medical classifier.
    if state.get("critical_safety_flag") is True:
        work.state["biometric_metrics"]["critical_safety_flag"] = True
    return work.state


def prepare_comparison(state: dict, source: str) -> dict:
    first, second, _ = _load_demo_sessions_for_runtime()
    summary = state["raw_polar_telemetry"]
    reference = second if source == "accesslink" and second.exercise_id != summary["exercise_id"] else first
    candidate = ExerciseSession(
        exercise_id=summary["exercise_id"], start_time=summary["start_time"],
        device=summary.get("device"), sport=summary.get("sport"),
        duration_seconds=summary.get("duration_seconds"),
        heart_rate_average=summary.get("heart_rate_average"),
        heart_rate_maximum=summary.get("heart_rate_maximum"),
    )
    # Reuse the metrics of the actual ingested session, not the frozen FIT candidate.
    metrics = BiometricMetrics(**{
        key: state["biometric_metrics"][key] for key in BiometricMetrics.__dataclass_fields__
    })
    reference_metrics = calculate_metrics(reference)
    comparison = asdict(compare_sessions(reference, candidate, reference_metrics, metrics))
    result = {
        "session_comparison": comparison,
        "comparison_metrics": {"reference": asdict(reference_metrics), "candidate": asdict(metrics)},
        "domain_events": [*state.get("domain_events", []), {
            "event_type": "SessionsCompared", "session_id": candidate.exercise_id,
        }],
    }
    result["workflow_decision"] = select_workflow_decision_from_state({**state, **result})
    return result


class ProgrammaticPreparationAgent(BaseAgent):
    phase: Literal["ingestion", "comparison"]
    source: Literal["local_fit", "accesslink"] = "local_fit"

    async def _run_async_impl(self, ctx):
        function = prepare_ingestion if self.phase == "ingestion" else prepare_comparison
        try:
            delta = await asyncio.to_thread(function, dict(ctx.session.state), self.source)
        except Exception:
            case = deepcopy(ctx.session.state["inference_case"])
            case.update(status="BLOCKED", termination_reason=f"{self.phase.upper()}_FAILED")
            delta = {"inference_case": case}
        yield Event(
            author=self.name, invocation_id=ctx.invocation_id,
            branch=ctx.branch,
            actions=EventActions(state_delta=delta),
        )
