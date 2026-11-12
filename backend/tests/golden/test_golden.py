"""Run golden cases and enforce per-rule coverage (firing / boundary / unknown)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.config import REPO_ROOT
from app.content.yamlio import load_yaml
from app.rules.engine import evaluate
from app.rules.loader import RuleSet, load_ruleset
from app.rules.schema import Urgency

GOLDEN_DIR = Path(__file__).parent


def _files() -> list[Path]:
    return sorted(GOLDEN_DIR.glob("*.yaml"))


def _cases() -> list[tuple[str, dict[str, Any]]]:
    """Cases with facts resolved: file ``base`` + case ``facts``, minus case ``unset``."""
    out = []
    for path in _files():
        doc = load_yaml(path)
        base = doc.get("base") or {}
        for case in doc["cases"]:
            facts = {} if case.get("no_base") else dict(base)
            facts.update(case.get("facts") or {})
            for key in case.get("unset", []):
                facts.pop(key)
            out.append((doc.get("pathway"), {**case, "facts": facts}))
    return out


@pytest.fixture(scope="module")
def rules() -> RuleSet:
    return load_ruleset(REPO_ROOT)


@pytest.mark.parametrize(
    ("pathway", "case"), _cases(), ids=lambda v: v["id"] if isinstance(v, dict) else str(v)
)
def test_golden_case(rules: RuleSet, pathway: str | None, case: dict[str, Any]) -> None:
    for key, value in case["facts"].items():
        from app.domain.facts import normalise_value

        assert normalise_value(rules.registry.facts[key], value) == value, (key, value)
    r = evaluate(
        case["facts"],
        rules.pathway(pathway) if pathway else None,
        rules.danger_signs,
        rules.version,
    )
    exp = case["expect"]
    assert r.urgency is Urgency(exp["urgency"]), r
    if "fired" in exp:
        assert set(r.fired_rule_ids) == set(exp["fired"]), r.fired_rule_ids
    if "reason" in exp:
        assert r.reason == exp["reason"]
    if "minimum_level" in exp:
        assert r.minimum_level == (Urgency(exp["minimum_level"]) if exp["minimum_level"] else None)
    for key in exp.get("missing_includes", []):
        assert key in r.missing_fact_keys, (key, r.missing_fact_keys)
    if "missing_first" in exp:
        assert r.missing_fact_keys[0] == exp["missing_first"], r.missing_fact_keys


def _has_numeric(cond: Any) -> bool:
    if not isinstance(cond, dict):
        return False
    for key, spec in cond.items():
        if key in ("all", "any") and any(_has_numeric(c) for c in spec):
            return True
        if key == "not" and _has_numeric(spec):
            return True
        if isinstance(spec, dict) and set(spec) & {"gte", "lte", "gt", "lt"}:
            return True
    return False


def test_every_rule_has_firing_boundary_and_unknown_cases(rules: RuleSet) -> None:
    covered: dict[tuple[str, str], int] = {}
    for _, case in _cases():
        for c in case.get("covers", []):
            covered[(c["rule"], c["kind"])] = covered.get((c["rule"], c["kind"]), 0) + 1
    problems = []
    for sign in rules.danger_signs.signs:
        if (sign.id, "firing") not in covered:
            problems.append(f"{sign.id}: no firing case")
    for p in rules.pathways.values():
        items: list[Any] = [*p.danger_signs, *p.rules] + ([p.low_care] if p.low_care else [])
        for item in items:
            needs = ["firing", "unknown"] + (["boundary"] if _has_numeric(item.when) else [])
            problems += [f"{item.id}: no {k} case" for k in needs if (item.id, k) not in covered]
    assert not problems, "\n".join(problems)


def test_covers_claims_are_true(rules: RuleSet) -> None:
    """A case that claims to cover a rule's firing must actually fire it."""
    for pathway, case in _cases():
        r = evaluate(
            case["facts"],
            rules.pathway(pathway) if pathway else None,
            rules.danger_signs,
            rules.version,
        )
        for c in case.get("covers", []):
            if c["kind"] == "firing":
                assert c["rule"] in r.fired_rule_ids, (case["id"], c)
            else:
                assert c["rule"] not in r.fired_rule_ids, (case["id"], c)
