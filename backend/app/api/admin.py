"""Admin endpoints: audit search, export and deletion of a person's record (data rights)."""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import RulesDep, SessionDep, WorkerDep
from app.services import audit
from app.services.auth import require_role
from app.services.encounters import replay
from app.services.errors import NotFound
from app.services.speech import delete_audio
from app.store.models import AuditEvent, Consent, Encounter, Person, TriageRow

router = APIRouter(prefix="/admin", tags=["admin"])
PERSON_FIELDS = ("id", "name", "age_years", "age_months", "sex", "village", "state", "pregnant")


@router.get("/audit")
def audit_search(
    session: SessionDep,
    worker: WorkerDep,
    encounter_id: str | None = None,
    action: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    require_role(worker, "admin")
    q = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(min(limit, 1000))
    if encounter_id:
        q = q.where(AuditEvent.encounter_id == encounter_id)
    if action:
        q = q.where(AuditEvent.action == action)
    return [
        {"id": e.id, "at": e.at.isoformat(), "actor_id": e.actor_id, "encounter_id": e.encounter_id,
         "person_id": e.person_id, "action": e.action, "detail": e.detail, "versions": e.versions}
        for e in session.scalars(q)
    ]  # fmt: skip


@router.get("/replay")
def replay_all(session: SessionDep, worker: WorkerDep, rules: RulesDep) -> dict[str, Any]:
    """Re-evaluate every stored triage result from its stored confirmed facts."""
    require_role(worker, "admin")
    checked = mismatched = other_version = 0
    for row in session.scalars(select(TriageRow)):
        if row.ruleset_version != rules.version:
            other_version += 1
            continue
        enc = session.get(Encounter, row.encounter_id)
        checked += 1
        if replay(row, rules, row.result.get("pathway_id") if enc else None) != row.result:
            mismatched += 1
    return {"checked": checked, "mismatched": mismatched, "other_ruleset_version": other_version}


def _person(session: SessionDep, person_id: str) -> Person:
    p = session.get(Person, person_id)
    if p is None:
        raise NotFound("person_not_found")
    return p


@router.get("/persons/{person_id}/export")
def export_person(person_id: str, session: SessionDep, worker: WorkerDep) -> dict[str, Any]:
    require_role(worker, "admin")
    p = _person(session, person_id)
    encs = list(session.scalars(select(Encounter).where(Encounter.person_id == p.id)))
    audit.record(
        session,
        "person_exported",
        actor_id=worker.id,
        person_id=p.id,
        detail={"encounters": len(encs)},
    )
    session.commit()
    return {
        "person": {k: getattr(p, k) for k in PERSON_FIELDS},
        "encounters": [
            {
                "id": e.id,
                "created_at": e.created_at.isoformat(),
                "status": e.status,
                "pathway_id": e.pathway_id,
                "facts": [{"key": f.key, "value": f.value, "status": f.status} for f in e.facts],
                "captures": [{"kind": c.kind, "transcript": c.transcript} for c in e.captures],
                "triage": [t.result for t in e.triage_results],
                "outputs": [{"kind": o.kind, "body": o.body} for o in e.outputs],
            }
            for e in encs
        ],
        "consents": [
            {"kind": c.kind, "granted": c.granted, "at": c.recorded_at.isoformat()}
            for c in session.scalars(select(Consent).where(Consent.person_id == p.id))
        ],
    }


@router.delete("/persons/{person_id}", status_code=204)
def delete_person(person_id: str, session: SessionDep, worker: WorkerDep) -> None:
    """Delete a person's record and all their visits. The audit trail keeps IDs only."""
    require_role(worker, "admin")
    p = _person(session, person_id)
    encs = list(session.scalars(select(Encounter).where(Encounter.person_id == p.id)))
    for consent in session.scalars(select(Consent).where(Consent.person_id == p.id)):
        session.delete(consent)
    session.flush()
    for e in encs:
        for cap in e.captures:
            delete_audio(cap)
        session.delete(e)
    session.delete(p)
    audit.record(
        session,
        "person_deleted",
        actor_id=worker.id,
        person_id=person_id,
        detail={"encounters": len(encs)},
    )
    session.commit()
