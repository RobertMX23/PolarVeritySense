"""Configuración de memoria oficial de ADK para el MVP.

La memoria es compartida entre runners durante la vida del proceso.  Para
producción se sustituye por VertexAiMemoryBankService o RAG sin cambiar el
contrato del agente.
"""

import os

from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService


def create_memory_services() -> tuple[InMemorySessionService, InMemoryMemoryService]:
    """Crea servicios compartidos para sesiones y conocimiento de largo plazo."""
    return InMemorySessionService(), InMemoryMemoryService()


def create_memory_service():
    """Build the configured ADK long-term memory service.

    Local mode is the safe default. Cloud mode is opt-in and requires the
    Vertex AI dependency plus an existing Agent Engine Memory Bank instance.
    """
    mode = os.getenv("ADK_MEMORY_MODE", "local").lower()
    if mode != "vertex":
        return InMemoryMemoryService()

    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    agent_engine_id = os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ID"]
    try:
        from google.adk.memory import VertexAiMemoryBankService
    except ImportError as exc:
        raise RuntimeError(
            "ADK_MEMORY_MODE=vertex requiere google-cloud-aiplatform[agent_engines,adk]."
        ) from exc
    return VertexAiMemoryBankService(
        project=project,
        location=location,
        agent_engine_id=agent_engine_id,
    )
