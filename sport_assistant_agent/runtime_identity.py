"""Trusted QA identity binding between IAP and the technical Firestore subject."""

from __future__ import annotations

import os


def qa_subject_for_iap_user(session_user_id: str) -> str | None:
    """Map a server-issued opaque IAP session ID to the explicitly configured QA subject.

    This is deliberately a QA-only binding for the non-personal technical
    fixture.  It does not derive an athlete identifier from email, a Polar ID,
    or a user-controlled ADK ``userId``.
    """
    configured_subject = os.getenv("FIRESTORE_QA_SUBJECT_ID", "")
    if not session_user_id.startswith("iap_"):
        return None
    if not configured_subject.startswith("ath_"):
        return None
    return configured_subject
