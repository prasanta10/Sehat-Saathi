"""Run extraction for an encounter and store the results as *suggested* facts."""

from __future__ import annotations

from app.ai.factory import HostedNotAllowed, extractor_for
from app.ai.interfaces import Extractor
from app.ai.orchestrator import ExtractionResult, extract
from app.config import Settings
from app.domain.facts import FactOrigin, FactStatus
from app.domain.state_machine import EncounterState as S
from app.rules.loader import RuleSet
from app.services.encounters import _move
from app.services.errors import Conflict, DomainError
from app.store.models import Encounter, ExtractionRow, FactRow, utcnow


def candidate_facts(enc: Encounter, rules: RuleSet) -> tuple[list[str], list[str]]:
    """Fact keys to extract and candidate pathway ids."""
    pathways = [enc.pathway_id] if enc.pathway_id else sorted(rules.pathways)
    keys: list[str] = []
    for pid in pathways:
        keys += [q.fact for q in rules.pathway(pid).questions]
    keys += [k for k in ("cough_present", "fever_present") if k in rules.registry.facts]
    return list(dict.fromkeys(k for k in keys if k in rules.registry.facts)), sorted(rules.pathways)


async def run_extraction(
    enc: Encounter, rules: RuleSet, settings: Settings, extractor: Extractor | None = None
) -> ExtractionResult:
    if S(enc.status) not in (S.captured, S.extracted):
        raise Conflict("invalid_transition", f"nothing to extract in state {enc.status}")
    if not enc.captures:
        raise DomainError("no_capture")
    capture = enc.captures[-1]
    keys, pathways = candidate_facts(enc, rules)
    specs = [rules.registry.facts[k] for k in keys]
    try:
        extractor = extractor or extractor_for(settings, synthetic=enc.synthetic)
    except HostedNotAllowed:
        result = ExtractionResult(degraded=True, reason="hosted_not_allowed", provider="hosted")
    except ValueError:
        result = ExtractionResult(
            degraded=True, reason="provider_not_configured", provider=settings.llm_provider
        )
    else:
        result = await extract(extractor, capture.transcript, enc.language, specs, pathways)

    enc.extractions.append(
        ExtractionRow(
            encounter_id=enc.id,
            capture_id=capture.id,
            provider=result.provider,
            model_rev=result.model_rev,
            prompt_version=result.prompt_version,
            degraded=result.degraded,
            reason=result.reason,
            attempts=result.attempts,
            suggested=len(result.facts),
            discarded=result.discarded,
            suggested_pathways=result.suggested_pathways,
            unparsed_concerns=result.unparsed_concerns,
        )
    )
    if result.degraded:
        return result  # stays `captured`; the client continues by hand

    existing = {f.key: f for f in enc.facts}
    for sf in result.facts:
        row = existing.get(sf.key)
        if row is not None and (
            row.origin != FactOrigin.extracted.value or row.status == FactStatus.confirmed.value
        ):
            continue  # never overwrite what the worker entered or confirmed
        if row is None:
            row = FactRow(key=sf.key, encounter_id=enc.id)
            enc.facts.append(row)
        row.value = sf.value
        row.status = FactStatus.suggested.value
        row.origin = FactOrigin.extracted.value
        row.source_span = sf.evidence
        row.updated_at = utcnow()
    if enc.pathway_id is None and len(result.suggested_pathways) == 1:
        enc.pathway_id = result.suggested_pathways[0]
        enc.pathway_version = rules.pathway(enc.pathway_id).version
    if S(enc.status) is S.captured:
        _move(enc, S.extracted)
    return result


def reject_fact(enc: Encounter, key: str) -> None:
    row = next((f for f in enc.facts if f.key == key), None)
    if row is None:
        raise DomainError("unknown_fact", key)
    if row.status == FactStatus.confirmed.value:
        raise Conflict("already_confirmed", "edit the fact instead")
    row.status = FactStatus.rejected.value
    row.updated_at = utcnow()
