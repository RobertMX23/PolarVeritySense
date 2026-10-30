"""Single-request Vertex AI Gemini adapter. No tools or SDK retries."""

import os

from google import genai
from google.genai import types

from polar_assistant.application.inference_contracts import InferenceReply, InferenceRequest


class GeminiInferenceGateway:
    """Model boundary authenticated by Cloud Run's workload identity.

    The service never reads a Gemini Developer API key. In Cloud Run, the
    attached service account supplies Application Default Credentials to Vertex
    AI; local callers must provide normal Google ADC and the project variables.
    """

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    def _client(self):
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        if not project:
            raise RuntimeError("VERTEX_PROJECT_MISSING")
        return genai.Client(
            vertexai=True,
            project=project,
            location=os.getenv("VERTEX_GEMINI_LOCATION", "global"),
            http_options=types.HttpOptions(
                api_version="v1",
                timeout=30000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    async def count_tokens(self, text: str) -> int:
        # AI Studio count_tokens does not support system_instruction in this SDK.
        # All instructions and schemas are deliberately embedded in the same contents.
        async with self._client().aio as client:
            result = await client.models.count_tokens(model=self.model, contents=text)
        if not isinstance(result.total_tokens, int) or result.total_tokens < 1:
            raise RuntimeError("TOKEN_COUNT_UNAVAILABLE")
        return result.total_tokens

    async def generate(self, request: InferenceRequest) -> InferenceReply:
        async with self._client().aio as client:
            response = await client.models.generate_content(
                model=self.model, contents=request.prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1, max_output_tokens=request.max_output_tokens,
                    response_mime_type="application/json", candidate_count=1,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    # Keep the application token budgets deterministic. For this
                    # bounded workflow, hidden reasoning must not consume the
                    # analyst/critic output budget.
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=False,
                        thinking_budget=0,
                    ),
                ),
            )
        candidates = response.candidates or []
        finish = str(candidates[0].finish_reason.value) if candidates and candidates[0].finish_reason else "UNKNOWN"
        usage = response.usage_metadata
        return InferenceReply(
            text=response.text or "", finish_reason=finish,
            usage={
                "input_tokens": getattr(usage, "prompt_token_count", None),
                "output_tokens": getattr(usage, "candidates_token_count", None),
                "thinking_tokens": getattr(usage, "thoughts_token_count", None),
                "total_tokens": getattr(usage, "total_token_count", None),
            },
        )
