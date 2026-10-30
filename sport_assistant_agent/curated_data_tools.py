"""ADK tool factory for the curated-session query boundary."""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext

from polar_assistant.application.curated_sessions import CuratedSessionQueryService


def authenticated_subject_id_from_state(state: dict[str, Any]) -> str | None:
    """Return only the server-bound subject stored in trusted session state."""
    subject_id = state.get("authenticated_subject_id")
    return subject_id if isinstance(subject_id, str) and subject_id.startswith("ath_") else None


def build_latest_curated_session_tool(query_service: CuratedSessionQueryService):
    """Create a tool that derives the subject solely from authenticated state.

    The user and the model cannot pass an arbitrary subject ID. An identity
    middleware added with IAP/OAuth must set ``authenticated_subject_id`` before
    this tool runs.
    """

    def query_latest_curated_session_tool(tool_context: ToolContext) -> dict[str, Any]:
        """Devuelve el resumen curado de la última sesión del usuario autenticado."""
        subject_id = authenticated_subject_id_from_state(tool_context.state)
        if subject_id is None:
            return {"status": "AUTHENTICATED_SUBJECT_REQUIRED"}
        return query_service.latest_for_authenticated_subject(subject_id)

    return query_latest_curated_session_tool


def build_curated_history_tool(query_service: CuratedSessionQueryService):
    """Create a bounded, read-only history tool scoped to trusted state."""

    def query_curated_history_tool(tool_context: ToolContext, limit: int = 5) -> dict[str, Any]:
        """Lista hasta cinco sesiones curadas del usuario autenticado."""
        subject_id = authenticated_subject_id_from_state(tool_context.state)
        if subject_id is None:
            return {"status": "AUTHENTICATED_SUBJECT_REQUIRED"}
        if not isinstance(limit, int) or not 1 <= limit <= 5:
            return {"status": "INVALID_HISTORY_LIMIT"}
        return query_service.list_for_authenticated_subject(subject_id, limit=limit)

    return query_curated_history_tool


def build_curated_session_by_id_tool(query_service: CuratedSessionQueryService):
    """Create a read-only lookup that cannot cross an authenticated subject."""

    def query_curated_session_by_id_tool(session_id: str, tool_context: ToolContext) -> dict[str, Any]:
        """Devuelve una sesión curada del usuario autenticado por su ID interno."""
        subject_id = authenticated_subject_id_from_state(tool_context.state)
        if subject_id is None:
            return {"status": "AUTHENTICATED_SUBJECT_REQUIRED"}
        if not isinstance(session_id, str) or not session_id.startswith("ses_"):
            return {"status": "INVALID_CURATED_SESSION_ID"}
        return query_service.session_for_authenticated_subject(subject_id, session_id=session_id)

    return query_curated_session_by_id_tool
