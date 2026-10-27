"""Deterministic routing policy for the Gym Coach workflow.

This policy deliberately contains no LLM or ADK imports.  It converts validated
metrics and comparison limitations into an explicit route that an ADK workflow
can orchestrate later.  The priority order is safety, data integrity, fatigue,
comparison context, and normal trend analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .entities import BiometricMetrics, SessionComparison


class WorkflowRoute(StrEnum):
    """Named, auditable paths through the post-training workflow."""

    SAFETY_ESCALATION = "SAFETY_ESCALATION"
    DATA_QUALITY_REVIEW = "DATA_QUALITY_REVIEW"
    RECOVERY_RECOMMENDATION = "RECOVERY_RECOMMENDATION"
    CONTEXT_LIMITED_RECOMMENDATION = "CONTEXT_LIMITED_RECOMMENDATION"
    COMPARABLE_TREND_RECOMMENDATION = "COMPARABLE_TREND_RECOMMENDATION"


@dataclass(frozen=True)
class WorkflowDecision:
    """The deterministic decision passed to orchestration and audit layers."""

    route: WorkflowRoute
    llm_analysis_required: bool
    plan_update_allowed: bool
    reason: str


def select_workflow_route(
    metrics: BiometricMetrics,
    comparison: SessionComparison,
    *,
    critical_safety_flag: bool = False,
) -> WorkflowDecision:
    """Select the safest applicable route without drawing medical conclusions.

    ``critical_safety_flag`` must be computed and validated upstream.  A true
    flag never authorizes a plan update.  All recommendation paths still require
    the separate explicit-human-approval gate before local audit persistence.
    """
    if critical_safety_flag:
        return WorkflowDecision(
            route=WorkflowRoute.SAFETY_ESCALATION,
            llm_analysis_required=False,
            plan_update_allowed=False,
            reason="critical_safety_flag_true",
        )
    if metrics.data_quality != "HIGH":
        return WorkflowDecision(
            route=WorkflowRoute.DATA_QUALITY_REVIEW,
            llm_analysis_required=False,
            plan_update_allowed=False,
            reason="insufficient_heart_rate_samples",
        )
    if metrics.fatigue_signal:
        return WorkflowDecision(
            route=WorkflowRoute.RECOVERY_RECOMMENDATION,
            llm_analysis_required=True,
            plan_update_allowed=False,
            reason="cardiac_drift_above_threshold",
        )
    if not comparison.comparable_for_load_trend:
        return WorkflowDecision(
            route=WorkflowRoute.CONTEXT_LIMITED_RECOMMENDATION,
            llm_analysis_required=True,
            plan_update_allowed=False,
            reason="comparison_limited_by_context",
        )
    return WorkflowDecision(
        route=WorkflowRoute.COMPARABLE_TREND_RECOMMENDATION,
        llm_analysis_required=True,
        plan_update_allowed=False,
        reason="validated_comparable_sessions_without_fatigue_signal",
    )
