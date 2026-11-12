"""Deterministic scheme matching. Never decides entitlement: results are
possibly_relevant, needs_confirmation or not_applicable, each with sources."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.content.yamlio import load_yaml
from app.domain.facts import FactValue, I18nText
from app.rules import conditions
from app.rules.schema import I18nList, SourceRef, Urgency


class Status(StrEnum):
    possibly_relevant = "possibly_relevant"
    needs_confirmation = "needs_confirmation"
    not_applicable = "not_applicable"


class Amount(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: I18nText
    source: SourceRef
    as_of: str


class Scheme(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    id: str
    name: I18nText
    jurisdiction: str
    states_excluded: tuple[str, ...] = ()
    care_types: tuple[str, ...] = ()
    not_for: tuple[str, ...] = ()
    requires_tags: tuple[str, ...] = ()
    applies_to: dict[str, Any] | None = None
    priority: str = "free_service"
    eligibility_signals: tuple[dict[str, Any], ...] = ()
    may_cover: I18nList
    does_not_cover: I18nList
    to_confirm: I18nList | None = None
    not_applicable_note: I18nText | None = None
    documents: tuple[str, ...] = ()
    where_to_confirm: I18nText
    helpline: str | None = None
    amounts: tuple[Amount, ...] = ()
    sources: tuple[SourceRef, ...]


class Card(BaseModel):
    scheme: Scheme
    status: Status
    unknown_facts: list[str]


PRIORITY = ["free_service", "transport", "hospital_cover", "cash_benefit", "helpline"]


def load_schemes(root: Path) -> list[Scheme]:
    return [Scheme(**load_yaml(p)) for p in sorted((root / "knowledge" / "schemes").glob("*.yaml"))]


def visit_care(urgency: Urgency, facts: dict[str, FactValue]) -> set[str]:
    """Care the visit is heading for, implied by the rule result (and pregnancy)."""
    care: set[str] = set()
    if urgency in (Urgency.EMERGENCY, Urgency.HIGH):
        care |= {"inpatient", "emergency_transport"}
    elif urgency in (Urgency.MEDIUM, Urgency.INCOMPLETE):
        care |= {"outpatient", "diagnostics"}
    if facts.get("pregnant") == "yes":
        care.add("maternity")
    return care


def match(
    schemes: list[Scheme],
    *,
    state: str | None,
    urgency: Urgency,
    facts: dict[str, FactValue],
    pathway_tags: set[str],
) -> list[Card]:
    care = visit_care(urgency, facts)
    cards: list[Card] = []
    for s in schemes:
        if state and state in s.states_excluded:
            continue
        if s.jurisdiction != "national" and s.jurisdiction != state:
            continue
        if s.requires_tags and not (set(s.requires_tags) & pathway_tags):
            continue
        applies = conditions.evaluate(s.applies_to, facts) if s.applies_to else True
        if applies is False:
            continue
        if (
            applies is None
            and "pregnant" not in facts
            and conditions.evaluate(s.applies_to or {}, {**facts, "pregnant": "no"}) is False
        ):
            continue  # only pregnancy keeps it open: shown once pregnancy is recorded (UI hints)
        if not (set(s.care_types) & care):
            if s.not_applicable_note and set(s.not_for) & care:
                cards.append(Card(scheme=s, status=Status.not_applicable, unknown_facts=[]))
            continue
        unknown = (
            conditions.unknown_facts(s.applies_to, facts)
            if applies is None and s.applies_to
            else []
        )
        unknown += [sig["fact"] for sig in s.eligibility_signals if facts.get(sig["fact"]) is None]
        status = Status.needs_confirmation if unknown or s.to_confirm else Status.possibly_relevant
        cards.append(Card(scheme=s, status=status, unknown_facts=list(dict.fromkeys(unknown))))
    rank = {p: i for i, p in enumerate(PRIORITY)}
    cards.sort(
        key=lambda c: (
            c.status is Status.not_applicable,
            rank.get(c.scheme.priority, 99),
            c.scheme.id,
        )
    )
    return cards
