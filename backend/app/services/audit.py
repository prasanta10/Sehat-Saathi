"""Append-only audit trail. Detail holds IDs, keys, statuses, counts and versions —
never names, transcripts or fact values."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.store.models import AuditEvent

FORBIDDEN_DETAIL_KEYS = {"name", "transcript", "text", "value", "body", "village", "phone", "pin"}


def record(
    session: Session,
    action: str,
    *,
    actor_id: str | None,
    encounter_id: str | None = None,
    person_id: str | None = None,
    detail: dict[str, Any] | None = None,
    versions: dict[str, Any] | None = None,
) -> None:
    detail = detail or {}
    bad = FORBIDDEN_DETAIL_KEYS & set(detail)
    if bad:
        raise ValueError(f"audit detail must not contain {sorted(bad)}")
    session.add(
        AuditEvent(
            actor_id=actor_id,
            encounter_id=encounter_id,
            person_id=person_id,
            action=action,
            detail=detail,
            versions=versions or {},
        )
    )
