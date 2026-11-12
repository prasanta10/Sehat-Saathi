"""Deterministic mock providers. No model, no network, no downloads.

The mock extractor answers from fixtures (exact transcript match) and otherwise from a small
keyword lexicon. It goes through exactly the same validation and evidence checks as a real
model. It exists for development and tests; it is not an extraction method.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.ai.interfaces import ExtractedFact, ExtractionOutput, Transcript
from app.ai.parsing import normalise
from app.content.yamlio import load_yaml
from app.domain.facts import FactSpec

FIXTURES = Path(__file__).parent / "mock_fixtures.yaml"

# Word boundaries via whitespace: `\b` fails after Devanagari vowel signs (e.g. the ं in नहीं).
_NEG = r"(?:^|\s)(?:nahi|nahin|nahee|na|no|not|नहीं|नही|ना)(?=\s|$)"
_DURATION = (
    r"((?:\d+|[०-९]+|ek|do|teen|tin|char|chaar|paanch|panch|chhe|saat|aath|nau|das|dus|bees|"
    r"one|two|three|four|five|six|seven|ten|a|एक|दो|तीन|चार|पांच|पाँच|छह|सात|आठ|दस|बीस)\s+"
    r"(?:din|dino|dinon|days?|hafte|hafta|haftey|weeks?|mahina|mahine|months?|दिन|दिनों|हफ़्ते|हफ्ते|हफ़्ता|हफ्ता|महीना|महीने))"
)

# fact key -> keyword patterns (lowercase); each mention yields yes, or no if negated nearby.
LEXICON: dict[str, list[str]] = {
    "cough_present": [r"khansi", r"khaansi", r"खांसी", r"खाँसी", r"cough"],
    "fever_present": [r"bukhar", r"bukhaar", r"बुखार", r"fever"],
    "blood_in_sputum": [r"balgam me[nm]? khoon", r"khoon", r"बलगम में खून", r"खून", r"blood"],
    "night_sweats": [r"raat (ko )?pasina", r"रात (को )?पसीना", r"night sweat"],
    "significant_weight_loss": [
        r"[wv]ajan (nahi[n]? )?(kam|ghat)",
        r"वज़न (नहीं )?(कम|घट)",
        r"वजन (नहीं )?(कम|घट)",
        r"weight loss",
        r"lost weight",
    ],
    "tb_household_contact": [r"ghar mei?n? .{0,20}(tb|टीबी)", r"घर में .{0,20}टीबी"],
    "past_tb": [r"pehle .{0,15}(tb|टीबी)", r"पहले .{0,15}टीबी"],
}
DURATION_OF = {"cough_duration_days": "cough_present", "fever_duration_days": "fever_present"}
CONCERNS = [
    r"kiraya",
    r"kiraaya",
    r"bus",
    r"paisa",
    r"paise",
    r"किराया",
    r"पैसे",
    r"मज़दूरी",
    r"mazdoori",
    r"dihadi",
]


def _clauses(text: str) -> list[str]:
    return [
        c.strip()
        for c in re.split(r"[.,;।!?\n]|\baur\b|\bपर\b|\bलेकिन\b|\blekin\b|\bpar\b", text)
        if c.strip()
    ]


def lexicon_extract(transcript: str, keys: set[str], pathways: list[str]) -> ExtractionOutput:
    facts: dict[str, ExtractedFact] = {}
    for clause in _clauses(transcript):
        low = clause.lower()
        for key, patterns in LEXICON.items():
            if key not in keys or key in facts:
                continue
            for pat in patterns:
                m = re.search(pat, low)
                if not m:
                    continue
                # A negation just before, inside or shortly after the mention negates it.
                window = low[max(0, m.start() - 8) : m.end() + 25]
                negated = re.search(_NEG, window) is not None
                facts[key] = ExtractedFact(
                    key=key, value="no" if negated else "yes", evidence=clause
                )
                break
        for dkey, parent in DURATION_OF.items():
            if (
                dkey in keys
                and dkey not in facts
                and any(re.search(p, clause.lower()) for p in LEXICON[parent])
            ):
                d = re.search(_DURATION, clause.lower())
                if d:
                    facts[dkey] = ExtractedFact(key=dkey, value=d.group(1), evidence=clause)
    out_facts = [
        facts.get(k, ExtractedFact(key=k, value=None, evidence=None)) for k in sorted(keys)
    ]
    concerns = [c for c in _clauses(transcript) if any(re.search(p, c.lower()) for p in CONCERNS)]
    suggested = [
        p
        for p in pathways
        if p == "adult_cough"
        and facts.get("cough_present")
        and facts["cough_present"].value == "yes"
    ]
    complaints = [
        k.replace("_present", "")
        for k in ("cough_present", "fever_present")
        if k in facts and facts[k].value == "yes"
    ]
    return ExtractionOutput(
        chief_complaints=complaints,
        facts=out_facts,
        suggested_pathways=suggested,
        unparsed_concerns=concerns,
    )


class MockExtractor:
    name = "mock"
    model_rev = "mock-lexicon-1"

    def __init__(self, fixtures: dict[str, Any] | None = None) -> None:
        if fixtures is None:
            fixtures = load_yaml(FIXTURES) if FIXTURES.exists() else {}
        self._fixtures = {normalise(k): v for k, v in (fixtures or {}).items()}

    async def extract(
        self, transcript: str, language: str, facts: list[FactSpec], pathways: list[str]
    ) -> str:
        fixture = self._fixtures.get(normalise(transcript))
        if fixture is not None:
            return fixture if isinstance(fixture, str) else json.dumps(fixture, ensure_ascii=False)
        return lexicon_extract(transcript, {f.key for f in facts}, pathways).model_dump_json()


MOCK_TRANSCRIPT = {
    "hi": "[mock ASR] तीन हफ़्ते से खांसी है, बुखार नहीं है।",
    "en": "[mock ASR] Cough for three weeks, no fever.",
}


class MockASR:
    """Returns a fixture transcript by audio hash, else a fixed synthetic sentence that is clearly
    labelled as a mock. The worker can edit it like any transcript."""

    name = "mock"

    def __init__(self, transcripts: dict[str, str] | None = None) -> None:
        self._transcripts = transcripts or {}

    async def transcribe(self, audio: bytes, language: str) -> Transcript:
        import hashlib

        digest = hashlib.sha256(audio).hexdigest()
        text = self._transcripts.get(digest, MOCK_TRANSCRIPT.get(language, MOCK_TRANSCRIPT["hi"]))
        return Transcript(text=text, language=language, provider="mock", model_rev="mock-asr-1")


class MockWriter:
    """Returns the template unchanged: outputs are complete and correct with no model."""

    name = "mock"
    model_rev = "identity"

    async def rewrite(self, kind: str, language: str, text: str) -> str:
        return text
