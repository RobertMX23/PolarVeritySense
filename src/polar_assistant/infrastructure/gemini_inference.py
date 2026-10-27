"""Single-request Gemini adapter. No tools, hidden history or SDK retries."""

import os

from google import genai
from google.genai import types

from polar_assistant.application.inference_contracts import InferenceReply, InferenceRequest


class GeminiInferenceGateway:
    def __init__(self, model: str = "gemini-3.8-flash"):
        self.model = model

    def _client(self):
        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_KEY_MISSING")
        return genai.Client(
            api_key=key, vertexai=False,
            http_options=types.HttpOptions(
                timeout=30000, retry_options=types.HttpRetryOptions(attempts=1),
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
