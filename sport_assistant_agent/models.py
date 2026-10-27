from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AccessLinkExerciseSummary(BaseModel):
    """Contrato mínimo y tolerante para una sesión real de AccessLink."""

    exercise_id: str
    start_time: str
    upload_time: str | None = None
    device: str | None = None
    sport: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    heart_rate_average: float | None = Field(default=None, ge=0, le=240)
    heart_rate_maximum: float | None = Field(default=None, ge=0, le=240)
    heart_rate_zones: list[dict[str, Any]] = Field(default_factory=list)
    sample_count: int = Field(default=0, ge=0)
    source: str = "polar_accesslink"

