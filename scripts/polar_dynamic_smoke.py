"""Read-only Polar Dynamic API smoke test with local in-memory persistence.

It prints a minimized list of days and verifies that records, including zone
periods, survive an idempotent upsert in the curated repository. It never logs
tokens, raw samples, notes, coordinates or the full provider payload.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from polar_assistant.application.curated_sessions import curate_dynamic_training_session
from polar_assistant.infrastructure.curated_session_store import InMemoryCuratedSessionRepository
from polar_assistant.infrastructure.polar_dynamic import PolarDynamicApiClient, PolarDynamicApiError


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def zone_summary(record) -> list[dict[str, object]]:
    return [
        {
            "type": zone.zone_type,
            "lower": zone.lower_limit,
            "upper": zone.higher_limit,
            "seconds": zone.duration_seconds,
        }
        for zone in record.zone_periods
    ]


def main() -> int:
    today = datetime.now(timezone.utc).date()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="from_date", type=parse_date, default=today - timedelta(days=90))
    parser.add_argument("--to", dest="to_date", type=parse_date, default=today + timedelta(days=1))
    parser.add_argument("--subject-id", default="ath_local_smoke_2026")
    args = parser.parse_args()
    if args.from_date >= args.to_date:
        parser.error("--from debe ser anterior a --to")

    load_dotenv(ROOT / ".env")
    token = os.getenv("POLAR_ACCESSLINK_ACCESS_TOKEN")
    if not token:
        raise SystemExit("Falta POLAR_ACCESSLINK_ACCESS_TOKEN en .env; no se hizo ninguna llamada.")

    client = PolarDynamicApiClient(token)
    try:
        headers = client.list_training_sessions(from_date=args.from_date, to_date=args.to_date)
        available_days = sorted({str(item.get("startTime", ""))[:10] for item in headers if item.get("startTime")})
        sessions: list[dict] = []
        for day_text in available_days:
            day = date.fromisoformat(day_text)
            sessions.extend(client.list_training_sessions(
                from_date=day,
                to_date=day + timedelta(days=1),
                include_zones=True,
            ))
    except PolarDynamicApiError as error:
        raise SystemExit(f"SMOKE_TEST_FAILED: {error}") from error

    repository = InMemoryCuratedSessionRepository()
    curated = [
        curate_dynamic_training_session(subject_id=args.subject_id, payload=session)
        for session in sessions
    ]
    for record in curated:
        repository.upsert(record)
        repository.upsert(record)  # proves an idempotent retry does not duplicate it

    saved = repository.list_for_subject(args.subject_id, limit=max(1, len(curated)))
    if len(saved) != len({record.session_id for record in curated}):
        raise SystemExit("SMOKE_TEST_FAILED: el repositorio no conservó el número esperado de sesiones.")
    if any(not record.zone_periods for record in curated):
        raise SystemExit("SMOKE_TEST_FAILED: Polar devolvió una sesión sin zonas en la consulta con features=zones.")

    print(json.dumps({
        "status": "SMOKE_TEST_PASSED",
        "available_days": available_days,
        "sessions_seen": len(headers),
        "sessions_curated": len(curated),
        "sessions_saved": len(saved),
        "sessions": [
            {
                "day": record.started_at.date().isoformat(),
                "session_id": record.session_id,
                "sport_reference_id": record.sport_reference_id,
                "duration_seconds": record.duration_seconds,
                "heart_rate_average_bpm": record.heart_rate_average_bpm,
                "heart_rate_maximum_bpm": record.heart_rate_maximum_bpm,
                "zone_periods": zone_summary(record),
            }
            for record in saved
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
