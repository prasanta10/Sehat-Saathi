"""Request and response models: the single definition of the HTTP contract."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.rules.engine import TriageResult

Language = Literal["hi", "en"]
TriValue = Literal["yes", "no", "unknown"]


class PersonIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    age_years: int | None = Field(default=None, ge=0, le=120)
    age_months: int | None = Field(default=None, ge=0, le=59)
    sex: Literal["female", "male", "other"] | None = None
    village: str | None = Field(default=None, max_length=200)
    pregnant: TriValue = "unknown"
    ayushman_card_held: TriValue = "unknown"
    synthetic: bool = False


class PersonPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    age_years: int | None = Field(default=None, ge=0, le=120)
    age_months: int | None = Field(default=None, ge=0, le=59)
    sex: Literal["female", "male", "other"] | None = None
    village: str | None = Field(default=None, max_length=200)
    pregnant: TriValue | None = None
    ayushman_card_held: TriValue | None = None


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    age_years: int | None
    age_months: int | None
    sex: str | None
    village: str | None
    pregnant: str
    ayushman_card_held: str = "unknown"
    synthetic: bool


class EncounterCreate(BaseModel):
    person_id: str
    language: Language = "hi"
    pathway_id: str | None = None


class EncounterPatch(BaseModel):
    pathway_id: str | None = None
    language: Language | None = None


class FactOut(BaseModel):
    key: str
    value: str | int | float | None
    status: str
    origin: str
    evidence: str | None = None


class CaptureOut(BaseModel):
    id: str
    kind: str
    transcript: str
    transcript_original: str | None = None
    has_audio: bool = False
    created_at: datetime


class TriageOut(BaseModel):
    id: str
    created_at: datetime
    result: TriageResult


class EncounterOut(BaseModel):
    id: str
    status: str
    language: str
    pathway_id: str | None
    pathway_version: str | None
    created_at: datetime
    person: PersonOut
    facts: list[FactOut]
    captures: list[CaptureOut]
    triage: TriageOut | None
    unparsed_concerns: list[str] = []
    record_audio_consent: bool | None = None  # latest answer for this visit; None = not asked


class EncounterSummary(BaseModel):
    id: str
    status: str
    created_at: datetime
    person_name: str
    pathway_id: str | None
    urgency: str | None


class TextCapture(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


FactInputValue = str | int | float | None


class AnswerIn(BaseModel):
    fact_key: str
    value: FactInputValue = Field(description="A value of the fact's type, or 'unknown'.")
    answered_via: Literal["option", "text", "voice", "skipped"] = "option"


class FactEdit(BaseModel):
    key: str
    value: FactInputValue


class FactsPatch(BaseModel):
    facts: list[FactEdit] = Field(min_length=1)


class ConfirmIn(BaseModel):
    checked_with_family: bool


class EmergencyIn(BaseModel):
    danger_sign_ids: list[str] = Field(min_length=1)


class NextQuestionOut(BaseModel):
    done: bool
    needs_pathway: bool = False
    fact_key: str | None = None
    remaining: list[str] = []
    ask: dict[str, str] | None = None
    options: list[str] = []
    input: str | None = None


class SuggestedFactOut(BaseModel):
    key: str
    value: str | int | float
    evidence: str
    approximate: bool


class ExtractOut(BaseModel):
    encounter: EncounterOut
    degraded: bool
    reason: str | None
    suggested: list[SuggestedFactOut]
    discarded: int
    suggested_pathways: list[str]
    unparsed_concerns: list[str]


class ParseAnswerIn(BaseModel):
    fact_key: str
    text: str = Field(min_length=1, max_length=500)


class ParseAnswerOut(BaseModel):
    understood: bool
    value: str | int | float | None = None
    approximate: bool = False


class ConsentIn(BaseModel):
    kind: Literal["record_audio", "store_record", "share_handoff"]
    granted: bool


class ConsentOut(BaseModel):
    kind: str
    granted: bool


class AudioCaptureOut(BaseModel):
    encounter: EncounterOut
    degraded: bool
    reason: str | None = None


class TranscriptEdit(BaseModel):
    transcript: str = Field(min_length=1, max_length=10_000)


class SpokenAnswerOut(BaseModel):
    understood: bool
    text: str | None = None


class PlanOut(BaseModel):
    urgency: str
    facility_level: str | None
    facility_names: list[str]
    target_window: str | None
    bring_list: list[str]
    return_precautions: dict[str, list[str]] | None = None
    review_status: str


class OutputOut(BaseModel):
    id: str
    kind: str
    language: str
    body: str
    generated_by: str
    edited_by_worker: bool
    check_failures: list[str]


class OutputEdit(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class SourceOut(BaseModel):
    ref: str
    locator: str
    title: str
    publisher: str
    url: str
    retrieved_on: str
    excerpt: str | None = None


class AmountOut(BaseModel):
    text: dict[str, str]
    as_of: str
    source: SourceOut


class SchemeCardOut(BaseModel):
    id: str
    status: Literal["possibly_relevant", "needs_confirmation", "not_applicable"]
    name: dict[str, str]
    may_cover: dict[str, list[str]]
    does_not_cover: dict[str, list[str]]
    to_confirm: dict[str, list[str]] | None
    not_applicable_note: dict[str, str] | None
    unknown_facts: list[str]
    documents: list[str]
    where_to_confirm: dict[str, str]
    helpline: str | None
    amounts: list[AmountOut]
    sources: list[SourceOut]


class SchemesOut(BaseModel):
    cards: list[SchemeCardOut]
    unparsed_concerns: list[str]
    pregnancy_unknown: bool = (
        False  # a woman whose pregnancy is not recorded: maternity schemes hidden
    )


class ExcerptOut(BaseModel):
    source: SourceOut
