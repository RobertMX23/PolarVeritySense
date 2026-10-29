from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from polar_assistant.application.curated_sessions import (
    CuratedSessionQueryService,
    curate_accesslink_v3_exercise,
    curate_dynamic_training_session,
)
from polar_assistant.infrastructure.curated_session_store import InMemoryCuratedSessionRepository
from sport_assistant_agent.curated_data_tools import build_latest_curated_session_tool


SUBJECT_ID = "ath_demo_subject_2026"


def dynamic_payload(session_id="polar-session-42", start_time="2026-10-29T08:30:00Z"):
    return {
        "identifier": {"id": session_id},
        "startTime": start_time,
        "durationMillis": 2400000,
        "sport": {"id": "treadmill-running"},
        "hrAvg": 141,
        "hrMax": 164,
        "trainingLoad": 121.5,
        "distanceMeters": 5000,
        "calories": 380,
        "note": "This free text must never be persisted.",
        "latitude": 19.4326,
        "physicalInformation": {"birthday": "1990-01-01"},
        "samples": [{"heartRate": 141}],
        "exercises": [{
            "zones": [{
                "type": "ZONE_TYPE_HEART_RATE",
                "zones": [
                    {"lowerLimit": 110, "higherLimit": 128, "inZone": 480000},
                    {"lowerLimit": 128, "higherLimit": 146, "inZone": 1320000},
                    {"lowerLimit": 146, "higherLimit": 165, "inZone": 600000},
                ],
            }],
        }],
    }


def test_curates_only_the_allowed_dynamic_api_fields_and_generates_stable_id():
    record = curate_dynamic_training_session(
        subject_id=SUBJECT_ID,
        payload=dynamic_payload(),
        ingested_at=datetime(2026, 10, 29, 9, tzinfo=timezone.utc),
    )

    retry = curate_dynamic_training_session(subject_id=SUBJECT_ID, payload=dynamic_payload())
    assert record.session_id.startswith("ses_")
    assert record.session_id == retry.session_id
    assert record.duration_seconds == 2400
    assert record.data_quality == "validated"
    assert [(zone.lower_limit, zone.higher_limit, zone.duration_seconds) for zone in record.zone_periods] == [
        (110, 128, 480), (128, 146, 1320), (146, 165, 600),
    ]
    assert record.heart_rate_zone_duration_seconds == 2400
    assert record.heart_rate_zone_duration_quality == "complete"
    document = record.firestore_document()
    assert set(document) == {
        "session_id", "subject_id", "provider", "provider_session_id", "started_at",
        "duration_seconds", "sport_reference_id", "heart_rate_average_bpm",
        "heart_rate_maximum_bpm", "training_load", "distance_meters", "calories",
            "source_created_at", "source_modified_at", "ingested_at", "data_quality",
            "zone_periods", "heart_rate_zone_duration_seconds",
            "heart_rate_zone_coverage_percent", "heart_rate_zone_duration_quality",
            "schema_version",
    }
    assert "note" not in document
    assert "samples" not in document
    assert "physicalInformation" not in document


def test_rejects_invalid_provider_values_before_persistence():
    payload = dynamic_payload()
    payload["durationMillis"] = 0

    with pytest.raises(ValidationError):
        curate_dynamic_training_session(subject_id=SUBJECT_ID, payload=payload)


def test_curates_current_accesslink_v3_zones_without_turning_unknown_time_into_zero():
    record = curate_accesslink_v3_exercise(subject_id=SUBJECT_ID, payload={
        "id": "v3-session-42",
        "start_time": "2026-10-29T08:30:00Z",
        "duration": "PT40M",
        "sport": "TREADMILL_RUNNING",
        "heart_rate": {"average": 141, "maximum": 164},
        "heart_rate_zones": [
            {"index": 2, "lower_limit": 128, "upper_limit": 146, "in_zone": "PT22M"},
            {"index": 3, "lower_limit": 146, "upper_limit": 165, "in_zone": None},
        ],
    })

    assert record.provider == "polar_accesslink_v3"
    assert [(zone.zone_index, zone.duration_seconds) for zone in record.zone_periods] == [(2, 1320), (3, None)]
    assert record.heart_rate_zone_coverage_percent == 55.0
    assert record.heart_rate_zone_duration_quality == "partial"


def test_query_service_is_scoped_to_the_authenticated_subject_and_returns_latest():
    repository = InMemoryCuratedSessionRepository()
    repository.upsert(curate_dynamic_training_session(
        subject_id=SUBJECT_ID,
        payload=dynamic_payload("older", "2026-10-28T08:30:00Z"),
    ))
    repository.upsert(curate_dynamic_training_session(
        subject_id=SUBJECT_ID,
        payload=dynamic_payload("newer", "2026-10-29T08:30:00Z"),
    ))
    repository.upsert(curate_dynamic_training_session(
        subject_id="ath_another_subject_2026",
        payload=dynamic_payload("other", "2026-10-30T08:30:00Z"),
    ))

    result = CuratedSessionQueryService(repository).latest_for_authenticated_subject(SUBJECT_ID)

    assert result["status"] == "FOUND"
    assert result["session"]["provider_session_id"] == "newer"
    assert "subject_id" not in result["session"]


def test_adk_tool_requires_subject_from_authenticated_state():
    service = CuratedSessionQueryService(InMemoryCuratedSessionRepository())
    tool = build_latest_curated_session_tool(service)

    class Context:
        state = {}

    assert tool(Context()) == {"status": "AUTHENTICATED_SUBJECT_REQUIRED"}
