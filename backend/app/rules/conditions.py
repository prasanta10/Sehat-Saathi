"""Three-valued evaluation of rule conditions.

A condition over facts is TRUE, FALSE or UNDETERMINED (``None``). It is undetermined when a fact
it needs is unknown and the known facts do not settle it. A rule only fires when its condition
is definitely TRUE, and an undetermined condition can never be read as FALSE by the engine — that
is how "unknown stays unknown" is enforced.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.facts import FactValue

Tri = bool | None
_OPS = ("eq", "in", "gte", "lte", "gt", "lt")


def _leaf(value: FactValue | None, spec: Any) -> Tri:
    if value is None:
        return None
    if not isinstance(spec, dict):
        return bool(value == spec)
    results: list[bool] = []
    for op, arg in spec.items():
        if op == "eq":
            results.append(value == arg)
        elif op == "in":
            results.append(value in arg)
        else:
            if isinstance(value, str):
                # Content validation forbids comparisons on non-numeric facts.
                raise TypeError(f"numeric comparison {op!r} on non-numeric value {value!r}")
            if op == "gte":
                results.append(value >= arg)
            elif op == "lte":
                results.append(value <= arg)
            elif op == "gt":
                results.append(value > arg)
            elif op == "lt":
                results.append(value < arg)
            else:
                raise ValueError(f"unknown operator {op!r}")
    return all(results)


def tri_all(values: list[Tri]) -> Tri:
    if any(v is False for v in values):
        return False
    if any(v is None for v in values):
        return None
    return True


def tri_any(values: list[Tri]) -> Tri:
    if any(v is True for v in values):
        return True
    if any(v is None for v in values):
        return None
    return False


def evaluate(cond: Mapping[str, Any], facts: Mapping[str, FactValue]) -> Tri:
    parts: list[Tri] = []
    for key, spec in cond.items():
        if key == "all":
            parts.append(tri_all([evaluate(c, facts) for c in spec]))
        elif key == "any":
            parts.append(tri_any([evaluate(c, facts) for c in spec]))
        elif key == "not":
            inner = evaluate(spec, facts)
            parts.append(None if inner is None else not inner)
        else:
            parts.append(_leaf(facts.get(key), spec))
    return tri_all(parts)


def referenced_facts(cond: Mapping[str, Any]) -> list[str]:
    """Fact keys used by a condition, in first-use order, without duplicates."""
    out: list[str] = []

    def walk(c: Mapping[str, Any]) -> None:
        for key, spec in c.items():
            if key in ("all", "any"):
                for sub in spec:
                    walk(sub)
            elif key == "not":
                walk(spec)
            elif key not in out:
                out.append(key)

    walk(cond)
    return out


def unknown_facts(cond: Mapping[str, Any], facts: Mapping[str, FactValue]) -> list[str]:
    """Facts that are unknown and referenced by an undetermined condition."""
    return [k for k in referenced_facts(cond) if k not in facts]


def is_operator(spec: Any) -> bool:
    return isinstance(spec, dict) and bool(spec) and set(spec) <= set(_OPS)
