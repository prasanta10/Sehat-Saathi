"""The rules engine: the only component that produces an urgency level.

``evaluate`` is a pure function of confirmed fact values and versioned content. No model, no
network, no clock. Order:

1. Any confirmed universal or pathway danger sign -> EMERGENCY. Nothing else matters.
2. Pathway does not apply to this person (known facts contradict ``applies_when``)
   -> INCOMPLETE ``pathway_not_applicable``.
3. A HIGH rule definitely true on known facts -> HIGH (still listing facts to ask, so an
   emergency can be ruled out). Missing information never hides an established HIGH.
4. Any required fact unknown, or any danger sign / higher-level rule undetermined because a fact
   it needs is unknown -> INCOMPLETE ``missing_facts`` (with ``minimum_level`` if a MEDIUM rule
   already holds).
5. A MEDIUM rule true -> MEDIUM.
6. An explicit low-care rule true -> LOW. A pathway without one can never return LOW.
7. Otherwise -> INCOMPLETE ``no_rule_matched`` (refer for assessment). There is no default-to-low.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.facts import FactValue, I18nText
from app.rules import conditions
from app.rules.schema import (
    DangerSigns,
    I18nList,
    Pathway,
    ReviewStatus,
    Rule,
    SourceRef,
    Urgency,
)

LEVEL_RANK = {
    Urgency.LOW: 0,
    Urgency.INCOMPLETE: 1,
    Urgency.MEDIUM: 2,
    Urgency.HIGH: 3,
    Urgency.EMERGENCY: 4,
}


class Reason(StrEnum):
    danger_sign = "danger_sign"
    rule = "rule"
    low_care = "low_care"
    missing_facts = "missing_facts"
    no_rule_matched = "no_rule_matched"
    no_pathway = "no_pathway"
    pathway_not_applicable = "pathway_not_applicable"


class FiredKind(StrEnum):
    danger_sign = "danger_sign"
    pathway_danger_sign = "pathway_danger_sign"
    rule = "rule"
    low_care = "low_care"


class Fired(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    kind: FiredKind
    level: Urgency
    text: I18nText  # danger-sign label or rule rationale, from the content file
    sources: tuple[SourceRef, ...]


class TriageResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    urgency: Urgency
    reason: Reason
    fired: tuple[Fired, ...] = ()
    missing_fact_keys: tuple[str, ...] = ()
    minimum_level: Urgency | None = None
    facility_level: str | None = None
    target_window: str | None = None
    return_precautions: I18nList | None = None
    pathway_id: str | None = None
    pathway_version: str | None = None
    ruleset_version: str
    review_status: ReviewStatus

    @property
    def fired_rule_ids(self) -> tuple[str, ...]:
        return tuple(f.id for f in self.fired)

    @property
    def source_refs(self) -> tuple[SourceRef, ...]:
        seen: dict[tuple[str, str], SourceRef] = {}
        for f in self.fired:
            for s in f.sources:
                seen.setdefault((s.ref, s.locator), s)
        return tuple(seen.values())


def _dedupe(keys: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(keys))


def evaluate(
    facts: Mapping[str, FactValue],
    pathway: Pathway | None,
    danger_signs: DangerSigns,
    ruleset_version: str,
) -> TriageResult:
    """Evaluate *confirmed* fact values. Callers obtain them via ``confirmed_values``."""
    review = danger_signs.review.status
    if pathway is not None and pathway.review.status is ReviewStatus.draft:
        review = ReviewStatus.draft

    base: dict[str, Any] = {
        "ruleset_version": ruleset_version,
        "review_status": review,
        "pathway_id": pathway.id if pathway else None,
        "pathway_version": pathway.version if pathway else None,
    }

    def result(urgency: Urgency, reason: Reason, **kw: Any) -> TriageResult:
        return TriageResult(urgency=urgency, reason=reason, **base, **kw)

    # 1. Danger signs ---------------------------------------------------------------------
    fired: list[Fired] = [
        Fired(
            id=s.id,
            kind=FiredKind.danger_sign,
            level=Urgency.EMERGENCY,
            text=s.label,
            sources=s.sources,
        )
        for s in danger_signs.signs
        if facts.get(s.fact) == "yes"
    ]
    undetermined_ds: list[str] = []
    if pathway is not None:
        for ds in pathway.danger_signs:
            outcome = conditions.evaluate(ds.when, facts)
            if outcome is True:
                fired.append(
                    Fired(
                        id=ds.id,
                        kind=FiredKind.pathway_danger_sign,
                        level=Urgency.EMERGENCY,
                        text=ds.label,
                        sources=(ds.source,),
                    )
                )
            elif outcome is None:
                undetermined_ds += conditions.unknown_facts(ds.when, facts)
    if fired:
        return result(
            Urgency.EMERGENCY,
            Reason.danger_sign,
            fired=tuple(fired),
            target_window="immediately",
        )

    if pathway is None:
        return result(Urgency.INCOMPLETE, Reason.no_pathway)

    # 2. Does the pathway apply? -------------------------------------------------------------
    applies = conditions.evaluate(pathway.applies_when, facts)
    applies_missing = (
        conditions.unknown_facts(pathway.applies_when, facts) if applies is None else []
    )

    # Rule outcomes on known facts.
    true_rules = [r for r in pathway.rules if conditions.evaluate(r.when, facts) is True]
    undetermined_rules = [r for r in pathway.rules if conditions.evaluate(r.when, facts) is None]
    high = next((r for r in true_rules if r.level is Urgency.HIGH), None)
    medium = next((r for r in true_rules if r.level is Urgency.MEDIUM), None)
    established = high or medium

    def rule_fired(r: Rule) -> Fired:
        return Fired(
            id=r.id, kind=FiredKind.rule, level=r.level, text=r.rationale, sources=(r.source,)
        )

    if applies is False:
        return result(
            Urgency.INCOMPLETE,
            Reason.pathway_not_applicable,
            minimum_level=established.level if established else None,
            fired=(rule_fired(established),) if established else (),
        )

    # Facts still to ask, in priority order: danger signs first, then the pathway's questions.
    required_missing = [
        q.fact
        for q in pathway.questions
        if q.required
        and q.fact not in facts
        and (q.ask_when is None or conditions.evaluate(q.ask_when, facts) is not False)
    ]

    # 3. HIGH holds on known facts ------------------------------------------------------------
    if high is not None:
        return result(
            Urgency.HIGH,
            Reason.rule,
            fired=(rule_fired(high),),
            missing_fact_keys=_dedupe(undetermined_ds + applies_missing + required_missing),
            facility_level=high.facility_level,
            target_window=high.target_window,
        )

    # 4. Anything unknown that could change the answer ------------------------------------------
    current_rank = LEVEL_RANK[medium.level] if medium else LEVEL_RANK[Urgency.LOW]
    blocking_rule_facts = [
        k
        for r in undetermined_rules
        if LEVEL_RANK[r.level] > current_rank
        for k in conditions.unknown_facts(r.when, facts)
    ]
    missing = _dedupe(undetermined_ds + applies_missing + required_missing + blocking_rule_facts)
    if missing:
        return result(
            Urgency.INCOMPLETE,
            Reason.missing_facts,
            missing_fact_keys=missing,
            minimum_level=medium.level if medium else None,
            fired=(rule_fired(medium),) if medium else (),
            facility_level=medium.facility_level if medium else None,
            target_window=medium.target_window if medium else None,
        )

    # 5. MEDIUM ------------------------------------------------------------------------------
    if medium is not None:
        return result(
            Urgency.MEDIUM,
            Reason.rule,
            fired=(rule_fired(medium),),
            facility_level=medium.facility_level,
            target_window=medium.target_window,
        )

    # 6. Explicit low-care rule ---------------------------------------------------------------
    low = pathway.low_care
    if low is not None:
        outcome = conditions.evaluate(low.when, facts)
        if outcome is True:
            return result(
                Urgency.LOW,
                Reason.low_care,
                fired=(
                    Fired(
                        id=low.id,
                        kind=FiredKind.low_care,
                        level=Urgency.LOW,
                        text=low.rationale,
                        sources=(low.source,),
                    ),
                ),
                return_precautions=low.return_precautions,
            )
        if outcome is None:
            return result(
                Urgency.INCOMPLETE,
                Reason.missing_facts,
                missing_fact_keys=_dedupe(conditions.unknown_facts(low.when, facts)),
            )

    # 7. Nothing matched -----------------------------------------------------------------------
    return result(Urgency.INCOMPLETE, Reason.no_rule_matched)
