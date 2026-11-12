"""Checks for any non-template output (LLM rewrite or worker edit preview).

A rewrite passes only if it keeps every required line verbatim and introduces no disease name,
medicine, dose or money term that the template did not already contain.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.config import REPO_ROOT
from app.content.yamlio import load_yaml


@lru_cache
def _patterns() -> dict[str, list[re.Pattern[str]]]:
    data = load_yaml(REPO_ROOT / "rules" / "output_checks.yaml")
    out: dict[str, list[re.Pattern[str]]] = {}
    for group in ("disease_terms", "medicine_terms", "money_terms"):
        out[group] = [
            re.compile(p, re.IGNORECASE) for lang in ("en", "hi") for p in data[group][lang]
        ]
    return out


def _hits(text: str, pattern: re.Pattern[str]) -> set[str]:
    return {m.group(0).lower() for m in pattern.finditer(text)}


def check_output(text: str, template: str, required: list[str]) -> list[str]:
    """Return failure codes; empty means the text may be used."""
    failures = [f"missing_required_line:{line[:40]}" for line in required if line not in text]
    for group, patterns in _patterns().items():
        for p in patterns:
            new = _hits(text, p) - _hits(template, p)
            if new:
                failures.append(f"{group}:{sorted(new)[0]}")
    return failures
