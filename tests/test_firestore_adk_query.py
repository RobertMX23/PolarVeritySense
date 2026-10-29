from datetime import datetime, timezone

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from polar_assistant.application.curated_sessions import CuratedSessionQueryService, curate_dynamic_training_session
from polar_assistant.infrastructure.curated_session_store import InMemoryCuratedSessionRepository
from sport_assistant_agent.agent import build_workflow


def _record(provider_session_id: str, started_at: str):
    return curate_dynamic_training_session(
        subject_id="ath_local_smoke_2026",
        payload={
            "identifier": {"id": provider_session_id},
            "startTime": started_at,
            "durationMillis": 1800000,
            "sport": {"id": "TREADMILL_RUNNING"},
            "hrAvg": 138,
            "hrMax": 161,
            "exercises": [{"zones": [{"type": "ZONE_TYPE_HEART_RATE", "zones": [
                {"lowerLimit": 110, "higherLimit": 130, "inZone": 600000},
            ]}]}],
        },
        ingested_at=datetime(2026, 10, 29, tzinfo=timezone.utc),
    )


def _texts(events):
    return [
        "".join(part.text or "" for part in event.content.parts or [])
        for event in events
        if event.content and event.content.parts
    ]


def test_iap_bound_agent_reads_firestore_history_without_model_call(monkeypatch):
    monkeypatch.setenv("FIRESTORE_QA_SUBJECT_ID", "ath_local_smoke_2026")
    repository = InMemoryCuratedSessionRepository()
    repository.upsert(_record("older", "2026-10-28T08:30:00Z"))
    repository.upsert(_record("newer", "2026-10-29T08:30:00Z"))
    agent = build_workflow(
        gateway=object(),
        curated_session_query=CuratedSessionQueryService(repository),
    )
    service = InMemorySessionService()
    service.create_session_sync(app_name="firestore_adk", user_id="iap_" + "a" * 64, session_id="s1")
    runner = Runner(app_name="firestore_adk", agent=agent, session_service=service)

    list(runner.run(
        user_id="iap_" + "a" * 64,
        session_id="s1",
        new_message=types.Content(role="user", parts=[types.Part(text="hola")]),
    ))
    latest = list(runner.run(
        user_id="iap_" + "a" * 64,
        session_id="s1",
        new_message=types.Content(role="user", parts=[types.Part(text="1")]),
    ))
    history = list(runner.run(
        user_id="iap_" + "a" * 64,
        session_id="s1",
        new_message=types.Content(role="user", parts=[types.Part(text="mi histórico de sesiones")]),
    ))

    assert any("Firestore curado de QA" in text and "TREADMILL_RUNNING" in text for text in _texts(latest))
    assert any("Histórico de sesiones curadas de QA" in text and "2026-10-29" in text for text in _texts(history))
