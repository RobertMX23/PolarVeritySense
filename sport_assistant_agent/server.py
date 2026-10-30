"""IAP-aware ASGI entry point for the private ADK QA web service.

``adk web`` is a development server whose ``userId`` comes from the browser.
This wrapper replaces that client value with an opaque value derived from the
IAP header before ADK creates or runs a session.  Cloud Run accepts only the
Google-managed IAP service account, so external clients cannot reach this
process while forging that header.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from google.adk.cli.fast_api import get_fast_api_app


_USER_PATH = re.compile(r"(/users/)[^/]+")
_BODY_USER_PATHS = frozenset({"/run", "/run_sse"})


def _headers(scope: dict[str, Any]) -> dict[str, str]:
    return {name.decode("latin-1").lower(): value.decode("latin-1") for name, value in scope.get("headers", [])}


def _opaque_iap_user_id(iap_user_id: str) -> str:
    """Avoid placing email or the IAP subject itself into ADK session storage."""
    return "iap_" + hashlib.sha256(iap_user_id.encode("utf-8")).hexdigest()


async def _read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            return b"".join(chunks)


def _replay_body(
    body: bytes, original_receive: Callable[[], Awaitable[dict[str, Any]]]
) -> Callable[[], Awaitable[dict[str, Any]]]:
    """Supply the rewritten body once, then preserve the ASGI receive channel.

    ``StreamingResponse`` keeps reading the receive channel to detect a client
    disconnect.  Returning empty ``http.request`` messages forever starves its
    event loop and prevents ADK's SSE events from being delivered.
    """
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return await original_receive()
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


class IapUserBindingMiddleware:
    """Bind ADK's mutable browser user ID to an IAP-authenticated session ID."""

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        original_path = scope.get("path", "")
        needs_identity = original_path in _BODY_USER_PATHS or "/users/" in original_path
        if not needs_identity:
            await self.app(scope, receive, send)
            return

        iap_user_id = _headers(scope).get("x-goog-authenticated-user-id")
        if not iap_user_id:
            body = b'{"detail":"IAP identity is required for ADK session access."}'
            await send({"type": "http.response.start", "status": 401, "headers": [
                (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
            ]})
            await send({"type": "http.response.body", "body": body})
            return

        canonical_user_id = _opaque_iap_user_id(iap_user_id)
        updated_scope = dict(scope)
        updated_scope["path"] = _USER_PATH.sub(r"\1" + canonical_user_id, original_path)
        updated_scope["raw_path"] = updated_scope["path"].encode("utf-8")

        if original_path in _BODY_USER_PATHS:
            raw_body = await _read_body(receive)
            try:
                decoded = json.loads(raw_body or b"{}")
                if isinstance(decoded, dict):
                    # ADK's browser uses the API alias ``userId`` while
                    # programmatic clients commonly send ``user_id``.  The
                    # Pydantic model accepts both, but its alias takes
                    # precedence.  Rewriting only the snake_case spelling
                    # therefore left a browser request bound to its mutable
                    # ``user`` value and made a just-created IAP session look
                    # missing at /run_sse.
                    if "userId" in decoded:
                        decoded["userId"] = canonical_user_id
                    if "user_id" in decoded:
                        decoded["user_id"] = canonical_user_id
                    if "userId" not in decoded and "user_id" not in decoded:
                        decoded["user_id"] = canonical_user_id
                    raw_body = json.dumps(decoded, separators=(",", ":")).encode("utf-8")
            except (TypeError, ValueError):
                # ADK will report a malformed request body through its normal validation.
                pass
            headers = [(name, value) for name, value in scope.get("headers", []) if name.lower() != b"content-length"]
            headers.append((b"content-length", str(len(raw_body)).encode()))
            updated_scope["headers"] = headers
            receive = _replay_body(raw_body, receive)

        await self.app(updated_scope, receive, send)


app = get_fast_api_app(
    agents_dir=os.environ.get("ADK_AGENTS_DIR", str(Path(__file__).resolve().parent)),
    session_service_uri=os.environ.get("ADK_SESSION_SERVICE_URI", "sqlite:////tmp/polar-adk/sessions.db"),
    memory_service_uri="memory://",
    artifact_service_uri="memory://",
    use_local_storage=False,
    web=True,
    bind_host="0.0.0.0",
)
app.add_middleware(IapUserBindingMiddleware)
