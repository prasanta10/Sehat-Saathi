"""Invariant 2: Unknown stays unknown. Missing essential facts give INCOMPLETE, never LOW."""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.rules import conditions
from app.rules.loader import RuleSet
from app.rules.schema import Urgency
from tests.invariants.helpers import triage
from tests.strategies import fact_sets


@settings(max_examples=400, deadline=None)
@given(data=st.data())
def test_missing_required_fact_never_gives_low(ruleset: RuleSet, data: st.DataObject) -> None:
    pathway_id = data.draw(st.sampled_from(sorted(ruleset.pathways)))
    pathway = ruleset.pathway(pathway_id)
    facts = data.draw(fact_sets(ruleset))
    required = [q for q in pathway.questions if q.required]
    q = data.draw(st.sampled_from(required))
    facts.pop(q.fact, None)
    if q.ask_when is not None and conditions.evaluate(q.ask_when, facts) is False:
        return  # the question does not apply to this person
    assert triage(ruleset, facts, pathway_id).urgency is not Urgency.LOW


@settings(max_examples=400, deadline=None)
@given(data=st.data())
def test_forgetting_any_fact_never_produces_low(ruleset: RuleSet, data: st.DataObject) -> None:
    """If the full fact set is not LOW, no subset of it may be LOW either."""
    pathway_id = data.draw(st.sampled_from(sorted(ruleset.pathways)))
    facts = data.draw(fact_sets(ruleset))
    if triage(ruleset, facts, pathway_id).urgency is Urgency.LOW:
        return
    kept = data.draw(st.sets(st.sampled_from(sorted(facts)) if facts else st.nothing()))
    subset = {k: v for k, v in facts.items() if k in kept}
    assert triage(ruleset, subset, pathway_id).urgency is not Urgency.LOW


def test_no_facts_is_incomplete_for_every_pathway(ruleset: RuleSet) -> None:
    for pid in ruleset.pathways:
        r = triage(ruleset, {}, pid)
        assert r.urgency is Urgency.INCOMPLETE
        assert r.missing_fact_keys, pid


def test_pathway_without_low_care_can_never_return_low(ruleset: RuleSet) -> None:
    for pathway in ruleset.pathways.values():
        if pathway.low_care is None:
            assert all(r.level is not Urgency.LOW for r in pathway.rules)


@settings(max_examples=300, deadline=None)
@given(data=st.data())
def test_low_only_from_an_explicit_low_rule(ruleset: RuleSet, data: st.DataObject) -> None:
    pathway_id = data.draw(st.sampled_from(sorted(ruleset.pathways)))
    r = triage(ruleset, data.draw(fact_sets(ruleset)), pathway_id)
    if r.urgency is Urgency.LOW:
        low = ruleset.pathway(pathway_id).low_care
        assert low is not None and r.fired_rule_ids == (low.id,)
