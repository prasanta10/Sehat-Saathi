"""Facts: typed key/value statements about the person, with ``unknown`` as a first-class value.

Only facts the worker has *confirmed* are ever passed to the rules engine. Suggested facts
(from AI extraction) are drafts until the worker confirms them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FactValue = str | int | float
YES: Literal["yes"] = "yes"
NO: Literal["no"] = "no"
UNKNOWN: Literal["unknown"] = "unknown"


class FactType(StrEnum):
    tristate = "tristate"
    number = "number"
    enum = "enum"


class FactStatus(StrEnum):
    suggested = "suggested"  # proposed by AI or a parser; not yet checked by the worker
    confirmed = "confirmed"  # worker checked it with the family
    unknown = "unknown"  # worker confirmed that nobody knows ("don't know")
    rejected = "rejected"  # worker discarded a suggestion


class FactOrigin(StrEnum):
    extracted = "extracted"
    clarification = "clarification"
    manual = "manual"


class I18nText(BaseModel):
    model_config = ConfigDict(frozen=True)
    en: str
    hi: str


class FactSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str
    type: FactType
    label: I18nText
    group: str
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    integer: bool = False
    values: tuple[str, ...] = ()
    value_labels: dict[str, I18nText] = Field(default_factory=dict)
    note: str | None = None
    evidence_must_include: tuple[str, ...] = ()


class InvalidFactValue(ValueError):
    pass


def normalise_value(spec: FactSpec, value: object) -> FactValue | None:
    """Check ``value`` against the registry spec. Returns None for unknown.

    Raises InvalidFactValue for anything else that does not fit the spec.
    """
    if value is None or value == UNKNOWN:
        return None
    if spec.type is FactType.tristate:
        if value in (YES, NO):
            return str(value)
        raise InvalidFactValue(f"{spec.key}: tristate must be yes, no or unknown, got {value!r}")
    if spec.type is FactType.number:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise InvalidFactValue(f"{spec.key}: expected a number, got {value!r}")
        if spec.integer and float(value) != int(value):
            raise InvalidFactValue(f"{spec.key}: expected a whole number, got {value!r}")
        if spec.min is not None and value < spec.min:
            raise InvalidFactValue(f"{spec.key}: {value} is below the minimum {spec.min}")
        if spec.max is not None and value > spec.max:
            raise InvalidFactValue(f"{spec.key}: {value} is above the maximum {spec.max}")
        return int(value) if spec.integer else value
    if value in spec.values:
        return str(value)
    raise InvalidFactValue(f"{spec.key}: {value!r} is not one of {list(spec.values)}")


class Fact(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str
    value: FactValue | None = None
    status: FactStatus = FactStatus.suggested
    origin: FactOrigin = FactOrigin.manual
    source_span: str | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None


def confirmed_values(facts: Iterable[Fact] | Mapping[str, Fact]) -> dict[str, FactValue]:
    """The only view of facts the rules engine sees: confirmed, known values.

    Suggested, rejected and unknown facts are all absent, i.e. unknown to the engine.
    """
    items = facts.values() if isinstance(facts, Mapping) else facts
    out: dict[str, FactValue] = {}
    for f in items:
        if f.status is FactStatus.confirmed and f.value is not None and f.value != UNKNOWN:
            out[f.key] = f.value
    return out
