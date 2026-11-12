"""Hypothesis strategies that generate valid confirmed-fact sets for a RuleSet."""

from __future__ import annotations

from typing import Any

from hypothesis import strategies as st

from app.domain.facts import FactSpec, FactType, FactValue
from app.rules.conditions import referenced_facts
from app.rules.loader import RuleSet


def _numeric_thresholds(cond: Any, out: dict[str, set[float]]) -> None:
    if not isinstance(cond, dict):
        return
    for key, spec in cond.items():
        if key in ("all", "any"):
            for sub in spec:
                _numeric_thresholds(sub, out)
        elif key == "not":
            _numeric_thresholds(spec, out)
        elif isinstance(spec, dict):
            for op, arg in spec.items():
                if op in ("gte", "lte", "gt", "lt"):
                    out.setdefault(key, set()).update({arg - 1, arg, arg + 1})


def _conditions(rs: RuleSet) -> list[Any]:
    conds: list[Any] = []
    for p in rs.pathways.values():
        conds.append(p.applies_when)
        conds += [d.when for d in p.danger_signs] + [r.when for r in p.rules]
        conds += [q.ask_when for q in p.questions if q.ask_when]
        if p.low_care:
            conds.append(p.low_care.when)
    return conds


def relevant_keys(rs: RuleSet) -> list[str]:
    keys: list[str] = [s.fact for s in rs.danger_signs.signs]
    for p in rs.pathways.values():
        keys += [q.fact for q in p.questions]
    for c in _conditions(rs):
        keys += referenced_facts(c)
    return list(dict.fromkeys(keys))


def value_strategy(spec: FactSpec, thresholds: set[float]) -> st.SearchStrategy[FactValue]:
    if spec.type is FactType.tristate:
        return st.sampled_from(["yes", "no"])
    if spec.type is FactType.enum:
        return st.sampled_from(list(spec.values))
    lo = spec.min if spec.min is not None else 0
    hi = spec.max if spec.max is not None else 1000
    edge = sorted({int(v) for v in thresholds | {lo, hi} if lo <= v <= hi})
    return st.one_of(st.sampled_from(edge), st.integers(int(lo), int(hi)))


def fact_sets(rs: RuleSet) -> st.SearchStrategy[dict[str, FactValue]]:
    thresholds: dict[str, set[float]] = {}
    for c in _conditions(rs):
        _numeric_thresholds(c, thresholds)
    parts = {
        k: st.one_of(st.none(), value_strategy(rs.registry.facts[k], thresholds.get(k, set())))
        for k in relevant_keys(rs)
    }
    return st.fixed_dictionaries(parts).map(lambda d: {k: v for k, v in d.items() if v is not None})


def pathway_choice(rs: RuleSet) -> st.SearchStrategy[str | None]:
    return st.sampled_from([None, *sorted(rs.pathways)])
