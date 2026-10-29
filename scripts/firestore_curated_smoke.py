"""Write and verify a small, privacy-minimized curated-session batch in Firestore.

The script reads the already-authorized Polar AccessLink v3 feed, validates it
through the curated Pydantic contract, and upserts a bounded set of sessions to
``athletes/{subject_id}/sessions/{session_id}``.  It never stores the raw Polar
payload, OAuth token, samples, location, notes, or biometric time series.

It uses Application Default Credentials (ADC).  A production synchronizer
should use the dedicated ``polar-sport-sync`` service account through a
keyless runtime identity; this operator smoke test deliberately creates no
service-account key.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.auth
from google.auth.transport.requests import Request
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from polar_assistant.application.curated_sessions import curate_accesslink_v3_exercise
from scripts.polar_v3_inventory import fetch_exercises


TIMESTAMP_FIELDS = frozenset({"started_at", "source_created_at", "source_modified_at", "ingested_at"})
FIRESTORE_SCOPE = "https://www.googleapis.com/auth/datastore"


def firestore_value(value: Any, *, field_name: str | None = None) -> dict[str, Any]:
    """Encode the curated contract for Firestore's REST document format."""
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, str):
        if field_name in TIMESTAMP_FIELDS:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return {
                "timestampValue": parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            }
        return {"stringValue": value}
    if isinstance(value, dict):
        return {
            "mapValue": {
                "fields": {
                    key: firestore_value(nested, field_name=key)
                    for key, nested in value.items()
                }
            }
        }
    if isinstance(value, (list, tuple)):
        return {
            "arrayValue": {
                "values": [firestore_value(item) for item in value]
            }
        }
    raise TypeError(f"Valor no soportado para Firestore: {type(value)!r}")


def firestore_fields(document: dict[str, Any]) -> dict[str, Any]:
    return {
        key: firestore_value(value, field_name=key)
        for key, value in document.items()
    }


def adc_token() -> str:
    credentials, _ = google.auth.default(scopes=[FIRESTORE_SCOPE])
    credentials.refresh(Request())
    if not credentials.token:
        raise RuntimeError("ADC no devolvió un token para Firestore.")
    return credentials.token


def _document_url(*, project_id: str, database_id: str, subject_id: str, session_id: str) -> str:
    return (
        f"https://firestore.googleapis.com/v1/projects/{project_id}"
        f"/databases/{database_id}/documents/athletes/{subject_id}/sessions/{session_id}"
    )


def upsert_and_read(
    *,
    project_id: str,
    database_id: str,
    subject_id: str,
    session_id: str,
    document: dict[str, Any],
    token: str,
) -> dict[str, Any]:
    url = _document_url(
        project_id=project_id,
        database_id=database_id,
        subject_id=subject_id,
        session_id=session_id,
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.patch(url, headers=headers, json={"fields": firestore_fields(document)}, timeout=30)
    if not response.ok:
        try:
            message = response.json().get("error", {}).get("message", "sin detalle")
        except ValueError:
            message = "sin detalle"
        raise RuntimeError(f"Firestore rechazó la escritura ({response.status_code}): {message}")
    verified = requests.get(url, headers=headers, timeout=30)
    verified.raise_for_status()
    return verified.json()


def stored_zone_count(document: dict[str, Any]) -> int:
    values = (
        document.get("fields", {})
        .get("zone_periods", {})
        .get("arrayValue", {})
        .get("values", [])
    )
    return len(values) if isinstance(values, list) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--database-id", default="(default)")
    parser.add_argument("--subject-id", default="ath_local_smoke_2026")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit debe ser al menos 1")

    polar_token = str(dotenv_values(ROOT / ".env").get("POLAR_ACCESSLINK_ACCESS_TOKEN") or "")
    if not polar_token:
        print("Falta POLAR_ACCESSLINK_ACCESS_TOKEN en .env; no se hizo ninguna llamada.")
        return 2

    exercises = fetch_exercises(polar_token)
    curated = [
        curate_accesslink_v3_exercise(subject_id=args.subject_id, payload=exercise)
        for exercise in exercises[: args.limit]
    ]
    if not curated:
        print("No hay sesiones de Polar para validar; no se escribió Firestore.")
        return 3

    token = adc_token()
    verified_documents: list[dict[str, Any]] = []
    # Two identical writes per deterministic ID demonstrate idempotent upserts.
    for session in curated:
        document = session.firestore_document()
        upsert_and_read(
            project_id=args.project_id,
            database_id=args.database_id,
            subject_id=args.subject_id,
            session_id=session.session_id,
            document=document,
            token=token,
        )
        verified_documents.append(
            upsert_and_read(
                project_id=args.project_id,
                database_id=args.database_id,
                subject_id=args.subject_id,
                session_id=session.session_id,
                document=document,
                token=token,
            )
        )

    expected_ids = {session.session_id for session in curated}
    verified_ids = {
        document.get("fields", {}).get("session_id", {}).get("stringValue")
        for document in verified_documents
    }
    zone_counts = [stored_zone_count(document) for document in verified_documents]
    success = expected_ids == verified_ids and len(verified_documents) == len(curated) and all(zone_counts)
    print(json.dumps({
        "status": "CLOUD_SMOKE_TEST_PASSED" if success else "CLOUD_SMOKE_TEST_FAILED",
        "project_id": args.project_id,
        "database_id": args.database_id,
        "collection": "athletes/{authenticated_subject_id}/sessions/{session_id}",
        "records_expected": len(curated),
        "records_verified_after_idempotent_retries": len(verified_documents),
        "records_with_zone_periods": sum(count > 0 for count in zone_counts),
        "zone_periods_verified": sum(zone_counts),
        "zone_duration_quality": {
            "complete": sum(session.heart_rate_zone_duration_quality == "complete" for session in curated),
            "partial": sum(session.heart_rate_zone_duration_quality == "partial" for session in curated),
            "unavailable": sum(session.heart_rate_zone_duration_quality == "unavailable" for session in curated),
        },
        "raw_polar_payload_stored": False,
        "service_account_key_created": False,
    }, ensure_ascii=False, indent=2))
    return 0 if success else 4


if __name__ == "__main__":
    raise SystemExit(main())
