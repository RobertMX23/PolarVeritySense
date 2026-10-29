"""Storage adapters for the curated training-session contract.

The in-memory adapter is test-only. Cloud adapters can receive the official
Firestore or BigQuery client at composition time, keeping Google SDK imports
out of the domain/application layers.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from polar_assistant.application.curated_sessions import CuratedTrainingSession


class InMemoryCuratedSessionRepository:
    """Deterministic repository for unit tests and local contract checks."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, CuratedTrainingSession]] = defaultdict(dict)

    def upsert(self, session: CuratedTrainingSession) -> None:
        self._sessions[session.subject_id][session.session_id] = session

    def latest_for_subject(self, subject_id: str) -> CuratedTrainingSession | None:
        sessions = self.list_for_subject(subject_id, limit=1)
        return sessions[0] if sessions else None

    def list_for_subject(self, subject_id: str, *, limit: int) -> list[CuratedTrainingSession]:
        if limit < 1:
            raise ValueError("limit debe ser al menos 1")
        return sorted(
            self._sessions.get(subject_id, {}).values(),
            key=lambda session: session.started_at,
            reverse=True,
        )[:limit]


class FirestoreCuratedSessionWriter:
    """Write to `athletes/{subject_id}/sessions/{session_id}` through a client.

    This adapter needs a configured Firestore client in the sync service. It is
    intentionally a writer only: Cloud Run's interactive agent reads through a
    repository/query service with authenticated-subject checks.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def upsert(self, session: CuratedTrainingSession) -> None:
        reference = (
            self._client.collection("athletes")
            .document(session.subject_id)
            .collection("sessions")
            .document(session.session_id)
        )
        reference.set(session.firestore_document(), merge=False)


class BigQueryCuratedSessionWriter:
    """Insert an allowlisted row; retries are handled by the sync orchestrator."""

    def __init__(self, client: Any, table_id: str) -> None:
        self._client = client
        self._table_id = table_id

    def upsert(self, session: CuratedTrainingSession) -> None:
        errors = self._client.insert_rows_json(self._table_id, [session.bigquery_row()])
        if errors:
            raise RuntimeError("BigQuery rechazó la sesión curada.")
