"""Extraction orchestration: call the model, validate, verify evidence, normalise numbers.

Guarantees (tested):
- Output is validated with Pydantic; on failure one retry, then a degraded result (manual entry).
- A non-null value survives only if its evidence is a span actually present in the transcript.
- Durations and numbers are converted by deterministic code, never by the model.
- Unknown keys, wrong types and invented pathways are dropped.
"""

from __future__ import annotations

import difflib
import logging
import re
import unicodedata
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.ai import prompts
from app.ai.interfaces import ExtractionOutput, Extractor, ProviderError
from app.ai.parsing import (
    SPELLING_FOLD,
    count_quantities,
    has_negation,
    parse_duration_days,
    parse_number,
)
from app.domain.facts import FactSpec, FactType, FactValue

log = logging.getLogger("sehat.ai")


@dataclass(frozen=True)
class SuggestedFact:
    key: str
    value: FactValue
    evidence: str
    approximate: bool = False


# AI may suggest "yes" for these (it can only raise urgency), never "no": a danger sign or red
# flag is ruled out only by the worker asking. Misattributed "no" evidence was seen in evals.
YES_ONLY_GROUPS = ("danger_sign", "red_flag")


@dataclass
class ExtractionResult:
    degraded: bool
    reason: str | None = None
    facts: list[SuggestedFact] = field(default_factory=list)
    discarded: int = 0
    withheld_denials: int = 0
    suggested_pathways: list[str] = field(default_factory=list)
    unparsed_concerns: list[str] = field(default_factory=list)
    attempts: int = 0
    provider: str = ""
    model_rev: str = ""
    prompt_version: str = prompts.EXTRACT_PROMPT_VERSION


# Spelling varies in speech transcripts (खांसी / खाँसी / खासी, वॉमिटिंग / वोमिटिंग): the same
# spelling fold as the parsers is applied when checking that evidence talks about a fact.
def _loose(text: str) -> str:
    return unicodedata.normalize("NFC", text).translate(SPELLING_FOLD).lower()


def mentions(evidence: str, patterns: tuple[str, ...] | list[str]) -> bool:
    ev = _loose(evidence)
    return any(re.search(_loose(p), ev, re.IGNORECASE) for p in patterns)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def find_span(phrase: str | None, transcript: str, min_ratio: float = 0.9) -> str | None:
    """The transcript's own words matching ``phrase``: exact, or near-exact for phrases of 8+
    characters (models sometimes miscopy one Devanagari letter, e.g. हफ्टे for हफ्ते).
    Comparison ignores case, spacing, nasal marks and the nukta. Returns None if absent."""
    if not phrase or not phrase.strip():
        return None
    p, t = _loose(_norm(phrase)), _loose(_norm(transcript))
    if p in t:
        return p
    if len(p) < 8:
        return None
    best, best_ratio = None, 0.0
    for size in range(max(1, len(p) - 2), len(p) + 3):
        for i in range(0, max(1, len(t) - size + 1)):
            window = t[i : i + size]
            ratio = difflib.SequenceMatcher(None, p, window).ratio()
            if ratio > best_ratio:
                best, best_ratio = window, ratio
    return best if best_ratio >= min_ratio else None


def evidence_in(evidence: str | None, transcript: str) -> bool:
    return find_span(evidence, transcript) is not None


def verify(
    output: ExtractionOutput, transcript: str, specs: dict[str, FactSpec], pathways: list[str]
) -> ExtractionResult:
    result = ExtractionResult(degraded=False)
    seen: set[str] = set()
    for f in output.facts:
        if f.value is None:
            continue  # not mentioned: stays unknown
        spec = specs.get(f.key)
        if spec is None or f.key in seen or not evidence_in(f.evidence, transcript):
            result.discarded += 1
            continue
        assert f.evidence is not None
        value: FactValue | None
        approximate = False
        if spec.evidence_must_include and not mentions(f.evidence, spec.evidence_must_include):
            result.discarded += 1  # evidence does not talk about what this fact needs
            continue
        if spec.type is FactType.tristate:
            value = f.value if f.value in ("yes", "no") else None
            if value == "no" and spec.group in YES_ONLY_GROUPS:
                result.withheld_denials += 1
                continue
            # The quoted words must agree with the answer: "no" needs a negation, "yes" must not
            # have one. Disagreement means the model is unsure or misattributed: leave unknown.
            if value is not None and (value == "no") != has_negation(f.evidence):
                result.discarded += 1
                continue
        elif spec.type is FactType.enum:
            value = f.value if f.value in spec.values else None
        else:
            spoken = find_span(f.value, transcript)
            if spoken is None:
                # The model miscopied the phrase: fall back to its evidence, in the transcript's own
                # words, but only if that span holds exactly one quantity (so nothing is guessed).
                ev_span = find_span(f.evidence, transcript)
                if ev_span is not None and count_quantities(ev_span) == 1:
                    spoken = ev_span
            if spoken is None:
                value = None  # the phrase itself must have been said
            elif count_quantities(f.evidence) > 1 and count_quantities(f.value) < count_quantities(
                f.evidence
            ):
                # The evidence holds more than one quantity ("do ya teen hafte"): the model picked
                # one. Ambiguous, so unknown; the worker asks.
                value = None
            elif spec.unit == "days":
                parsed = parse_duration_days(spoken)  # the transcript's words, not the model's
                value, approximate = (parsed.value, parsed.approximate) if parsed else (None, False)
            else:
                value = parse_number(spoken)
            if value is not None and isinstance(value, float) and value == int(value):
                value = int(value)
            if value is not None and spec.integer and value != int(value):
                value, approximate = round(value), True
            if value is not None and (
                (spec.min is not None and value < spec.min)
                or (spec.max is not None and value > spec.max)
            ):
                value = None
        if value is None:
            result.discarded += 1
            continue
        seen.add(f.key)
        result.facts.append(
            SuggestedFact(
                key=f.key, value=value, evidence=f.evidence.strip(), approximate=approximate
            )
        )
    # A stated duration means the symptom is present: drop a contradicting "no".
    by_key = {sf.key: sf for sf in result.facts}
    for sf in list(result.facts):
        if sf.key.endswith("_duration_days") and sf.value:
            present = by_key.get(sf.key.removesuffix("_duration_days") + "_present")
            if present is not None and present.value == "no":
                result.facts.remove(present)
                result.discarded += 1
    result.suggested_pathways = [p for p in output.suggested_pathways if p in pathways]
    result.unparsed_concerns = [c for c in output.unparsed_concerns if evidence_in(c, transcript)]
    return result


async def extract(
    extractor: Extractor,
    transcript: str,
    language: str,
    specs: list[FactSpec],
    pathways: list[str],
) -> ExtractionResult:
    by_key = {s.key: s for s in specs}
    reason = "unknown"
    for attempt in (1, 2):
        try:
            raw = await extractor.extract(transcript, language, specs, pathways)
            output = ExtractionOutput.model_validate_json(raw)
        except ProviderError:
            reason = "provider_unavailable"
            log.warning(
                "extraction provider failed", extra={"provider": extractor.name, "attempt": attempt}
            )
            continue
        except ValidationError:
            reason = "invalid_output"
            log.warning(
                "extraction output failed validation",
                extra={"provider": extractor.name, "attempt": attempt},
            )
            continue
        result = verify(output, transcript, by_key, pathways)
        result.attempts = attempt
        result.provider, result.model_rev = extractor.name, extractor.model_rev
        return result
    return ExtractionResult(
        degraded=True,
        reason=reason,
        attempts=2,
        provider=extractor.name,
        model_rev=extractor.model_rev,
    )
