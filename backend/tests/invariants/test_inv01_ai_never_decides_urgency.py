"""Invariant 1: AI never decides urgency.

Urgency comes only from the deterministic engine acting on worker-confirmed facts. Suggested
(AI-extracted) facts must have no effect on the result until the worker confirms them.
"""

import ast
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.facts import Fact, FactOrigin, FactStatus, confirmed_values
from app.rules.loader import RuleSet
from app.rules.schema import Urgency
from tests.invariants.helpers import triage
from tests.strategies import fact_sets, pathway_choice

RULES_DIR = Path(__file__).resolve().parents[2] / "app" / "rules"


@settings(max_examples=300, deadline=None)
@given(data=st.data())
def test_unconfirmed_facts_never_change_the_result(ruleset: RuleSet, data: st.DataObject) -> None:
    confirmed = data.draw(fact_sets(ruleset))
    noise = data.draw(fact_sets(ruleset))
    status = data.draw(
        st.sampled_from([FactStatus.suggested, FactStatus.rejected, FactStatus.unknown])
    )
    pathway = data.draw(pathway_choice(ruleset))
    facts = [Fact(key=k, value=v, status=FactStatus.confirmed) for k, v in confirmed.items()]
    facts += [
        Fact(key=k, value=v, status=status, origin=FactOrigin.extracted)
        for k, v in noise.items()
        if k not in confirmed
    ]
    with_noise = triage(ruleset, confirmed_values(facts), pathway)
    without = triage(ruleset, confirmed, pathway)
    assert with_noise == without


def test_suggested_danger_sign_alone_is_not_an_emergency(ruleset: RuleSet) -> None:
    sign = ruleset.danger_signs.signs[0]
    suggested = [
        Fact(key=sign.fact, value="yes", status=FactStatus.suggested, origin=FactOrigin.extracted)
    ]
    assert triage(ruleset, confirmed_values(suggested), None).urgency is not Urgency.EMERGENCY
    confirmed = [Fact(key=sign.fact, value="yes", status=FactStatus.confirmed)]
    assert triage(ruleset, confirmed_values(confirmed), None).urgency is Urgency.EMERGENCY


def test_rules_engine_does_not_import_ai_or_io() -> None:
    forbidden = (
        "app.ai",
        "app.schemes",
        "app.store",
        "app.api",
        "httpx",
        "requests",
        "openai",
        "random",
        "time",
        "datetime",
    )
    for path in RULES_DIR.glob("*.py"):
        if path.name == "loader.py":
            continue  # reads content files at startup; evaluate() never calls it
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not name.startswith(forbidden), f"{path.name} imports {name}"
