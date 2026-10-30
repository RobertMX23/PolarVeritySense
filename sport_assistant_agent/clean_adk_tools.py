from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google.adk.tools import ToolContext

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from polar_assistant.application.events import InMemoryEventBus
from polar_assistant.application.use_cases import AnalyzeExercise, CompareSessions
from polar_assistant.domain.entities import BiometricMetrics, SessionComparison
from polar_assistant.domain.metrics import calculate_metrics
from polar_assistant.domain.routing import select_workflow_route
from polar_assistant.infrastructure.fit import load_fit_session
from polar_assistant.infrastructure.polar import AccessLinkExerciseRepository


DEMO_REFERENCE_EXERCISE_ID = "0bLJlrpB"
DEMO_CANDIDATE_EXERCISE_ID = "yVQw6bnw"
DEMO_ZONE_LIMITS = ((0, 92, 110), (1, 110, 128), (2, 128, 146), (3, 146, 165), (4, 165, 241))


def _load_demo_sessions():
    """Load the fixed, real FIT evidence used by the time-bounded demo."""
    root = Path(__file__).resolve().parents[1]
    # Cloud QA can mount the existing files at runtime without baking personal
    # telemetry into a container or publishing it to the source repository.
    configured_fit_dir = os.getenv("POLAR_FIT_DIR")
    fit_dir = Path(configured_fit_dir) if configured_fit_dir else root / "data" / "accesslink_fit"
    reference = load_fit_session(
        fit_dir / f"{DEMO_REFERENCE_EXERCISE_ID}.fit",
        exercise_id=DEMO_REFERENCE_EXERCISE_ID,
        sport="HIIT",
        zone_limits=DEMO_ZONE_LIMITS,
    )
    candidate = load_fit_session(
        fit_dir / f"{DEMO_CANDIDATE_EXERCISE_ID}.fit",
        exercise_id=DEMO_CANDIDATE_EXERCISE_ID,
        sport="TREADMILL_RUNNING",
        zone_limits=DEMO_ZONE_LIMITS,
    )
    return reference, candidate


def _session_summary(session) -> dict[str, Any]:
    """Return a privacy-minimized summary; never place raw FIT samples in ADK state."""
    valid_samples = [x for x in session.heart_rate_samples if 30 <= x <= 240]
    return {
        "exercise_id": session.exercise_id,
        "start_time": session.start_time,
        "device": session.device,
        "sport": session.sport,
        "duration_seconds": session.duration_seconds,
        "heart_rate_average": session.heart_rate_average,
        "heart_rate_maximum": session.heart_rate_maximum,
        "heart_rate_minimum": min(valid_samples) if valid_samples else None,
        "heart_rate_zones": list(session.heart_rate_zones),
        "zone_limits_source": "demo_configuration",
        "zone_duration_method": "sample_count_assuming_1hz",
        "source": "FIT local real, descargado previamente desde Polar AccessLink",
        "raw_samples_excluded": True,
    }


def select_workflow_decision_from_state(state: dict[str, Any]) -> dict[str, Any]:
    """Select a deterministic route from already validated ADK state.

    The caller owns orchestration. This helper neither calls an LLM nor performs
    persistence; it only transforms calculated state into an auditable decision.
    """
    metrics_payload = state.get("biometric_metrics")
    comparison_payload = state.get("session_comparison")
    if not isinstance(metrics_payload, dict) or not isinstance(comparison_payload, dict):
        raise ValueError("No existen biometric_metrics y session_comparison para decidir la ruta.")

    metrics = BiometricMetrics(
        mean_hr_bpm=metrics_payload.get("mean_hr_bpm"),
        max_hr_bpm=metrics_payload.get("max_hr_bpm"),
        cardiac_drift_pct=metrics_payload.get("cardiac_drift_pct"),
        zone_seconds=metrics_payload.get("zone_seconds", {}),
        fatigue_signal=bool(metrics_payload.get("fatigue_signal", False)),
        data_quality=str(metrics_payload.get("data_quality", "SUMMARY_ONLY")),
    )
    comparison = SessionComparison(**comparison_payload)
    decision = select_workflow_route(
        metrics,
        comparison,
        critical_safety_flag=bool(metrics_payload.get("critical_safety_flag", False)),
    )
    return {
        "route": decision.route.value,
        "llm_analysis_required": decision.llm_analysis_required,
        "plan_update_allowed": decision.plan_update_allowed,
        "reason": decision.reason,
    }


def analyze_exercise_tool(exercise_id: str | None, tool_context: ToolContext) -> dict[str, Any]:
    """Ejecuta el caso de uso limpio y expone sus resultados al estado ADK."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    token = os.getenv("POLAR_ACCESSLINK_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Falta POLAR_ACCESSLINK_ACCESS_TOKEN en .env.")
    bus = InMemoryEventBus()
    repository = AccessLinkExerciseRepository(token)
    result = AnalyzeExercise(repository, bus).execute(exercise_id or None)
    summary = {key: value for key, value in result["session"].items() if key != "heart_rate_samples"}
    valid_samples = [x for x in result["session"].get("heart_rate_samples", []) if 30 <= x <= 240]
    summary.update(heart_rate_minimum=min(valid_samples) if valid_samples else None,
                   zone_limits_source="polar_accesslink", zone_duration_method="provider_duration")
    summary.update(source="Polar AccessLink", raw_samples_excluded=True)
    tool_context.state["raw_polar_telemetry"] = summary
    tool_context.state["biometric_metrics"] = result["metrics"]
    tool_context.state["domain_events"] = [event.__dict__ for event in bus.events]
    return {
        "status": "success",
        "session": summary,
        "metrics": result["metrics"],
        "events": [event.event_type for event in bus.events],
    }


def compare_recent_fit_sessions_tool(tool_context: ToolContext) -> dict[str, Any]:
    """Compare the two prepared local FIT sessions without calling Polar or an LLM."""
    reference, candidate = _load_demo_sessions()
    bus = InMemoryEventBus()
    result = CompareSessions(bus).execute(reference, candidate)
    comparison_events = [event.__dict__ for event in bus.events]
    existing_events = list(tool_context.state.get("domain_events", []))
    tool_context.state["session_comparison"] = result["comparison"]
    tool_context.state["comparison_metrics"] = {
        "reference": result["reference_metrics"],
        "candidate": result["candidate_metrics"],
    }
    # The full workflow already receives live metrics from ingestion.  The
    # comparison tool is also intentionally runnable in isolation for tests and
    # local troubleshooting, where candidate metrics are the deterministic
    # evidence available for selecting a route.
    tool_context.state.setdefault("biometric_metrics", result["candidate_metrics"])
    tool_context.state["workflow_decision"] = select_workflow_decision_from_state(tool_context.state)
    tool_context.state["domain_events"] = [*existing_events, *comparison_events]
    return {
        "status": "success",
        "comparison": result["comparison"],
        "events": [event["event_type"] for event in comparison_events],
    }


def prepare_demo_evidence_tool(tool_context: ToolContext) -> dict[str, Any]:
    """Populate demo state from fixed real FIT files with no live network dependency.

    This is intentionally a deterministic boundary: it gives the LLM compact
    calculated evidence, never the FIT samples, and does not expose a plan-update
    capability.
    """
    if tool_context.state.get("demo_evidence_ready"):
        return {"status": "already_prepared", "exercise_id": DEMO_CANDIDATE_EXERCISE_ID}

    reference, candidate = _load_demo_sessions()
    candidate_metrics = asdict(calculate_metrics(candidate))
    bus = InMemoryEventBus()
    comparison_result = CompareSessions(bus).execute(reference, candidate)
    events = [event.__dict__ for event in bus.events]
    events.append(
        {
            "event_type": "DemoEvidencePrepared",
            "session_id": candidate.exercise_id,
            "payload": {"source": "local_real_fit", "network_called": False},
        }
    )

    tool_context.state["raw_polar_telemetry"] = _session_summary(candidate)
    tool_context.state["biometric_metrics"] = candidate_metrics
    tool_context.state["session_comparison"] = comparison_result["comparison"]
    tool_context.state["comparison_metrics"] = {
        "reference": comparison_result["reference_metrics"],
        "candidate": comparison_result["candidate_metrics"],
    }
    tool_context.state["workflow_decision"] = select_workflow_decision_from_state(tool_context.state)
    tool_context.state["domain_events"] = events
    tool_context.state["demo_evidence_ready"] = True
    tool_context.state["demo_mode"] = {
        "enabled": True,
        "source": "real FIT recordings prepared locally",
        "network_called": False,
        "plan_updates_available": False,
    }
    return {
        "status": "success",
        "exercise_id": candidate.exercise_id,
        "metrics": candidate_metrics,
        "comparison": comparison_result["comparison"],
        "events": [event["event_type"] for event in events],
    }
