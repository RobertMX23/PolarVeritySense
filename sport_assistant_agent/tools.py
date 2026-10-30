from __future__ import annotations
import json
import os
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from google.adk.tools import ToolContext
from pydantic import BaseModel, Field, field_validator
from .accesslink import fetch_accesslink_session

class TreadmillContext(BaseModel):
    speed_kmh: float = Field(ge=0)
    incline_percent: float = Field(ge=0)

class HeartRate(BaseModel):
    average: float = Field(ge=30, le=240)
    maximum: float = Field(ge=30, le=240)
    resting_baseline: float = Field(ge=30, le=240)
    first_half_avg_hr: float = Field(ge=30, le=240)
    second_half_avg_hr: float = Field(ge=30, le=240)

class OpticalPpiStats(BaseModel):
    avg_ppi_ms: float = Field(gt=0)
    rmssd_recovery_index: float = Field(gt=0)
    sensor_contact_quality: str

class PolarTelemetry(BaseModel):
    polar_exercise_id: str
    device: str
    device_id: str
    sport: str
    start_time: datetime
    duration_minutes: float = Field(gt=0)
    treadmill_context: TreadmillContext
    heart_rate: HeartRate
    optical_ppi_stats: OpticalPpiStats
    heart_rate_zones_minutes: dict[str, float]
    recent_training_loads: list[float] = Field(default_factory=lambda: [38, 42, 45, 40, 44, 41, 43])
    subjective_report: str = ""

    @field_validator("device")
    @classmethod
    def supported_device(cls, value: str) -> str:
        if value.lower() != "polar verity sense":
            raise ValueError("Este MVP solo admite Polar Verity Sense.")
        return value

    @field_validator("heart_rate_zones_minutes")
    @classmethod
    def valid_zones(cls, value: dict[str, float]) -> dict[str, float]:
        if any(minutes < 0 for minutes in value.values()):
            raise ValueError("Los minutos de zona no pueden ser negativos.")
        return value

def _demo_path() -> Path:
    configured = os.getenv("POLAR_DEMO_SESSION_PATH")
    return Path(configured) if configured else Path(__file__).resolve().parent.parent / "data" / "demo_polar_session.json"

def fetch_polar_session_tool(session_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """Carga y valida una sesión real de AccessLink o una sesión local de demo.

    Usa POLAR_DATA_SOURCE=accesslink para consultar Polar Flow. El modo demo es
    el predeterminado para conservar una ejecución reproducible sin Internet.
    """
    source = os.getenv("POLAR_DATA_SOURCE", "demo").lower()
    if source == "accesslink":
        payload = fetch_accesslink_session(session_id)
    elif source == "demo":
        path = _demo_path()
        if not path.exists():
            raise FileNotFoundError(f"No existe el payload de demo: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError("POLAR_DATA_SOURCE debe ser demo o accesslink.")
    if session_id and payload.get("polar_exercise_id") != session_id:
        raise ValueError("La sesión solicitada no coincide con el payload de demo.")
    validated = PolarTelemetry.model_validate(payload).model_dump(mode="json")
    tool_context.state["raw_polar_telemetry"] = validated
    return validated

def calculate_biometrics_tool(tool_context: ToolContext) -> dict[str, Any]:
    """Calcula TRIMP, deriva cardíaca y ACWR únicamente con Python."""
    raw = tool_context.state.get("raw_polar_telemetry")
    if not raw:
        raise ValueError("No existe raw_polar_telemetry en el estado compartido.")
    telemetry = PolarTelemetry.model_validate(raw)
    hr = telemetry.heart_rate
    drift_pct = ((hr.second_half_avg_hr - hr.first_half_avg_hr) / hr.first_half_avg_hr) * 100
    intensity = max(0.0, (hr.average - hr.resting_baseline) / (190 - hr.resting_baseline))
    trimp = telemetry.duration_minutes * intensity * 0.64 * (2 ** (1.92 * intensity))
    loads = telemetry.recent_training_loads
    acute = sum(loads[-7:])
    chronic = (sum(loads) / len(loads) * 7) if loads else 0
    acwr = acute / chronic if chronic else 0
    metrics = {"trimp_banister": round(trimp, 2), "cardiac_drift_pct": round(drift_pct, 2), "acwr": round(acwr, 2), "mean_hr_bpm": hr.average, "max_hr_bpm": hr.maximum, "avg_ppi_ms": telemetry.optical_ppi_stats.avg_ppi_ms, "rmssd_recovery_index": telemetry.optical_ppi_stats.rmssd_recovery_index, "fatigue_anomaly_detected": drift_pct > 5 or acwr > 1.3, "critical_safety_flag": hr.resting_baseline > 110}
    tool_context.state["biometric_metrics"] = metrics
    tool_context.state["fatigue_anomaly_detected"] = metrics["fatigue_anomaly_detected"]
    return metrics

def _normalize_approval_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").strip()


def _has_explicit_approval(approval_text: str) -> bool:
    """Accept only a short, unambiguous user confirmation in Spanish."""
    return _normalize_approval_text(approval_text) in {
        "apruebo el ajuste",
        "apruebo el ajuste al plan",
        "si, apruebo el ajuste",
        "si, apruebo el ajuste al plan",
    }


def update_training_plan_tool(
    recalibrated_session: dict[str, Any],
    approval_text: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Write a local-only audit record after explicit human approval.

    This function never calls Calendar, Sheets, Polar, or any external service.
    The approval phrase is validated here instead of trusting an LLM-provided
    boolean.
    """
    if not _has_explicit_approval(approval_text):
        return {"status": "BLOCKED_WAITING_EXPLICIT_CONFIRMATION"}
    result = {
        "status": "UPDATED_SIMULATION",
        "provider": "local_audit_only",
        "audit_event_id": str(uuid4()),
        "approval_text": approval_text,
        "next_session": recalibrated_session,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    tool_context.state["execution_audit_log"] = result
    return result
