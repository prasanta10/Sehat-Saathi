"""ASR metrics: word/character error rate and key-fact survival."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import unicodedata

from app.ai.parsing import normalise, parse_duration_days

_NEGATIONS = {"nahi", "nahin", "नहीं", "नही", "no", "not", "na"}


def _edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def strict(text: str) -> str:
    """Normalisation for error rates: keeps nasal marks and nukta, which ASR must get right."""
    text = unicodedata.normalize("NFC", text).lower()
    return re.sub(r"\s+", " ", re.sub(r"[.,!?।]", " ", text)).strip()


def wer(reference: str, hypothesis: str) -> float:
    ref = strict(reference).split()
    return _edit_distance(ref, strict(hypothesis).split()) / max(len(ref), 1)


def cer(reference: str, hypothesis: str) -> float:
    ref = list(strict(reference).replace(" ", ""))
    return _edit_distance(ref, list(strict(hypothesis).replace(" ", ""))) / max(len(ref), 1)


def key_facts(text: str) -> dict[str, object]:
    """The facts that matter most for safety: durations, numbers and negations, per clause."""
    clauses = [c for c in re.split(r"[.,;।!?]", text) if c.strip()]
    durations = sorted(d.value for c in clauses if (d := parse_duration_days(c)) is not None)
    negations = sum(1 for w in normalise(text).split() if w in _NEGATIONS)
    return {"durations": durations, "negations": negations}


def key_fact_survival(reference: str, hypothesis: str) -> bool:
    """True if every duration and negation in the reference survives transcription."""
    return key_facts(reference) == key_facts(hypothesis)
