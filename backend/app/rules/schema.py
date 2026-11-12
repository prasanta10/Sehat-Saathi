"""Typed views of the rules content files. Structure is first checked by JSON Schema."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.facts import FactSpec, I18nText


class Urgency(StrEnum):
    EMERGENCY = "EMERGENCY"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INCOMPLETE = "INCOMPLETE"


class ReviewStatus(StrEnum):
    draft = "draft"
    clinician_reviewed = "clinician_reviewed"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceRef(_Frozen):
    ref: str
    locator: str


class Review(_Frozen):
    status: ReviewStatus
    reviewer: str | None = None
    reviewed_on: str | None = None
    content_hash: str | None = None


class I18nList(_Frozen):
    en: tuple[str, ...]
    hi: tuple[str, ...]


Condition = dict[str, Any]


class Question(_Frozen):
    fact: str
    required: bool
    ask: I18nText
    options: tuple[str, ...] = ()
    input: str | None = None
    ask_when: Condition | None = None


class PathwayDangerSign(_Frozen):
    id: str
    when: Condition
    label: I18nText
    source: SourceRef


class Rule(_Frozen):
    id: str
    level: Urgency
    when: Condition
    rationale: I18nText
    source: SourceRef
    facility_level: str
    target_window: str


class LowCare(_Frozen):
    id: str
    when: Condition
    rationale: I18nText
    return_precautions: I18nList
    source: SourceRef


class Referral(_Frozen):
    bring: tuple[str, ...]


class Pathway(_Frozen):
    id: str
    version: str
    title: I18nText
    applies_when: Condition
    review: Review
    sources: tuple[str, ...]
    questions: tuple[Question, ...]
    danger_signs: tuple[PathwayDangerSign, ...]
    rules: tuple[Rule, ...]
    referral: Referral
    low_care: LowCare | None
    tags: tuple[str, ...] = ()


class DangerSign(_Frozen):
    id: str
    fact: str
    group: str
    label: I18nText
    pictogram: str
    sources: tuple[SourceRef, ...]


class DangerSigns(_Frozen):
    version: str
    review: Review
    signs: tuple[DangerSign, ...]


class FactRegistry(_Frozen):
    version: str
    facts: dict[str, FactSpec]
