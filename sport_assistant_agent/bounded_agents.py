"""Custom ADK workflow with a single, auditable generation budget per case.

ADK owns session persistence/events. The injected gateway owns exactly one SDK
generation per attempt; there is no AutoFlow, tool-call or summarization loop.
"""

import threading
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.genai import types
from pydantic import Field, PrivateAttr, ValidationError

from polar_assistant.application.inference_contracts import (
    Critique, InferencePolicy, PolicyViolation, Proposal, Stage,
)
from polar_assistant.application.inference_policy import (
    approval_command, build_request, compact_evidence, proposal_id,
    render_proposal, reserve_call, validate_proposal, validate_stage,
)


def state_event(agent, ctx, **delta):
    return Event(author=agent.name, invocation_id=ctx.invocation_id, branch=ctx.branch,
                 actions=EventActions(state_delta=deepcopy(delta)))


def message_event(agent, ctx, text):
    return Event(author=agent.name, invocation_id=ctx.invocation_id, branch=ctx.branch,
                 content=types.Content(role="model", parts=[types.Part(text=text)]))


def user_text(ctx) -> str:
    content = ctx.user_content
    if not content or content.role != "user":
        return ""
    return "".join(part.text or "" for part in content.parts or [])


def _normalize_user_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(char for char in normalized if not unicodedata.combining(char)).split())


def is_welcome_message(text: str) -> bool:
    """Recognize a greeting-only turn without treating it as training context."""
    normalized = _normalize_user_text(text).strip("!¡?. ,")
    return normalized in {"", "hola", "buen dia", "buenos dias", "buenas tardes", "buenas noches", "hello", "hi"}


def welcome_message() -> str:
    return (
        "Bienvenido al asistente deportivo. Aún no analizaré datos ni haré una recomendación.\n"
        "¿Qué quieres revisar?\n"
        "1. La información principal de la última sesión disponible.\n"
        "2. La comparación entre sesiones disponibles.\n"
        "3. Una recomendación orientativa de recuperación o carga.\n"
        "Responde con una opción o describe tu objetivo. Esperaré tu respuesta antes de abrir un caso."
    )


def waiting_for_intent_case(policy: InferencePolicy) -> dict:
    return {
        "case_id": uuid4().hex[:12], "status": "AWAITING_INTENT", "calls_used": 0,
        "calls_remaining": policy.max_calls, "attempts": [], "user_context": "",
        "max_input_tokens": policy.max_input_tokens, "max_calls": policy.max_calls,
        "termination_reason": "WAITING_FOR_USER_INTENT",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def blocked_case(case, reason):
    updated = deepcopy(case)
    updated.update(status="BLOCKED", termination_reason=reason)
    return updated


class BoundedInferenceAgent(BaseAgent):
    stage: Stage
    gateway: Any = Field(exclude=True)
    policy: InferencePolicy = Field(default_factory=InferencePolicy)

    async def _run_async_impl(self, ctx):
        case = deepcopy(ctx.session.state["inference_case"])
        try:
            validate_stage(case, self.stage, self.policy)
            request = build_request(self.stage, case, self.policy)
            count = await self.gateway.count_tokens(request.prompt)
            case = reserve_call(case, self.stage, count, self.policy)
            # Runner persists this event BEFORE the generator resumes to dispatch.
            yield state_event(self, ctx, inference_case=case)
            reply = await self.gateway.generate(request)
            attempt = case["attempts"][-1]
            attempt.update(status="RECEIVED", usage=reply.usage, finish_reason=reply.finish_reason)
            if reply.finish_reason != "STOP":
                raise PolicyViolation("INCOMPLETE_MODEL_OUTPUT")
            output_count = await self.gateway.count_tokens(reply.text)
            attempt["output_tokens_counted"] = output_count
            if type(output_count) is not int or not 1 <= output_count <= request.max_output_tokens:
                raise PolicyViolation("OUTPUT_TOKEN_BUDGET")
            # Provider-reported input is separately audited; no further call if it disagrees.
            reported_input = reply.usage.get("input_tokens")
            if reported_input is not None and reported_input > self.policy.max_input_tokens:
                raise PolicyViolation("PROVIDER_INPUT_TOKEN_BUDGET")
            if self.stage == "critic":
                critique = Critique.model_validate_json(reply.text)
                if critique.verdict == "APPROVE" and critique.required_changes:
                    raise PolicyViolation("CONTRADICTORY_CRITIQUE")
                if critique.verdict == "REVISE" and not critique.required_changes:
                    raise PolicyViolation("EMPTY_REVISION")
                case["critique"] = critique.model_dump()
            else:
                proposal = Proposal.model_validate_json(reply.text)
                validate_proposal(proposal, case["evidence"],
                                  Critique.model_validate(case["critique"]) if self.stage == "refinement" else None)
                case["proposal"] = proposal.model_dump()
                case["proposal_id"] = proposal_id(case["proposal"])
                case["proposal_version"] = 2 if self.stage == "refinement" else 1
            attempt["status"] = "VALIDATED"
        except PolicyViolation as error:
            case = blocked_case(case, str(error))
        except ValidationError:
            case = blocked_case(case, "INVALID_MODEL_SCHEMA")
        except Exception:
            # No exception body: SDK messages can contain request data or credentials.
            case = blocked_case(case, "MODEL_OR_TOKEN_SERVICE_FAILED")
        if case["status"] == "BLOCKED" and case["attempts"]:
            case["attempts"][-1]["status"] = "FAILED"
        yield state_event(self, ctx, inference_case=case)


class BoundedRecommendationAgent(BaseAgent):
    gateway: Any = Field(exclude=True)
    policy: InferencePolicy = Field(default_factory=InferencePolicy)

    async def _run_async_impl(self, ctx):
        case = deepcopy(ctx.session.state["inference_case"])
        try:
            case["evidence"] = compact_evidence(ctx.session.state, case["user_context"])
        except (PolicyViolation, ValueError):
            yield state_event(self, ctx, inference_case=blocked_case(case, "EVIDENCE_INVALID"))
            return
        yield state_event(self, ctx, inference_case=case)
        for stage_agent in self.sub_agents:
            if stage_agent.stage == "refinement":
                verdict = ctx.session.state["inference_case"]["critique"]["verdict"]
                if verdict != "REVISE":
                    break
            async for event in stage_agent.run_async(ctx):
                yield event
            if ctx.session.state["inference_case"]["status"] == "BLOCKED":
                return
        case = deepcopy(ctx.session.state["inference_case"])
        verdict = case["critique"]["verdict"]
        if verdict == "REJECT":
            yield state_event(self, ctx, inference_case=blocked_case(case, "CRITIC_REJECTED"))
            return
        case.update(
            status="AWAITING_APPROVAL" if verdict == "APPROVE" else "AWAITING_HUMAN_REVIEW",
            termination_reason="CRITIC_APPROVED" if verdict == "APPROVE" else "REFINEMENT_REQUIRES_HUMAN_REVIEW",
            critic_approved_version=1 if verdict == "APPROVE" else None,
        )
        # Keep identity-bound approval instructions in local state, outside ALL
        # provider requests, including the final-message token count.
        case["approval_command"] = approval_command(case)
        text = render_proposal(case)
        try:
            count = await self.gateway.count_tokens(text)
            if type(count) is not int or not 1 <= count <= self.policy.final_output_tokens:
                raise PolicyViolation("FINAL_TOKEN_BUDGET")
            case.update(final_text=text, final_tokens=count)
        except Exception:
            case = blocked_case(case, "FINAL_TOKEN_VALIDATION_FAILED")
        yield state_event(self, ctx, inference_case=case, proposed_adjustment=case.get("proposal"))


class GovernedWorkflowAgent(BaseAgent):
    """One local process/session. No automatic case resets on user follow-ups.

    Deploying multiple workers needs a transactional shared reservation store;
    this local demo deliberately makes no distributed-budget guarantee.
    """

    policy: InferencePolicy = Field(default_factory=InferencePolicy)
    _locks: dict = PrivateAttr(default_factory=dict)

    async def _run_async_impl(self, ctx):
        key = (ctx.session.app_name, ctx.session.user_id, ctx.session.id)
        lock = self._locks.setdefault(key, threading.Lock())
        if not lock.acquire(blocking=False):
            yield message_event(self, ctx, "Hay un caso en ejecución. Espera su resultado; no se abrió otra inferencia.")
            return
        try:
            # A second invocation may have obtained a stale session before acquiring the lock.
            latest = await ctx.session_service.get_session(
                app_name=key[0], user_id=key[1], session_id=key[2],
            )
            if latest:
                ctx.session.state.update(latest.state)
            async for event in self._run_case(ctx):
                yield event
        finally:
            lock.release()

    async def _run_case(self, ctx):
        text = user_text(ctx).strip()
        previous = ctx.session.state.get("inference_case")
        new_case = text == "/nuevo_caso" or text.startswith("/nuevo_caso ")

        if previous and previous.get("status") == "AWAITING_INTENT":
            if is_welcome_message(text):
                yield message_event(self, ctx, welcome_message())
                return
            # The next substantive user message starts a real case. The
            # welcome state is not an analysed session and is not audited as one.
            previous = None

        if not previous and not new_case and is_welcome_message(text):
            yield state_event(self, ctx, inference_case=waiting_for_intent_case(self.policy))
            yield message_event(self, ctx, welcome_message())
            return

        if previous and not new_case:
            async for event in self._follow_up(ctx, previous, text):
                yield event
            return
        if new_case:
            text = text.removeprefix("/nuevo_caso").strip()
        case = {
            "case_id": uuid4().hex[:12], "status": "RUNNING", "calls_used": 0,
            "calls_remaining": 3, "attempts": [], "user_context": text,
            "max_input_tokens": self.policy.max_input_tokens, "max_calls": 3,
            "termination_reason": None, "created_at": datetime.now(timezone.utc).isoformat(),
        }
        # Drop stale evidence/proposals before any preparation can fail.
        delta = {key: None for key in (
            "raw_polar_telemetry", "biometric_metrics", "session_comparison", "comparison_metrics",
            "workflow_decision", "proposed_adjustment", "execution_audit_log",
        )}
        if previous:
            history = list(ctx.session.state.get("case_audit_history", []))
            history.append({key: previous.get(key) for key in (
                "case_id", "calls_used", "attempts", "status", "termination_reason", "proposal_id",
            )})
            delta["case_audit_history"] = history
        if len(text) > 1200:
            case = blocked_case(case, "CONTEXT_TOO_LARGE")
            case["user_context"] = ""  # No raw pasted telemetry retained in case state.
        yield state_event(self, ctx, **delta, inference_case=case)
        if case["status"] == "RUNNING":
            for agent in self.sub_agents:
                async for event in agent.run_async(ctx):
                    yield event
                if ctx.session.state["inference_case"]["status"] == "BLOCKED":
                    break
        case = deepcopy(ctx.session.state["inference_case"])
        if case["status"] == "RUNNING":
            # Safety/data-quality branch has already emitted its fixed response.
            case = blocked_case(case, ctx.session.state.get("workflow_decision", {}).get("route", "NO_ROUTE"))
            yield state_event(self, ctx, inference_case=case)
            return
        if case["status"] == "BLOCKED":
            yield message_event(self, ctx, "Caso bloqueado: " + case["termination_reason"] + ". No se aplicó ningún ajuste.")
        else:
            yield message_event(self, ctx, case["final_text"])

    async def _follow_up(self, ctx, previous, text):
        case = deepcopy(previous)
        if case["status"] in {"AWAITING_APPROVAL", "AWAITING_HUMAN_REVIEW"}:
            expected = approval_command(case)
            if text == expected and case.get("proposal_id") == proposal_id(case["proposal"]):
                audit = {
                    "status": "UPDATED_SIMULATION", "provider": "local_audit_only",
                    "audit_event_id": uuid4().hex, "case_id": case["case_id"],
                    "proposal_id": case["proposal_id"], "proposal_version": case["proposal_version"],
                    "human_review_confirmed": case["status"] == "AWAITING_HUMAN_REVIEW",
                    "approval_text": text, "next_session": case["proposal"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                case.update(status="APPROVED_SIMULATION", termination_reason="HUMAN_APPROVED")
                yield state_event(self, ctx, inference_case=case, execution_audit_log=audit)
                yield message_event(self, ctx, "Aprobación registrada sólo como simulación local. Sin cambios externos ni nuevas inferencias.")
                return
            yield message_event(self, ctx, "No se registró aprobación. Confirma la propuesta exacta con: " + expected)
        elif case["status"] == "APPROVED_SIMULATION":
            yield message_event(self, ctx, "La simulación ya fue registrada; no se repitió la operación ni la inferencia.")
        else:
            if case["status"] == "RUNNING":
                yield state_event(self, ctx, inference_case=blocked_case(case, "INTERRUPTED_CASE"))
            yield message_event(self, ctx, "Este caso está cerrado o interrumpido. No se reintentó. Usa /nuevo_caso seguido del contexto para iniciar otro.")
