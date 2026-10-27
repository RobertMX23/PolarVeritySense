"""ADK dispatcher that applies the deterministic workflow-routing policy."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.genai import types

from .clean_adk_tools import select_workflow_decision_from_state


class DeterministicMessageAgent(BaseAgent):
    """Render a safety/data-quality response without invoking an LLM."""

    message: str = ""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=self.message)]),
        )


class WorkflowRouteDispatcher(BaseAgent):
    """Choose exactly one downstream branch from deterministic calculated state."""

    route_to_agent_name: dict[str, str] = {
        "SAFETY_ESCALATION": "SafetyEscalationResponse",
        "DATA_QUALITY_REVIEW": "DataQualityReviewResponse",
        "RECOVERY_RECOMMENDATION": "RecommendationAndApproval",
        "CONTEXT_LIMITED_RECOMMENDATION": "RecommendationAndApproval",
        "COMPARABLE_TREND_RECOMMENDATION": "RecommendationAndApproval",
    }

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        decision = select_workflow_decision_from_state(ctx.session.state)
        ctx.session.state["workflow_decision"] = decision
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(state_delta={"workflow_decision": decision}),
        )

        target_name = self.route_to_agent_name[decision["route"]]
        target = next((agent for agent in self.sub_agents if agent.name == target_name), None)
        if target is None:
            raise RuntimeError(f"No existe el destino ADK para la ruta {decision['route']}.")
        async for event in target.run_async(ctx):
            yield event
