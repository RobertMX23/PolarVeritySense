"""Framework-independent contracts for the bounded recommendation use case."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

Stage = Literal["analyst", "critic", "refinement"]
EvidenceKey = Literal["duration_seconds", "mean_hr_bpm", "min_hr_bpm", "max_hr_bpm",
                      "heart_rate_zones", "cardiac_drift_pct", "comparison"]
Limitation = Literal["NOT_MEDICAL", "CONTEXT_LIMITED", "NO_CAUSAL_INFERENCE"]
Correction = Literal["REQUEST_CONTEXT", "NO_MAINTAIN", "ACK_LIMITATIONS", "HUMAN_REVIEW"]


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    action: Literal["REDUCE_LOAD", "MAINTAIN_LOAD", "REQUEST_CONTEXT", "PAUSE"]
    evidence_keys: list[EvidenceKey] = Field(min_length=1, max_length=4)
    limitations: list[Limitation] = Field(min_length=2, max_length=3)
    explanation: str = Field(min_length=1, max_length=240)


class Critique(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    verdict: Literal["APPROVE", "REVISE", "REJECT"]
    required_changes: list[Correction] = Field(max_length=4)
    reason: str = Field(min_length=1, max_length=160)


@dataclass(frozen=True)
class InferencePolicy:
    max_input_tokens: int = 4096
    max_calls: int = field(default=3, init=False)
    final_output_tokens: int = field(default=350, init=False)

    def __post_init__(self):
        if not 256 <= self.max_input_tokens <= 4096:
            raise ValueError("El presupuesto de entrada debe estar entre 256 y 4096 tokens.")

    def output_limit(self, stage: Stage) -> int:
        return 180 if stage == "critic" else 350


@dataclass(frozen=True)
class InferenceRequest:
    stage: Stage
    prompt: str
    max_output_tokens: int


@dataclass(frozen=True)
class InferenceReply:
    text: str
    finish_reason: str
    usage: dict[str, int | None]


class InferenceGateway(Protocol):
    async def count_tokens(self, text: str) -> int: ...

    async def generate(self, request: InferenceRequest) -> InferenceReply: ...


class PolicyViolation(ValueError):
    """Public code only: never include raw prompts or provider errors."""
