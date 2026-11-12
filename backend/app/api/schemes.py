from typing import Any

from fastapi import APIRouter

from app.api.deps import RulesDep, SessionDep, WorkerDep
from app.api.schemas import AmountOut, ExcerptOut, SchemeCardOut, SchemesOut, SourceOut
from app.config import get_settings
from app.content.bundle import references
from app.domain.facts import confirmed_values
from app.rules.engine import TriageResult
from app.rules.schema import SourceRef
from app.schemes import search as fts
from app.schemes.matcher import load_schemes, match
from app.services import audit
from app.services import encounters as svc
from app.services.errors import Conflict

router = APIRouter(tags=["schemes"])


def _source(refs: dict[str, Any], s: SourceRef) -> SourceOut:
    r = refs[s.ref]
    excerpt = next((e["text"] for e in r["excerpts"] if e["locator"] == s.locator), None)
    return SourceOut(
        ref=s.ref,
        locator=s.locator,
        title=r["title"],
        publisher=r["publisher"],
        url=r["url"],
        retrieved_on=str(r["retrieved_on"]),
        excerpt=excerpt,
    )


@router.get("/encounters/{encounter_id}/schemes", response_model=SchemesOut)
def encounter_schemes(
    encounter_id: str, session: SessionDep, worker: WorkerDep, rules: RulesDep
) -> SchemesOut:
    """Scheme information for the visit. Computed after, and independently of, the triage result."""
    enc = svc.get_encounter(session, worker, encounter_id)
    t = svc.latest_triage(enc)
    if t is None:
        raise Conflict("not_triaged", "scheme information follows the urgency result")
    result = TriageResult.model_validate(t.result)
    p = enc.person
    facts: dict[str, Any] = {
        k: v
        for k, v in {"age_years": p.age_years, "age_months": p.age_months, "sex": p.sex}.items()
        if v is not None
    }
    for k in ("pregnant", "ayushman_card_held"):
        if getattr(p, k) in ("yes", "no"):
            facts[k] = getattr(p, k)
    if p.sex == "male" and "pregnant" not in facts:
        facts["pregnant"] = "no"  # scheme display only; never used for urgency
    facts.update(confirmed_values(svc.facts_of(enc)))
    tags = set(rules.pathway(enc.pathway_id).tags) if enc.pathway_id else set()
    root = get_settings().content_root
    cards = match(
        load_schemes(root),
        state=p.state or worker.state,
        urgency=result.urgency,
        facts=facts,
        pathway_tags=tags,
    )
    refs = references(root)
    out = [
        SchemeCardOut(
            id=c.scheme.id,
            status=c.status.value,
            name=c.scheme.name.model_dump(),
            may_cover=c.scheme.may_cover.model_dump(),
            does_not_cover=c.scheme.does_not_cover.model_dump(),
            to_confirm=c.scheme.to_confirm.model_dump() if c.scheme.to_confirm else None,
            not_applicable_note=c.scheme.not_applicable_note.model_dump()
            if c.scheme.not_applicable_note
            else None,
            unknown_facts=c.unknown_facts,
            documents=list(c.scheme.documents),
            where_to_confirm=c.scheme.where_to_confirm.model_dump(),
            helpline=c.scheme.helpline,
            amounts=[
                AmountOut(text=a.text.model_dump(), as_of=a.as_of, source=_source(refs, a.source))
                for a in c.scheme.amounts
            ],
            sources=[_source(refs, s) for s in c.scheme.sources],
        )
        for c in cards
    ]
    audit.record(
        session,
        "schemes_shown",
        actor_id=worker.id,
        encounter_id=enc.id,
        person_id=enc.person_id,
        detail={"cards": {c.id: c.status for c in out}},
    )
    session.commit()
    return SchemesOut(
        cards=out,
        unparsed_concerns=enc.extractions[-1].unparsed_concerns if enc.extractions else [],
    )


@router.get("/schemes/search", response_model=list[ExcerptOut])
def search_excerpts(q: str, worker: WorkerDep) -> list[ExcerptOut]:
    """'Tell me more': verbatim official excerpts matching the words.

    An empty result means the answer is "confirm at the facility", never a guess."""
    root = get_settings().content_root
    refs = references(root)
    return [
        ExcerptOut(source=_source(refs, SourceRef(ref=h["ref"], locator=h["locator"])))
        for h in fts.search(root, q)
    ]
