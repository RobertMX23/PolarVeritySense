"""Read a bounded, curated Firestore session list through the repository port.

This is an operator-only technical verification for the local test subject. It
uses ADC and Firestore's REST ``runQuery`` endpoint, then injects that narrow
client into the reusable repository. It does not expose a chat route or map an
IAP identity to a subject.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polar_assistant.infrastructure.curated_session_store import FirestoreCuratedSessionRepository
from scripts.firestore_curated_smoke import adc_token


def decode_firestore_value(value: dict[str, Any]) -> Any:
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
        return {
            key: decode_firestore_value(nested)
            for key, nested in value["mapValue"].get("fields", {}).items()
        }
    if "arrayValue" in value:
        return [decode_firestore_value(item) for item in value["arrayValue"].get("values", [])]
    raise ValueError("Firestore devolvió un tipo de valor no permitido.")


class FirestoreRestSessionDocumentClient:
    """Read one subject's sessions in descending time order through REST."""

    def __init__(self, *, project_id: str, database_id: str, token: str) -> None:
        self._project_id = project_id
        self._database_id = database_id
        self._token = token

    def list_session_documents(self, *, subject_id: str, limit: int) -> list[dict[str, Any]]:
        url = (
            f"https://firestore.googleapis.com/v1/projects/{self._project_id}"
            f"/databases/{self._database_id}/documents/athletes/{subject_id}:runQuery"
        )
        body = {
            "structuredQuery": {
                "from": [{"collectionId": "sessions"}],
                "orderBy": [{"field": {"fieldPath": "started_at"}, "direction": "DESCENDING"}],
                "limit": limit,
            }
        }
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        if not response.ok:
            try:
                message = response.json().get("error", {}).get("message", "sin detalle")
            except ValueError:
                message = "sin detalle"
            raise RuntimeError(f"Firestore rechazó la consulta ({response.status_code}): {message}")
        documents: list[dict[str, Any]] = []
        for result in response.json():
            raw_document = result.get("document")
            if isinstance(raw_document, dict):
                fields = raw_document.get("fields", {})
                documents.append({key: decode_firestore_value(value) for key, value in fields.items()})
        return documents


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--subject-id", required=True)
    parser.add_argument("--database-id", default="(default)")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit debe ser al menos 1")

    repository = FirestoreCuratedSessionRepository(
        FirestoreRestSessionDocumentClient(
            project_id=args.project_id,
            database_id=args.database_id,
            token=adc_token(),
        )
    )
    sessions = repository.list_for_subject(args.subject_id, limit=args.limit)
    print(json.dumps({
        "status": "FIRESTORE_QUERY_SMOKE_PASSED",
        "project_id": args.project_id,
        "subject_id": args.subject_id,
        "records_read": len(sessions),
        "ordered_descending_by_started_at": all(
            sessions[index].started_at >= sessions[index + 1].started_at
            for index in range(len(sessions) - 1)
        ),
        "records_with_zone_periods": sum(bool(session.zone_periods) for session in sessions),
        "session_ids": [session.session_id for session in sessions],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
