"""Invariant 5: no diagnosis, no treatment advice; and (outputs part of) invariant 6: no money.

Template outputs for every golden case are generated and scanned: family instructions contain no
disease, medicine or money terms at all; the clinician note contains no medicine or money terms
and names a condition only inside a cited rule line (e.g. "needs a TB test", never a conclusion).
"""

import re

import pytest

from app.config import REPO_ROOT
from app.outputs.checks import _patterns
from app.outputs.templates import OutputContext, clinician_handoff, family_instructions, strings
from app.rules.engine import evaluate
from app.rules.loader import load_ruleset
from tests.golden.test_golden import _cases

RULES = load_ruleset(REPO_ROOT)
CONCLUSIONS = re.compile(
    r"(has|suffering from|diagnosed with|confirmed)\s+(tb|tuberculosis)|को टीबी है|निदान हुआ", re.I
)


def _contexts():  # type: ignore[no-untyped-def]
    for pathway, case in _cases():
        p = RULES.pathway(pathway) if pathway else None
        r = evaluate(case["facts"], p, RULES.danger_signs, RULES.version)
        for lang in ("en", "hi"):
            yield (
                case["id"],
                lang,
                OutputContext(
                    language=lang,
                    person_name="Synthetic",
                    age_years=40,
                    sex="female",
                    village="Testpur",
                    pathway_title=p.title.model_dump() if p else None,
                    facts=case["facts"],
                    unknown_keys=list(r.missing_fact_keys),
                    result=r,
                    bring=list(p.referral.bring) if p else [],
                ),
            )


@pytest.mark.parametrize(
    ("case_id", "lang", "ctx"), list(_contexts()), ids=lambda v: v if isinstance(v, str) else ""
)
def test_outputs_contain_no_diagnosis_treatment_or_money(
    case_id: str, lang: str, ctx: OutputContext
) -> None:
    # The mandated fixed lines ("This is not a diagnosis...") are removed before scanning.
    # Fact labels are reviewed registry content describing what the family reported (e.g.
    # "Has had TB before"), not conclusions; they are removed too. Conclusion phrasing is
    # checked separately below, outside those labels.
    fixed = [strings()[k][lang] for k in ("not_diagnosis", "not_diagnosis_note")]
    fixed += sorted(
        (getattr(f.label, lang) for f in RULES.registry.facts.values()), key=len, reverse=True
    )

    def strip(text: str) -> str:
        for f in fixed:
            text = text.replace(f, "")
        return text

    fam = strip(family_instructions(ctx, lang))
    full_note = clinician_handoff(ctx, RULES, lang)
    note = strip(full_note)
    pats = _patterns()
    for group in ("disease_terms", "medicine_terms", "money_terms"):
        for p in pats[group]:
            assert not p.search(fam), (group, p.pattern, fam)
    for group in ("medicine_terms", "money_terms"):
        for p in pats[group]:
            assert not p.search(note), (group, p.pattern)
    non_rule_lines = [ln for ln in note.splitlines() if not ln.startswith(("Rule:", "नियम:"))]
    for p in pats["disease_terms"]:
        for ln in non_rule_lines:
            assert not p.search(ln), (p.pattern, ln)
    for ln in non_rule_lines:
        assert not CONCLUSIONS.search(strip(ln)), ln
