"""Verify the current authorized v3 data can be curated and saved idempotently.

The repository is intentionally in memory. It proves the transformation and
upsert contract before personal data are written to Firestore or BigQuery.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from polar_assistant.application.curated_sessions import curate_accesslink_v3_exercise
from polar_assistant.infrastructure.curated_session_store import InMemoryCuratedSessionRepository
from scripts.polar_v3_inventory import fetch_exercises


def main() -> int:
    token = str(dotenv_values(ROOT / ".env").get("POLAR_ACCESSLINK_ACCESS_TOKEN") or "")
    if not token:
        print("Falta POLAR_ACCESSLINK_ACCESS_TOKEN en .env; no se hizo ninguna llamada.")
        return 2
    exercises = fetch_exercises(token)
    repository = InMemoryCuratedSessionRepository()
    curated = [
        curate_accesslink_v3_exercise(subject_id="ath_local_smoke_2026", payload=exercise)
        for exercise in exercises
    ]
    for record in curated:
        repository.upsert(record)
        repository.upsert(record)
    saved = repository.list_for_subject("ath_local_smoke_2026", limit=max(1, len(curated)))
    expected_ids = {record.session_id for record in curated}
    status = "LOCAL_SMOKE_TEST_PASSED" if {record.session_id for record in saved} == expected_ids else "LOCAL_SMOKE_TEST_FAILED"
    print(json.dumps({
        "status": status,
        "source": "polar_accesslink_v3",
        "records_curated": len(curated),
        "records_saved_after_idempotent_retries": len(saved),
        "records_with_zone_periods": sum(bool(record.zone_periods) for record in saved),
        "records_with_complete_heart_rate_zone_duration": sum(
            record.heart_rate_zone_duration_quality == "complete" for record in saved
        ),
        "records_with_partial_heart_rate_zone_duration": sum(
            record.heart_rate_zone_duration_quality == "partial" for record in saved
        ),
        "persistence": "in_memory_contract_test_only",
        "sessions": [
            {
                "day": record.started_at.date().isoformat(),
                "provider_session_id": record.provider_session_id,
                "sport": record.sport_reference_id,
                "duration_seconds": record.duration_seconds,
                "heart_rate_average_bpm": record.heart_rate_average_bpm,
                "heart_rate_maximum_bpm": record.heart_rate_maximum_bpm,
                "heart_rate_zone_coverage_percent": record.heart_rate_zone_coverage_percent,
                "heart_rate_zone_duration_quality": record.heart_rate_zone_duration_quality,
                "zone_periods": [
                    {
                        "index": zone.zone_index,
                        "lower_limit": zone.lower_limit,
                        "higher_limit": zone.higher_limit,
                        "duration_seconds": zone.duration_seconds,
                    }
                    for zone in record.zone_periods
                ],
            }
            for record in saved
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if status.endswith("PASSED") else 4


if __name__ == "__main__":
    raise SystemExit(main())
