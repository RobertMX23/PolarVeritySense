"""ADK tool factory for the curated-session query boundary."""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext

from polar_assistant.application.curated_sessions import CuratedSessionQueryService


def build_latest_curated_session_tool(query_service: CuratedSessionQueryService):
    """Create a tool that derives the subject solely from authenticated state.

    The user and the model cannot pass an arbitrary subject ID. An identity
    middleware added with IAP/OAuth must set ``authenticated_subject_id`` before
    this tool runs.
    """

    def query_latest_curated_session_tool(tool_context: ToolContext) -> dict[str, Any]:
        """Devuelve el resumen curado de la última sesión del usuario autenticado."""
        subject_id = tool_context.state.get("authenticated_subject_id")
        if not isinstance(subject_id, str) or not subject_id.startswith("ath_"):
            return {"status": "AUTHENTICATED_SUBJECT_REQUIRED"}
        return query_service.latest_for_authenticated_subject(subject_id)

    return query_latest_curated_session_tool
