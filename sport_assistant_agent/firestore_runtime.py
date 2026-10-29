"""Runtime-only Firestore reader for curated session documents.

The ADK process receives Application Default Credentials from its Cloud Run
service account.  This adapter uses only Firestore's REST API and one
``athletes/{subject_id}/sessions`` subcollection; it never receives Polar
tokens, raw provider payloads, or a subject selected by chat text.
"""

from __future__ import annotations

import os
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession


def _decode_firestore_value(value: dict[str, Any]) -> Any:
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "timestampValue" in value:
        return value["timestampValue"]
    if "stringValue" in value:
        return value["stringValue"]
    if "mapValue" in value:
        return {key: _decode_firestore_value(nested) for key, nested in value["mapValue"].get("fields", {}).items()}
    if "arrayValue" in value:
        return [_decode_firestore_value(item) for item in value["arrayValue"].get("values", [])]
    raise ValueError("Firestore devolvió un tipo de valor no permitido.")


class FirestoreRuntimeSessionDocumentClient:
    """Read an allowlisted session collection with Cloud Run ADC."""

    def __init__(self, *, project_id: str | None = None, database_id: str = "(default)") -> None:
        self._project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._database_id = database_id
        if not self._project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT es requerido para consultar Firestore.")
        self._session: AuthorizedSession | None = None

    def _authorized_session(self) -> AuthorizedSession:
        if self._session is None:
            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/datastore"])
            self._session = AuthorizedSession(credentials)
        return self._session

    def list_session_documents(self, *, subject_id: str, limit: int) -> list[dict[str, Any]]:
        if not subject_id.startswith("ath_"):
            raise ValueError("El sujeto autenticado no es válido.")
        url = (
            f"https://firestore.googleapis.com/v1/projects/{self._project_id}"
            f"/databases/{self._database_id}/documents/athletes/{subject_id}:runQuery"
        )
        response = self._authorized_session().post(
            url,
            json={"structuredQuery": {
                "from": [{"collectionId": "sessions"}],
                "orderBy": [{"field": {"fieldPath": "started_at"}, "direction": "DESCENDING"}],
                "limit": limit,
            }},
            timeout=20,
        )
        if not response.ok:
            raise RuntimeError(f"Firestore rechazó la consulta de sesiones ({response.status_code}).")
        documents: list[dict[str, Any]] = []
        for result in response.json():
            document = result.get("document")
            if isinstance(document, dict):
                documents.append({
                    key: _decode_firestore_value(value)
                    for key, value in document.get("fields", {}).items()
                })
        return documents
