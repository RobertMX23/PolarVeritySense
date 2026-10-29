from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from polar_assistant.application.curated_sessions import curate_dynamic_training_session
from polar_assistant.infrastructure.curated_session_store import FirestoreCuratedSessionRepository


SUBJECT_A = "ath_firestore_subject_a"
SUBJECT_B = "ath_firestore_subject_b"


def payload(session_id: str, started_at: str) -> dict:
    return {
        "identifier": {"id": session_id},
        "startTime": started_at,
        "durationMillis": 600000,
        "sport": {"id": "treadmill-running"},
        "hrAvg": 120,
        "hrMax": 150,
        "exercises": [{"zones": [{"type": "ZONE_TYPE_HEART_RATE", "zones": [
            {"lowerLimit": 110, "higherLimit": 130, "inZone": 600000},
        ]}]}],
    }


def document(subject_id: str, session_id: str, started_at: str) -> dict:
    return curate_dynamic_training_session(
        subject_id=subject_id,
        payload=payload(session_id, started_at),
        ingested_at=datetime(2026, 10, 29, 9, tzinfo=timezone.utc),
    ).firestore_document()


class FakeFirestoreDocumentClient:
    def __init__(self, documents_by_subject: dict[str, list[dict]]) -> None:
        self.documents_by_subject = documents_by_subject
        self.calls: list[tuple[str, int]] = []

    def list_session_documents(self, *, subject_id: str, limit: int) -> list[dict]:
        self.calls.append((subject_id, limit))
        return sorted(
            self.documents_by_subject.get(subject_id, []),
            key=lambda item: item.get("started_at", ""),
            reverse=True,
        )[:limit]


def test_reads_the_latest_session_in_descending_order_and_forwards_limit():
    client = FakeFirestoreDocumentClient({
        SUBJECT_A: [
            document(SUBJECT_A, "older", "2026-10-28T08:30:00Z"),
            document(SUBJECT_A, "newer", "2026-10-29T08:30:00Z"),
        ],
    })
    repository = FirestoreCuratedSessionRepository(client)

    sessions = repository.list_for_subject(SUBJECT_A, limit=2)

    assert client.calls == [(SUBJECT_A, 2)]
    assert [session.provider_session_id for session in sessions] == ["newer", "older"]
    assert repository.latest_for_subject(SUBJECT_A).provider_session_id == "newer"
    assert client.calls[-1] == (SUBJECT_A, 1)


def test_returns_an_empty_list_for_a_subject_without_documents():
    repository = FirestoreCuratedSessionRepository(FakeFirestoreDocumentClient({}))

    assert repository.list_for_subject(SUBJECT_A, limit=1) == []
    assert repository.latest_for_subject(SUBJECT_A) is None


def test_rejects_a_document_returned_for_another_subject():
    client = FakeFirestoreDocumentClient({
        SUBJECT_A: [document(SUBJECT_B, "other", "2026-10-29T08:30:00Z")],
    })

    with pytest.raises(ValueError, match="otro sujeto"):
        FirestoreCuratedSessionRepository(client).list_for_subject(SUBJECT_A, limit=1)


def test_rejects_invalid_curated_documents_and_non_positive_limits():
    client = FakeFirestoreDocumentClient({SUBJECT_A: [{"session_id": "not-a-curated-record"}]})
    repository = FirestoreCuratedSessionRepository(client)

    with pytest.raises(ValidationError):
        repository.list_for_subject(SUBJECT_A, limit=1)
    with pytest.raises(ValueError, match="al menos 1"):
        repository.list_for_subject(SUBJECT_A, limit=0)
