"""Composition root: Python prepares evidence; Gemini only interprets/reviews."""

import os

# These adapters also establish the src layout for `adk web .`.
from .programmatic_agents import ProgrammaticPreparationAgent
from .bounded_agents import BoundedInferenceAgent, BoundedRecommendationAgent, GovernedWorkflowAgent
from .routing_agent import DeterministicMessageAgent, WorkflowRouteDispatcher
from polar_assistant.application.inference_contracts import InferencePolicy
from polar_assistant.infrastructure.gemini_inference import GeminiInferenceGateway


def build_workflow(*, source="local_fit", name="SportAssistantRoot", gateway=None, policy=None):
    """Inject the model boundary for offline Runner tests; never connect on import."""
    policy = policy or InferencePolicy(max_input_tokens=int(os.getenv("GYM_COACH_MAX_INPUT_TOKENS", "4096")))
    gateway = gateway or GeminiInferenceGateway()
    stages = [
        BoundedInferenceAgent(name=agent_name, stage=stage, gateway=gateway, policy=policy)
        for agent_name, stage in (
            ("PhysiologyAnalystAgent", "analyst"),
            ("SafetyCriticAgent", "critic"),
            ("ProposalRefinementAgent", "refinement"),
        )
    ]
    recommendation = BoundedRecommendationAgent(
        name="RecommendationAndApproval", gateway=gateway, policy=policy, sub_agents=stages,
    )
    dispatcher = WorkflowRouteDispatcher(name="WorkflowRouteDispatcher", sub_agents=[
        DeterministicMessageAgent(
            name="SafetyEscalationResponse",
            message="Existe una bandera crítica de seguridad. Detén el entrenamiento y busca valoración profesional. No se aplicó ningún ajuste.",
        ),
        DeterministicMessageAgent(
            name="DataQualityReviewResponse",
            message="Faltan datos suficientes. Revisa el sensor y la sincronización antes de solicitar recomendaciones. No se aplicó ningún ajuste.",
        ),
        recommendation,
    ])
    return GovernedWorkflowAgent(name=name, policy=policy, sub_agents=[
        ProgrammaticPreparationAgent(name="TelemetryIngestion", phase="ingestion", source=source),
        ProgrammaticPreparationAgent(name="SessionComparisonPreparation", phase="comparison", source=source),
        dispatcher,
    ])


demo_agent = build_workflow()
full_workflow_agent = build_workflow(source="accesslink", name="SportAssistantFullWorkflow")
route_dispatcher = full_workflow_agent.find_agent("WorkflowRouteDispatcher")
root_agent = (
    full_workflow_agent if os.getenv("GYM_COACH_AGENT_MODE", "demo").lower() == "full_simulation"
    else demo_agent
)
