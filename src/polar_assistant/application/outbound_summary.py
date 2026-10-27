"""Versioned, privacy-minimized Python -> Gemini contract (no network calls)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Seconds = Annotated[float, Field(ge=0)]
Bpm = Annotated[float, Field(ge=30, le=240)]
ShortText = Annotated[str, Field(max_length=80)]


class SummaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class HeartRateZone(SummaryModel):
    index: int = Field(ge=0, le=4)
    lower_limit_bpm: float | None = Field(default=None, ge=0, le=300)
    upper_limit_bpm: float | None = Field(default=None, ge=0, le=300)
    duration_seconds: Seconds

    @model_validator(mode="after")
    def ordered_limits(self):
        if (self.lower_limit_bpm is not None and self.upper_limit_bpm is not None
                and self.lower_limit_bpm >= self.upper_limit_bpm):
            raise ValueError("ZONE_LIMIT_ORDER")
        return self


class HeartRateZones(SummaryModel):
    zone_0: HeartRateZone | None
    zone_1: HeartRateZone | None
    zone_2: HeartRateZone | None
    zone_3: HeartRateZone | None
    zone_4: HeartRateZone | None

    @model_validator(mode="after")
    def matching_indices(self):
        for index in range(5):
            zone = getattr(self, f"zone_{index}")
            if zone is not None and zone.index != index:
                raise ValueError("ZONE_KEY_INDEX_MISMATCH")
        return self

    def available(self) -> list[HeartRateZone]:
        return [zone for index in range(5) if (zone := getattr(self, f"zone_{index}")) is not None]


class SummaryMetrics(SummaryModel):
    duration_seconds: Seconds | None
    mean_hr_bpm: Bpm | None
    min_hr_bpm: Bpm | None
    max_hr_bpm: Bpm | None
    heart_rate_zones: HeartRateZones
    zone_limits_source: Literal["polar_accesslink", "demo_configuration", "unknown"]
    zone_duration_method: Literal["provider_duration", "sample_count_assuming_1hz", "unknown"]
    cardiac_drift_pct: float | None
    fatigue_signal: bool
    data_quality: Literal["HIGH", "SUMMARY_ONLY"]
    critical_safety_flag: bool = False

    @model_validator(mode="after")
    def coherent_metrics(self):
        values = [v for v in (self.min_hr_bpm, self.mean_hr_bpm, self.max_hr_bpm) if v is not None]
        if values != sorted(values):
            raise ValueError("HEART_RATE_ORDER")
        zones = self.heart_rate_zones.available()
        if len({z.index for z in zones}) != len(zones):
            raise ValueError("DUPLICATE_ZONE_INDEX")
        bounded = sorted((z for z in zones if z.lower_limit_bpm is not None
                          and z.upper_limit_bpm is not None), key=lambda z: z.lower_limit_bpm)
        if any(a.upper_limit_bpm > b.lower_limit_bpm for a, b in zip(bounded, bounded[1:])):
            raise ValueError("OVERLAPPING_ZONES")
        # FIT's legacy sample count includes both endpoints of a 1 Hz interval.
        tolerance = 1 if self.zone_duration_method == "sample_count_assuming_1hz" else 0
        if self.duration_seconds is not None and sum(z.duration_seconds for z in zones) > self.duration_seconds + tolerance:
            raise ValueError("ZONE_TIME_EXCEEDS_SESSION")
        return self


class SummaryComparison(SummaryModel):
    reference_sport: ShortText | None
    candidate_sport: ShortText | None
    duration_delta_seconds: float | None
    average_hr_delta_bpm: float | None
    comparable_for_load_trend: bool
    comparison_warnings: list[Annotated[str, Field(max_length=240)]] = Field(max_length=8)
    data_quality: ShortText


class OutboundSummary(SummaryModel):
    schema_version: Literal["1.1"] = "1.1"
    source: Literal["local_real_fit", "polar_accesslink", "unknown"]
    metrics: SummaryMetrics
    comparison: SummaryComparison
    user_context: str = Field(max_length=1200)
    interpretation_limit: Literal["La deriva es descriptiva; faltan controles de carga y contexto."]
