"""Referral plan and generated outputs (handoff note, family instructions)."""

from __future__ import annotations

from app.ai.interfaces import ProviderError, Writer
from app.config import Settings
from app.domain.facts import FactStatus
from app.domain.state_machine import EncounterState as S
from app.outputs import facilities as fac
from app.outputs.checks import check_output
from app.outputs.templates import (
    OutputContext,
    clinician_handoff,
    family_instructions,
    required_lines,
)
from app.rules.engine import TriageResult
from app.rules.loader import RuleSet
from app.services.encounters import _move, latest_triage
from app.services.errors import Conflict, NotFound
from app.store.models import Encounter, OutputRow, ReferralPlanRow, TriageRow, Worker, utcnow


def _current(enc: Encounter) -> tuple[TriageRow, TriageResult]:
    row = latest_triage(enc)
    if row is None:
        raise Conflict("not_triaged", "a triage result is needed first")
    return row, TriageResult.model_validate(row.result)


def plan(enc: Encounter, rules: RuleSet, settings: Settings, worker: Worker) -> ReferralPlanRow:
    row, result = _current(enc)
    existing = next((p for p in reversed(enc.plans) if p.triage_id == row.id), None)
    if existing:
        return existing
    bring = list(rules.pathway(enc.pathway_id).referral.bring) if enc.pathway_id else []
    names: list[str] = []
    if result.facility_level:
        directory = fac.load_facilities(settings.content_root, worker.state)
        names = [f.name for f in fac.suggest(directory, result.facility_level, worker.district)]
    p = ReferralPlanRow(
        encounter_id=enc.id,
        triage_id=row.id,
        facility_level=result.facility_level,
        facility_names=names,
        target_window=result.target_window,
        bring_list=bring,
    )
    enc.plans.append(p)
    if S(enc.status) is S.triaged:
        _move(enc, S.plan_ready)
    return p


def context(
    enc: Encounter, rules: RuleSet, worker: Worker, result: TriageResult, lang: str
) -> OutputContext:
    facts = {
        f.key: f.value
        for f in enc.facts
        if f.status == FactStatus.confirmed.value and f.value is not None
    }
    unknown = [f.key for f in enc.facts if f.status == FactStatus.unknown.value]
    unknown += [k for k in result.missing_fact_keys if k not in unknown]
    p = enc.person
    return OutputContext(
        language=lang,
        person_name=p.name,
        age_years=p.age_years,
        sex=p.sex,
        village=p.village,
        pathway_title=rules.pathway(enc.pathway_id).title.model_dump() if enc.pathway_id else None,
        facts=facts,
        unknown_keys=unknown,
        result=result,
        bring=list(rules.pathway(enc.pathway_id).referral.bring) if enc.pathway_id else [],
        worker_name=worker.name,
        worker_phone=worker.phone,
    )


async def generate(
    enc: Encounter, rules: RuleSet, worker: Worker, writer: Writer
) -> list[OutputRow]:
    row, result = _current(enc)
    out = []
    for kind, lang in (("clinician_handoff", "en"), ("family_instructions", enc.language)):
        ctx = context(enc, rules, worker, result, lang)
        template = (
            clinician_handoff(ctx, rules, lang)
            if kind == "clinician_handoff"
            else family_instructions(ctx, lang)
        )
        body, generated_by, failures = template, "template", []
        if writer.name != "mock":
            try:
                candidate = await writer.rewrite(kind, lang, template)
                failures = check_output(candidate, template, required_lines(ctx, lang))
                if not failures:
                    body, generated_by = candidate, "llm"
            except ProviderError:
                failures = ["writer_unavailable"]
        o = OutputRow(
            encounter_id=enc.id,
            triage_id=row.id,
            kind=kind,
            language=lang,
            body=body,
            template_body=template,
            generated_by=generated_by,
            writer=f"{writer.name}:{writer.model_rev}",
            check_failures=failures,
        )
        enc.outputs.append(o)
        out.append(o)
    return out


def current_outputs(enc: Encounter) -> list[OutputRow]:
    t = latest_triage(enc)
    if t is None:
        return []
    latest: dict[str, OutputRow] = {}
    for o in enc.outputs:
        if o.triage_id == t.id:
            latest[o.kind] = o
    return list(latest.values())


def edit(enc: Encounter, output_id: str, body: str) -> OutputRow:
    o = next((x for x in enc.outputs if x.id == output_id), None)
    if o is None:
        raise NotFound("output_not_found")
    o.body = body.strip()
    o.edited_by_worker = True
    o.created_at = o.created_at or utcnow()
    return o
