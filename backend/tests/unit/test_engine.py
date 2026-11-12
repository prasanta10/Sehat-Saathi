"""Engine semantics on synthetic fixture content (tests/fixtures/content)."""

from app.rules.engine import Reason, evaluate
from app.rules.loader import RuleSet
from app.rules.schema import Urgency

# Everything a decision could depend on is known.
# fx_optional is "no", which settles fx.high_optional.
COMPLETE_MEDIUM = {
    "age_years": 40,
    "fx_symptom": "yes",
    "fx_severe": "no",
    "fx_marker_high": "no",
    "fx_duration_days": 12,
    "fx_optional": "no",
}


def run(rs: RuleSet, facts: dict, pathway: str | None = "fx_with_low"):  # type: ignore[no-untyped-def,type-arg]
    return evaluate(facts, rs.pathway(pathway) if pathway else None, rs.danger_signs, rs.version)


def test_universal_danger_sign_with_nothing_else_known(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {"fx_universal_b": "yes"})
    assert r.urgency is Urgency.EMERGENCY
    assert r.reason is Reason.danger_sign
    assert r.fired_rule_ids == ("fx.universal_b",)
    assert r.source_refs[0].ref == "fixture_ref"


def test_danger_sign_without_a_pathway(fixture_rules: RuleSet) -> None:
    assert run(fixture_rules, {"fx_universal_a": "yes"}, None).urgency is Urgency.EMERGENCY


def test_all_present_danger_signs_are_reported(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {"fx_universal_a": "yes", "fx_universal_b": "yes", "fx_severe": "yes"})
    assert set(r.fired_rule_ids) == {"fx.universal_a", "fx.universal_b", "fx.severe"}


def test_pathway_danger_sign(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {"fx_severe": "yes"})
    assert r.urgency is Urgency.EMERGENCY
    assert r.fired_rule_ids == ("fx.severe",)


def test_no_pathway_and_no_danger_sign_is_incomplete(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {}, None)
    assert (r.urgency, r.reason) == (Urgency.INCOMPLETE, Reason.no_pathway)


def test_empty_facts_are_incomplete_and_danger_signs_are_asked_first(
    fixture_rules: RuleSet,
) -> None:
    r = run(fixture_rules, {})
    assert r.urgency is Urgency.INCOMPLETE
    assert r.missing_fact_keys[0] == "fx_severe"
    assert set(r.missing_fact_keys) >= {
        "fx_severe",
        "age_years",
        "fx_symptom",
        "fx_marker_high",
        "fx_duration_days",
    }


def test_medium(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, COMPLETE_MEDIUM)
    assert (r.urgency, r.fired_rule_ids) == (Urgency.MEDIUM, ("fx.medium",))
    assert r.facility_level == "PHC"
    assert r.target_window == "within_3_days"


def test_medium_boundary(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {**COMPLETE_MEDIUM, "fx_duration_days": 9})
    assert r.urgency is Urgency.INCOMPLETE
    assert r.reason is Reason.no_rule_matched


def test_high_shown_even_when_other_required_facts_missing(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {"age_years": 40, "fx_symptom": "yes", "fx_marker_high": "yes"})
    assert r.urgency is Urgency.HIGH
    assert r.fired_rule_ids == ("fx.high",)
    # Still asks the questions that could make it an emergency.
    assert r.missing_fact_keys[0] == "fx_severe"
    assert "fx_duration_days" in r.missing_fact_keys


def test_medium_with_missing_required_is_incomplete_with_floor(fixture_rules: RuleSet) -> None:
    facts = {**COMPLETE_MEDIUM}
    del facts["fx_marker_high"]
    r = run(fixture_rules, facts)
    assert r.urgency is Urgency.INCOMPLETE
    assert r.minimum_level is Urgency.MEDIUM
    assert r.missing_fact_keys == ("fx_marker_high",)


def test_optional_fact_that_could_raise_to_high_blocks_a_lower_result(
    fixture_rules: RuleSet,
) -> None:
    # fx.high_optional needs fx_optional AND fx_kind; with fx_optional=yes and kind unknown,
    # the HIGH rule is undetermined, so the answer cannot be MEDIUM yet.
    r = run(fixture_rules, {**COMPLETE_MEDIUM, "fx_optional": "yes"})
    assert r.urgency is Urgency.INCOMPLETE
    assert r.minimum_level is Urgency.MEDIUM
    assert r.missing_fact_keys == ("fx_kind",)
    # Once settled the other way, MEDIUM stands.
    r = run(fixture_rules, {**COMPLETE_MEDIUM, "fx_optional": "yes", "fx_kind": "alpha"})
    assert r.urgency is Urgency.MEDIUM


def test_explicit_low(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {**COMPLETE_MEDIUM, "fx_duration_days": 2})
    assert r.urgency is Urgency.LOW
    assert r.return_precautions is not None
    assert r.return_precautions.hi == ("परीक्षण सावधानी",)


def test_low_boundary_is_not_low(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {**COMPLETE_MEDIUM, "fx_duration_days": 3})
    assert r.urgency is Urgency.INCOMPLETE


def test_pathway_without_low_care_never_returns_low(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {"fx_symptom": "yes", "fx_duration_days": 1}, "fx_no_low")
    assert (r.urgency, r.reason) == (Urgency.INCOMPLETE, Reason.no_rule_matched)


def test_pathway_not_applicable(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {**COMPLETE_MEDIUM, "age_years": 10})
    assert (r.urgency, r.reason) == (Urgency.INCOMPLETE, Reason.pathway_not_applicable)
    assert r.minimum_level is Urgency.MEDIUM


def test_pathway_not_applicable_still_honours_danger_signs(fixture_rules: RuleSet) -> None:
    r = run(fixture_rules, {"age_years": 10, "fx_symptom": "yes", "fx_universal_a": "yes"})
    assert r.urgency is Urgency.EMERGENCY


def test_draft_content_is_flagged(fixture_rules: RuleSet) -> None:
    assert run(fixture_rules, COMPLETE_MEDIUM).review_status == "draft"


def test_ruleset_version_is_stable(fixture_rules: RuleSet) -> None:
    from app.rules.loader import load_ruleset
    from tests.conftest import FIXTURE_ROOT

    assert load_ruleset(FIXTURE_ROOT).version == fixture_rules.version
    assert fixture_rules.version.startswith("sha256:")
