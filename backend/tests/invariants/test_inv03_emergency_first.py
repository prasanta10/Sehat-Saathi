"""Invariant 3: Emergency first.

Any confirmed danger sign gives EMERGENCY immediately, even with every other fact missing, with
or without a pathway. Evaluation is deterministic and independent of input order.
"""

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from app.rules.engine import LEVEL_RANK
from app.rules.loader import RuleSet
from app.rules.schema import Urgency
from tests.invariants.helpers import triage
from tests.strategies import fact_sets, pathway_choice


def test_each_universal_sign_alone_is_an_emergency(ruleset: RuleSet) -> None:
    for sign in ruleset.danger_signs.signs:
        for pid in [None, *ruleset.pathways]:
            r = triage(ruleset, {sign.fact: "yes"}, pid)
            assert r.urgency is Urgency.EMERGENCY, (sign.id, pid)
            assert sign.id in r.fired_rule_ids


@settings(max_examples=400, deadline=None)
@given(data=st.data())
def test_any_confirmed_danger_sign_wins(ruleset: RuleSet, data: st.DataObject) -> None:
    facts = data.draw(fact_sets(ruleset))
    sign = data.draw(st.sampled_from(ruleset.danger_signs.signs))
    facts[sign.fact] = "yes"
    assert triage(ruleset, facts, data.draw(pathway_choice(ruleset))).urgency is Urgency.EMERGENCY


@settings(max_examples=300, deadline=None)
@given(data=st.data())
def test_adding_a_danger_sign_never_lowers_urgency(ruleset: RuleSet, data: st.DataObject) -> None:
    facts = data.draw(fact_sets(ruleset))
    pid = data.draw(pathway_choice(ruleset))
    before = triage(ruleset, facts, pid)
    sign = data.draw(st.sampled_from(ruleset.danger_signs.signs))
    after = triage(ruleset, {**facts, sign.fact: "yes"}, pid)
    assert LEVEL_RANK[after.urgency] >= LEVEL_RANK[before.urgency]


@settings(max_examples=300, deadline=None)
@given(data=st.data(), seed=st.integers(0, 2**32 - 1))
def test_deterministic_and_order_independent(
    ruleset: RuleSet, data: st.DataObject, seed: int
) -> None:
    facts = data.draw(fact_sets(ruleset))
    pid = data.draw(pathway_choice(ruleset))
    items = list(facts.items())
    random.Random(seed).shuffle(items)
    assert triage(ruleset, facts, pid) == triage(ruleset, dict(items), pid)


def test_pathway_danger_signs_are_asked_before_anything_else(ruleset: RuleSet) -> None:
    from app.rules.conditions import referenced_facts

    for pid, p in ruleset.pathways.items():
        if not p.danger_signs:
            continue
        ds_facts = {k for d in p.danger_signs for k in referenced_facts(d.when)}
        missing = triage(ruleset, {}, pid).missing_fact_keys
        first = missing[: len(ds_facts)]
        assert set(first) <= ds_facts, (pid, missing)
