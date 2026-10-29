"""Composition root: Python prepares evidence; Gemini only interprets/reviews."""

import os

# These adapters also establish the src layout for `adk web .`.
from .programmatic_agents import ProgrammaticPreparationAgent
from .bounded_agents import BoundedInferenceAgent, BoundedRecommendationAgent, GovernedWorkflowAgent
from .routing_agent import DeterministicMessageAgent, WorkflowRouteDispatcher
from polar_assistant.application.inference_contracts import InferencePolicy
from polar_assistant.application.curated_sessions import CuratedSessionQueryService
from polar_assistant.infrastructure.curated_session_store import FirestoreCuratedSessionRepository
from polar_assistant.infrastructure.gemini_inference import GeminiInferenceGateway


def _firestore_query_service_for_runtime() -> CuratedSessionQueryService | None:
    """Compose Firestore only when the server has an explicit QA subject binding."""
    if not os.getenv("FIRESTORE_QA_SUBJECT_ID", "").startswith("ath_"):
        return None
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        return None
    from .firestore_runtime import FirestoreRuntimeSessionDocumentClient

    return CuratedSessionQueryService(
        FirestoreCuratedSessionRepository(FirestoreRuntimeSessionDocumentClient())
    )


def build_workflow(*, source="local_fit", name="SportAssistantRoot", gateway=None, policy=None,
                   curated_session_query=None):
    """Inject the model boundary for offline Runner tests; never connect on import."""
    policy = policy or InferencePolicy(max_input_tokens=int(os.getenv("GYM_COACH_MAX_INPUT_TOKENS", "4096")))
    gateway = gateway or GeminiInferenceGateway()
    stage_descriptions = {
        "analyst": "Interpreta evidencia biométrica ya calculada y propone una acción acotada.",
        "critic": "Valida la propuesta contra las reglas de seguridad y de evidencia.",
        "refinement": "Corrige una propuesta sólo cuando el crítico solicitó REVISE.",
    }
    stages = [
        BoundedInferenceAgent(
            name=agent_name,
            description=stage_descriptions[stage],
            stage=stage,
            gateway=gateway,
            policy=policy,
        )
        for agent_name, stage in (
            ("PhysiologyAnalystAgent", "analyst"),
            ("SafetyCriticAgent", "critic"),
            ("ProposalRefinementAgent", "refinement"),
        )
    ]
    recommendation = BoundedRecommendationAgent(
        name="RecommendationAndApproval",
        description="Ejecuta la cadena acotada analista, crítico y refinamiento condicional.",
        gateway=gateway,
        policy=policy,
        sub_agents=stages,
    )
    dispatcher = WorkflowRouteDispatcher(name="WorkflowRouteDispatcher", sub_agents=[
        DeterministicMessageAgent(
            name="SafetyEscalationResponse",
            description="Emite una respuesta fija ante una bandera crítica de seguridad.",
            message="Existe una bandera crítica de seguridad. Detén el entrenamiento y busca valoración profesional. No se aplicó ningún ajuste.",
        ),
        DeterministicMessageAgent(
            name="DataQualityReviewResponse",
            description="Emite una respuesta fija cuando faltan datos válidos.",
            message="Faltan datos suficientes. Revisa el sensor y la sincronización antes de solicitar recomendaciones. No se aplicó ningún ajuste.",
        ),
        recommendation,
    ], description="Selecciona una sola ruta determinista a partir de métricas ya calculadas.")
    return GovernedWorkflowAgent(name=name, policy=policy, curated_session_query=(
        _firestore_query_service_for_runtime()
        if curated_session_query is None else curated_session_query
    ), sub_agents=[
        ProgrammaticPreparationAgent(
            name="TelemetryIngestion",
            description="Carga telemetría validada y calcula métricas con Python.",
            phase="ingestion",
            source=source,
        ),
        ProgrammaticPreparationAgent(
            name="SessionComparisonPreparation",
            description="Compara sesiones y genera la decisión de ruta sin usar un LLM.",
            phase="comparison",
            source=source,
        ),
        dispatcher,
    ], description="Orquesta el caso, conserva el presupuesto y aplica el control HITL.")


demo_agent = build_workflow()
full_workflow_agent = build_workflow(source="accesslink", name="SportAssistantFullWorkflow")
route_dispatcher = full_workflow_agent.find_agent("WorkflowRouteDispatcher")
root_agent = (
    full_workflow_agent if os.getenv("GYM_COACH_AGENT_MODE", "demo").lower() == "full_simulation"
    else demo_agent
)
