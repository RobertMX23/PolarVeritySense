import asyncio

from sport_assistant_agent.runtime_identity import qa_subject_for_iap_user
from sport_assistant_agent.server import IapUserBindingMiddleware, _opaque_iap_user_id


async def _invoke(middleware, scope, body=b""):
    received = False
    events = []

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.request", "body": b"", "more_body": False}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        events.append(message)

    await middleware(scope, receive, send)
    return events


def test_iap_binding_uses_an_opaque_session_id_and_rewrites_client_user_id():
    captured = {}

    async def app(scope, receive, send):
        captured["path"] = scope["path"]
        captured["body"] = await receive()

    raw_iap_id = "accounts.google.com:opaque-subject"
    body = b'{"user_id":"browser-controlled","session_id":"s1"}'
    asyncio.run(_invoke(
        IapUserBindingMiddleware(app),
        {"type": "http", "path": "/run_sse", "headers": [(b"x-goog-authenticated-user-id", raw_iap_id.encode())]},
        body,
    ))

    canonical = _opaque_iap_user_id(raw_iap_id)
    assert canonical not in raw_iap_id
    assert canonical in captured["body"]["body"].decode()


def test_iap_binding_rejects_adk_session_endpoints_without_iap_identity():
    events = asyncio.run(_invoke(
        IapUserBindingMiddleware(lambda scope, receive, send: None),
        {"type": "http", "path": "/apps/a/users/browser/sessions", "headers": []},
    ))
    assert events[0]["status"] == 401


def test_qa_subject_binding_never_uses_client_or_iap_text_as_subject(monkeypatch):
    monkeypatch.setenv("FIRESTORE_QA_SUBJECT_ID", "ath_local_smoke_2026")
    assert qa_subject_for_iap_user("browser-controlled") is None
    assert qa_subject_for_iap_user("iap_" + "a" * 64) == "ath_local_smoke_2026"
