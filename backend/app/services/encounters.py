"""Encounter workflow: answers, confirmation, triage and the emergency path.

Urgency is only ever computed by ``app.rules.engine.evaluate`` on *confirmed* facts. Before
confirmation, the engine is used solely to decide which question to ask next; that interim
result is never returned to the client.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.facts import (
    Fact,
    FactOrigin,
    FactStatus,
    FactValue,
    InvalidFactValue,
    confirmed_values,
    normalise_value,
)
from app.domain.state_machine import (
    REOPEN_ON_EDIT_FROM,
    EncounterState,
    InvalidTransition,
    can_transition,
    transition,
)
from app.rules.engine import TriageResult, evaluate
from app.rules.loader import RuleSet
from app.rules.schema import Question
from app.services.errors import Conflict, DomainError, NotFound
from app.store.models import Encounter, FactRow, Person, TriageRow, Worker, utcnow

S = EncounterState
PERSON_FACTS = ("age_years", "age_months", "sex", "pregnant")


def _move(enc: Encounter, target: EncounterState) -> None:
    try:
        enc.status = transition(S(enc.status), target).value
    except InvalidTransition as e:
        raise Conflict("invalid_transition", str(e)) from e


def get_encounter(session: Session, worker: Worker, encounter_id: str) -> Encounter:
    enc = session.get(Encounter, encounter_id)
    if enc is None or enc.worker_id != worker.id:
        raise NotFound("encounter_not_found")
    return enc


def list_encounters(session: Session, worker: Worker) -> list[Encounter]:
    stmt = (
        select(Encounter)
        .where(Encounter.worker_id == worker.id)
        .order_by(Encounter.created_at.desc())
    )
    return list(session.scalars(stmt))


def _fact_row(enc: Encounter, key: str) -> FactRow | None:
    return next((f for f in enc.facts if f.key == key), None)


def _to_fact(row: FactRow) -> Fact:
    return Fact(
        key=row.key,
        value=row.value,
        status=FactStatus(row.status),
        origin=FactOrigin(row.origin),
        source_span=row.source_span,
        confirmed_by=row.confirmed_by,
        confirmed_at=row.confirmed_at,
    )


def facts_of(enc: Encounter) -> list[Fact]:
    return [_to_fact(r) for r in enc.facts]


def _set_fact(
    enc: Encounter,
    rules: RuleSet,
    key: str,
    raw: object,
    origin: FactOrigin,
    *,
    confirmed_by: str | None = None,
) -> None:
    spec = rules.registry.facts.get(key)
    if spec is None:
        raise DomainError("unknown_fact", f"fact {key!r} is not in the registry")
    try:
        value = normalise_value(spec, raw)
    except InvalidFactValue as e:
        raise DomainError("invalid_fact_value", str(e)) from e
    if confirmed_by:
        status = FactStatus.confirmed if value is not None else FactStatus.unknown
    else:
        status = FactStatus.suggested if value is not None else FactStatus.unknown
    row = _fact_row(enc, key)
    if row is None:
        row = FactRow(key=key, encounter_id=enc.id)
        enc.facts.append(row)
    row.value = value
    row.status = status.value
    row.origin = origin.value
    row.updated_at = utcnow()
    row.confirmed_by = confirmed_by
    row.confirmed_at = utcnow() if confirmed_by else None


def person_fact_values(person: Person, rules: RuleSet) -> dict[str, object]:
    raw: dict[str, object] = {
        "age_years": person.age_years,
        "age_months": person.age_months,
        "sex": person.sex,
        "pregnant": person.pregnant if person.pregnant in ("yes", "no") else None,
    }
    return {k: v for k, v in raw.items() if v is not None and k in rules.registry.facts}


def create_encounter(
    session: Session,
    worker: Worker,
    rules: RuleSet,
    person_id: str,
    language: str,
    pathway_id: str | None,
) -> Encounter:
    person = session.get(Person, person_id)
    if person is None or person.worker_id != worker.id:
        raise NotFound("person_not_found")
    enc = Encounter(
        person_id=person.id,
        worker_id=worker.id,
        language=language,
        synthetic=person.synthetic,
        status=S.draft.value,
    )
    session.add(enc)
    session.flush()
    for key, value in person_fact_values(person, rules).items():
        _set_fact(enc, rules, key, value, FactOrigin.manual)
    if pathway_id:
        set_pathway(enc, rules, pathway_id)
    return enc


def set_pathway(enc: Encounter, rules: RuleSet, pathway_id: str | None) -> None:
    if pathway_id is not None and pathway_id not in rules.pathways:
        raise DomainError("unknown_pathway", pathway_id)
    if pathway_id == enc.pathway_id:
        return
    enc.pathway_id = pathway_id
    enc.pathway_version = rules.pathways[pathway_id].version if pathway_id else None
    if S(enc.status) in REOPEN_ON_EDIT_FROM:
        _reopen_if_needed(enc)  # a confirmed result no longer matches the pathway


def capture_text(enc: Encounter, text: str) -> None:
    from app.store.models import Capture

    if not text.strip():
        raise DomainError("empty_capture")
    if S(enc.status) is S.emergency:
        raise Conflict("invalid_transition", "visit is in emergency")
    enc.captures.append(Capture(encounter_id=enc.id, kind="text", transcript=text.strip()))
    if can_transition(S(enc.status), S.captured):
        _move(enc, S.captured)


def _reopen_if_needed(enc: Encounter) -> None:
    state = S(enc.status)
    if state in REOPEN_ON_EDIT_FROM:
        for t in enc.triage_results:
            t.superseded = True
        _move(enc, S.clarifying)
    elif state in (S.draft, S.captured, S.extracted):
        _move(enc, S.clarifying)
    elif state is S.clarifying:
        pass
    else:
        raise Conflict("invalid_transition", f"cannot edit facts in state {state}")


def answer(enc: Encounter, rules: RuleSet, key: str, value: object, origin: FactOrigin) -> None:
    _set_fact(enc, rules, key, value, origin)
    _reopen_if_needed(enc)


def draft_values(enc: Encounter) -> dict[str, FactValue]:
    """All current non-rejected values, confirmed or not. Only for choosing questions."""
    return {
        f.key: f.value
        for f in enc.facts
        if f.status in (FactStatus.suggested.value, FactStatus.confirmed.value)
        and f.value is not None
    }


def next_question(enc: Encounter, rules: RuleSet) -> tuple[str | None, Question | None, list[str]]:
    """Next fact to ask, its pathway question (if any), and all facts still to ask."""
    if enc.pathway_id is None:
        return None, None, []
    pathway = rules.pathway(enc.pathway_id)
    interim = evaluate(draft_values(enc), pathway, rules.danger_signs, rules.version)
    asked_unknown = {f.key for f in enc.facts if f.status == FactStatus.unknown.value}
    to_ask = [k for k in interim.missing_fact_keys if k not in asked_unknown]
    if not to_ask:
        return None, None, []
    key = to_ask[0]
    question = next((q for q in pathway.questions if q.fact == key), None)
    return key, question, to_ask


def confirm(enc: Encounter, worker: Worker, checked_with_family: bool) -> None:
    if not checked_with_family:
        raise DomainError(
            "not_checked_with_family", "the worker must confirm the facts were checked"
        )
    if S(enc.status) in (S.draft, S.captured, S.extracted):
        _move(enc, S.clarifying)
    _move(enc, S.confirmed)
    now = utcnow()
    for row in enc.facts:
        if row.status == FactStatus.rejected.value:
            continue
        row.status = (
            FactStatus.confirmed.value if row.value is not None else FactStatus.unknown.value
        )
        row.confirmed_by = worker.id
        row.confirmed_at = now


def _store(enc: Encounter, result: TriageResult, values: dict[str, FactValue]) -> TriageRow:
    for t in enc.triage_results:
        t.superseded = True
    row = TriageRow(
        encounter_id=enc.id,
        urgency=result.urgency.value,
        result=result.model_dump(mode="json"),
        confirmed_facts=dict(values),
        ruleset_version=result.ruleset_version,
    )
    enc.triage_results.append(row)
    return row


def triage(enc: Encounter, rules: RuleSet) -> TriageResult:
    if S(enc.status) is not S.confirmed:
        raise Conflict("not_confirmed", "facts must be confirmed before triage")
    pathway = rules.pathway(enc.pathway_id) if enc.pathway_id else None
    values = confirmed_values(facts_of(enc))
    result = evaluate(values, pathway, rules.danger_signs, rules.version)
    _store(enc, result, values)
    _move(enc, S.triaged)
    return result


def emergency(enc: Encounter, worker: Worker, rules: RuleSet, sign_ids: list[str]) -> TriageResult:
    """Record worker-tapped danger signs and return EMERGENCY. Works from any open state."""
    by_id = {s.id: s for s in rules.danger_signs.signs}
    unknown = [s for s in sign_ids if s not in by_id]
    if not sign_ids or unknown:
        raise DomainError("unknown_danger_sign", ", ".join(unknown) or "no sign given")
    if not can_transition(S(enc.status), S.emergency):
        raise Conflict("invalid_transition", f"cannot record an emergency in state {enc.status}")
    for sid in sign_ids:
        _set_fact(enc, rules, by_id[sid].fact, "yes", FactOrigin.manual, confirmed_by=worker.id)
    pathway = rules.pathway(enc.pathway_id) if enc.pathway_id else None
    values = confirmed_values(facts_of(enc))
    result = evaluate(values, pathway, rules.danger_signs, rules.version)
    _store(enc, result, values)
    _move(enc, S.emergency)
    return result


def latest_triage(enc: Encounter) -> TriageRow | None:
    current = [t for t in enc.triage_results if not t.superseded]
    return current[-1] if current else None


def replay(row: TriageRow, rules: RuleSet, pathway_id: str | None) -> dict[str, Any]:
    pathway = rules.pathway(pathway_id) if pathway_id else None
    return evaluate(row.confirmed_facts, pathway, rules.danger_signs, rules.version).model_dump(
        mode="json"
    )
