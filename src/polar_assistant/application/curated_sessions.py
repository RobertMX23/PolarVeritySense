"""Contract and deterministic query boundary for curated sports sessions.

This module is deliberately independent of the Polar HTTP client and Google
SDKs.  It accepts a whitelisted projection of a Dynamic API v4 response and
emits the small record that a data store and the ADK agent are allowed to use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Protocol
from uuid import NAMESPACE_URL, uuid5

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


CURATED_SESSION_SCHEMA_VERSION = "1.0"
CURATED_DYNAMIC_FIELDS = (
    "identifier.id",
    "startTime",
    "durationMillis",
    "sport.id",
    "hrAvg",
    "hrMax",
    "trainingLoad",
    "distanceMeters",
    "calories",
    "created",
    "modified",
)


class PolarIdentifier(BaseModel):
    """Only the opaque identifier supplied by Polar is required."""

    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=200)


class PolarSportReference(BaseModel):
    """Dynamic API v4 exposes a sport reference, not necessarily a display name."""

    model_config = ConfigDict(extra="ignore")
    id: str | None = Field(default=None, max_length=200)


class PolarDynamicTrainingSession(BaseModel):
    """Allowlisted projection of one `/v4/data/training-sessions/list` item.

    ``extra=ignore`` is intentional: location, free-form note, physical profile,
    samples and other provider additions are discarded at the boundary.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    identifier: PolarIdentifier
    start_time: datetime = Field(validation_alias=AliasChoices("startTime", "start_time"))
    duration_millis: int = Field(
        ge=1,
        validation_alias=AliasChoices("durationMillis", "duration_millis"),
    )
    sport: PolarSportReference = Field(default_factory=PolarSportReference)
    heart_rate_average_bpm: int | None = Field(
        default=None,
        ge=30,
        le=240,
        validation_alias=AliasChoices("hrAvg", "heart_rate_average_bpm"),
    )
    heart_rate_maximum_bpm: int | None = Field(
        default=None,
        ge=30,
        le=240,
        validation_alias=AliasChoices("hrMax", "heart_rate_maximum_bpm"),
    )
    training_load: float | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("trainingLoad", "training_load"),
    )
    distance_meters: float | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("distanceMeters", "distance_meters"),
    )
    calories: int | None = Field(default=None, ge=0)
    source_created_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("created", "source_created_at"),
    )
    source_modified_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("modified", "source_modified_at"),
    )


class CuratedTrainingSession(BaseModel):
    """Storage and agent-safe record for one subject and one training session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(pattern=r"^ses_[0-9a-f]{32}$")
    subject_id: str = Field(pattern=r"^ath_[A-Za-z0-9_-]{8,128}$")
    provider: Literal["polar_accesslink_v4"] = "polar_accesslink_v4"
    provider_session_id: str = Field(min_length=1, max_length=200)
    started_at: datetime
    duration_seconds: int = Field(gt=0)
    sport_reference_id: str | None = Field(default=None, max_length=200)
    heart_rate_average_bpm: int | None = Field(default=None, ge=30, le=240)
    heart_rate_maximum_bpm: int | None = Field(default=None, ge=30, le=240)
    training_load: float | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    calories: int | None = Field(default=None, ge=0)
    source_created_at: datetime | None = None
    source_modified_at: datetime | None = None
    ingested_at: datetime
    data_quality: Literal["validated", "summary_only"]
    schema_version: Literal["1.0"] = CURATED_SESSION_SCHEMA_VERSION

    def firestore_document(self) -> dict[str, Any]:
        """Return a serializable document without tokens or raw provider JSON."""
        return self.model_dump(mode="json")

    def bigquery_row(self) -> dict[str, Any]:
        """Return an explicit table row with the same privacy-minimized fields."""
        return self.model_dump(mode="json")


class CuratedSessionRepository(Protocol):
    """Port used by the deterministic tool; implementations own authorization."""

    def upsert(self, session: CuratedTrainingSession) -> None: ...

    def latest_for_subject(self, subject_id: str) -> CuratedTrainingSession | None: ...

    def list_for_subject(self, subject_id: str, *, limit: int) -> list[CuratedTrainingSession]: ...


def curated_session_id(*, subject_id: str, provider_session_id: str) -> str:
    """Create a stable opaque ID, enabling idempotent sync retries."""
    value = f"polar-accesslink-v4/{subject_id}/{provider_session_id}"
    return f"ses_{uuid5(NAMESPACE_URL, value).hex}"


def curate_dynamic_training_session(
    *,
    subject_id: str,
    payload: dict[str, Any],
    ingested_at: datetime | None = None,
) -> CuratedTrainingSession:
    """Validate a v4 item and produce the only record persisted for the agent.

    The caller passes one item in ``trainingSessions``. A malformed or
    insufficient session fails before any persistence operation.
    """
    dynamic = PolarDynamicTrainingSession.model_validate(payload)
    received_at = ingested_at or datetime.now(timezone.utc)
    return CuratedTrainingSession(
        session_id=curated_session_id(
            subject_id=subject_id,
            provider_session_id=dynamic.identifier.id,
        ),
        subject_id=subject_id,
        provider_session_id=dynamic.identifier.id,
        started_at=dynamic.start_time,
        duration_seconds=round(dynamic.duration_millis / 1000),
        sport_reference_id=dynamic.sport.id,
        heart_rate_average_bpm=dynamic.heart_rate_average_bpm,
        heart_rate_maximum_bpm=dynamic.heart_rate_maximum_bpm,
        training_load=dynamic.training_load,
        distance_meters=dynamic.distance_meters,
        calories=dynamic.calories,
        source_created_at=dynamic.source_created_at,
        source_modified_at=dynamic.source_modified_at,
        ingested_at=received_at,
        data_quality=(
            "validated"
            if dynamic.heart_rate_average_bpm is not None
            and dynamic.heart_rate_maximum_bpm is not None
            else "summary_only"
        ),
    )


class CuratedSessionQueryService:
    """A narrow lookup service: it accepts an authenticated subject, never SQL."""

    def __init__(self, repository: CuratedSessionRepository) -> None:
        self._repository = repository

    def latest_for_authenticated_subject(self, subject_id: str) -> dict[str, Any]:
        record = self._repository.latest_for_subject(subject_id)
        if record is None:
            return {"status": "NO_CURATED_SESSION"}
        return {
            "status": "FOUND",
            "session": record.model_dump(mode="json", exclude={"subject_id"}),
        }
