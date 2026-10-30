"""Contract and deterministic query boundary for curated sports sessions.

This module is deliberately independent of the Polar HTTP client and Google
SDKs.  It accepts a whitelisted projection of a Dynamic API v4 response and
emits the small record that a data store and the ADK agent are allowed to use.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
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
    "exercises[].zones[].type",
    "exercises[].zones[].zones[].lowerLimit",
    "exercises[].zones[].zones[].higherLimit",
    "exercises[].zones[].zones[].inZone",
    "exercises[].zones[].zones[].distanceMeters",
    "exercises[].zones[].zones[].muscleLoad",
)


class PolarIdentifier(BaseModel):
    """Only the opaque identifier supplied by Polar is required."""

    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=200)


class PolarSportReference(BaseModel):
    """Dynamic API v4 exposes a sport reference, not necessarily a display name."""

    model_config = ConfigDict(extra="ignore")
    id: str | None = Field(default=None, max_length=200)


class PolarZone(BaseModel):
    """One aggregate period in a Dynamic API zone."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    lower_limit: float = Field(validation_alias=AliasChoices("lowerLimit", "lower_limit"))
    higher_limit: float = Field(validation_alias=AliasChoices("higherLimit", "higher_limit"))
    in_zone_millis: int = Field(
        ge=0,
        validation_alias=AliasChoices("inZone", "in_zone_millis"),
    )
    distance_meters: float | None = Field(
        default=None, ge=0, validation_alias=AliasChoices("distanceMeters", "distance_meters")
    )
    muscle_load: float | None = Field(
        default=None, ge=0, validation_alias=AliasChoices("muscleLoad", "muscle_load")
    )


class PolarZoneGroup(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    zone_type: str = Field(validation_alias=AliasChoices("type", "zone_type"), min_length=1)
    zones: list[PolarZone] = Field(default_factory=list)


class PolarExerciseProjection(BaseModel):
    """The zones feature is nested under a training session's exercises."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    zones: list[PolarZoneGroup] = Field(default_factory=list)


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
    exercises: list[PolarExerciseProjection] = Field(default_factory=list)


class CuratedZonePeriod(BaseModel):
    """A zone's bounds and aggregate time; it is not a raw sample sequence."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    zone_type: str = Field(min_length=1, max_length=80)
    zone_index: int | None = Field(default=None, ge=0)
    lower_limit: float | None = None
    higher_limit: float | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    muscle_load: float | None = Field(default=None, ge=0)


class CuratedTrainingSession(BaseModel):
    """Storage and agent-safe record for one subject and one training session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(pattern=r"^ses_[0-9a-f]{32}$")
    subject_id: str = Field(pattern=r"^ath_[A-Za-z0-9_-]{8,128}$")
    provider: Literal["polar_accesslink_v3", "polar_accesslink_v4"] = "polar_accesslink_v4"
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
    zone_periods: tuple[CuratedZonePeriod, ...] = Field(default_factory=tuple)
    heart_rate_zone_duration_seconds: int = Field(ge=0)
    heart_rate_zone_coverage_percent: float = Field(ge=0, le=100)
    heart_rate_zone_duration_quality: Literal["complete", "partial", "unavailable"]
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
    zone_periods = tuple(
        CuratedZonePeriod(
            zone_type=group.zone_type,
            zone_index=None,
            lower_limit=zone.lower_limit,
            higher_limit=zone.higher_limit,
            duration_seconds=round(zone.in_zone_millis / 1000),
            distance_meters=zone.distance_meters,
            muscle_load=zone.muscle_load,
        )
        for exercise in dynamic.exercises
        for group in exercise.zones
        for zone in group.zones
    )
    duration_seconds = round(dynamic.duration_millis / 1000)
    zone_metadata = _heart_rate_zone_metadata(zone_periods, duration_seconds)
    return CuratedTrainingSession(
        session_id=curated_session_id(
            subject_id=subject_id,
            provider_session_id=dynamic.identifier.id,
        ),
        subject_id=subject_id,
        provider_session_id=dynamic.identifier.id,
        started_at=dynamic.start_time,
        duration_seconds=duration_seconds,
        sport_reference_id=dynamic.sport.id,
        heart_rate_average_bpm=dynamic.heart_rate_average_bpm,
        heart_rate_maximum_bpm=dynamic.heart_rate_maximum_bpm,
        training_load=dynamic.training_load,
        distance_meters=dynamic.distance_meters,
        calories=dynamic.calories,
        source_created_at=dynamic.source_created_at,
        source_modified_at=dynamic.source_modified_at,
        zone_periods=zone_periods,
        **zone_metadata,
        ingested_at=received_at,
        data_quality=(
            "validated"
            if dynamic.heart_rate_average_bpm is not None
            and dynamic.heart_rate_maximum_bpm is not None
            else "summary_only"
        ),
    )


def _v3_duration_seconds(value: Any) -> int | None:
    if not value:
        return None
    total = 0.0
    for number, unit in re.findall(r"([0-9.]+)([HMS])", str(value)):
        total += float(number) * {"H": 3600, "M": 60, "S": 1}[unit]
    return round(total) if total else None


def _heart_rate_zone_metadata(
    zone_periods: tuple[CuratedZonePeriod, ...], duration_seconds: int,
) -> dict[str, Any]:
    heart_rate_zones = [zone for zone in zone_periods if zone.zone_type == "ZONE_TYPE_HEART_RATE"]
    known_seconds = sum(zone.duration_seconds or 0 for zone in heart_rate_zones)
    coverage = round((known_seconds / duration_seconds) * 100, 2) if duration_seconds else 0.0
    quality = (
        "unavailable" if not heart_rate_zones else
        "complete" if coverage >= 98 else
        "partial"
    )
    return {
        "heart_rate_zone_duration_seconds": known_seconds,
        "heart_rate_zone_coverage_percent": coverage,
        "heart_rate_zone_duration_quality": quality,
    }


def curate_accesslink_v3_exercise(
    *,
    subject_id: str,
    payload: dict[str, Any],
    ingested_at: datetime | None = None,
) -> CuratedTrainingSession:
    """Normalize the existing v3 exercise payload into the curated contract.

    It exists to migrate the already authorized AccessLink source. New OAuth
    integrations use ``curate_dynamic_training_session`` for Dynamic API v4.
    Unknown v3 zone durations stay ``None`` instead of being changed to zero.
    """
    provider_session_id = str(payload.get("id") or "")
    start_time = payload.get("start_time")
    duration_seconds = _v3_duration_seconds(payload.get("duration"))
    if not provider_session_id or not start_time or duration_seconds is None:
        raise ValueError("El ejercicio v3 no tiene id, inicio o duración válidos.")
    heart_rate = payload.get("heart_rate") or {}
    zones = payload.get("heart_rate_zones") or []
    if not isinstance(heart_rate, dict) or not isinstance(zones, list):
        raise ValueError("El ejercicio v3 tiene un formato de frecuencia cardiaca inválido.")
    zone_periods = tuple(
        CuratedZonePeriod(
            zone_type="ZONE_TYPE_HEART_RATE",
            zone_index=item.get("index"),
            lower_limit=item.get("lower_limit"),
            higher_limit=item.get("upper_limit"),
            duration_seconds=_v3_duration_seconds(item.get("in_zone")),
        )
        for item in zones
        if isinstance(item, dict)
    )
    return CuratedTrainingSession(
        session_id=curated_session_id(subject_id=subject_id, provider_session_id=provider_session_id),
        subject_id=subject_id,
        provider="polar_accesslink_v3",
        provider_session_id=provider_session_id,
        started_at=start_time,
        duration_seconds=duration_seconds,
        sport_reference_id=str(payload.get("detailed_sport_info") or payload.get("sport") or "") or None,
        heart_rate_average_bpm=heart_rate.get("average"),
        heart_rate_maximum_bpm=heart_rate.get("maximum"),
        source_created_at=None,
        source_modified_at=None,
        zone_periods=zone_periods,
        **_heart_rate_zone_metadata(zone_periods, duration_seconds),
        ingested_at=ingested_at or datetime.now(timezone.utc),
        data_quality=(
            "validated"
            if heart_rate.get("average") is not None and heart_rate.get("maximum") is not None
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

    def list_for_authenticated_subject(self, subject_id: str, *, limit: int = 5) -> dict[str, Any]:
        """Return a bounded history without exposing the internal subject id."""
        records = self._repository.list_for_subject(subject_id, limit=limit)
        return {
            "status": "FOUND" if records else "NO_CURATED_SESSION",
            "sessions": [record.model_dump(mode="json", exclude={"subject_id"}) for record in records],
        }

    def session_for_authenticated_subject(self, subject_id: str, *, session_id: str) -> dict[str, Any]:
        """Find one curated record only inside the authenticated subject's scope."""
        records = self._repository.list_for_subject(subject_id, limit=100)
        record = next((item for item in records if item.session_id == session_id), None)
        if record is None:
            return {"status": "NO_CURATED_SESSION"}
        return {
            "status": "FOUND",
            "session": record.model_dump(mode="json", exclude={"subject_id"}),
        }
