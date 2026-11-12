"""Every scheme's inclusion and exclusion conditions."""

import pytest

from app.config import REPO_ROOT
from app.rules.schema import Urgency
from app.schemes.matcher import Status, load_schemes, match

SCHEMES = load_schemes(REPO_ROOT)
U = Urgency


def run(urgency: Urgency = U.MEDIUM, state: str = "UP", tags: set[str] | None = None, **facts):  # type: ignore[no-untyped-def]
    return {
        c.scheme.id: c
        for c in match(
            SCHEMES, state=state, urgency=urgency, facts=facts, pathway_tags=tags or set()
        )
    }


ADULT = {"age_years": 40, "sex": "male", "pregnant": "no"}
WOMAN = {"age_years": 25, "sex": "female"}


def test_all_schemes_load() -> None:
    assert {s.id for s in SCHEMES} >= {
        "pmjay",
        "pmjay_70_plus",
        "jsy",
        "jssk",
        "pmmvy",
        "suman",
        "rbsk",
        "ntep_free_tb_care",
        "nikshay_poshan_yojana",
        "ambulance_108_102",
    }


# --- TB-related schemes: only on TB-tagged pathways ---------------------------------------
def test_tb_schemes_need_tb_pathway() -> None:
    assert "ntep_free_tb_care" in run(tags={"tb_related"}, **ADULT)
    assert "ntep_free_tb_care" not in run(tags=set(), **ADULT)


def test_nikshay_always_needs_confirmation() -> None:
    c = run(tags={"tb_related"}, **ADULT)["nikshay_poshan_yojana"]
    assert c.status is Status.needs_confirmation


def test_free_tb_care_is_possibly_relevant() -> None:
    assert run(tags={"tb_related"}, **ADULT)["ntep_free_tb_care"].status is Status.possibly_relevant


# --- PM-JAY ---------------------------------------------------------------------------------
def test_pmjay_not_applicable_for_outpatient_referral() -> None:
    c = run(U.MEDIUM, **ADULT)["pmjay"]
    assert c.status is Status.not_applicable and c.scheme.not_applicable_note is not None


@pytest.mark.parametrize("urgency", [U.HIGH, U.EMERGENCY])
def test_pmjay_needs_confirmation_for_hospital_care_when_card_unknown(urgency: Urgency) -> None:
    c = run(urgency, **ADULT)["pmjay"]
    assert c.status is Status.needs_confirmation and "ayushman_card_held" in c.unknown_facts


def test_pmjay_card_known_still_needs_confirming_membership() -> None:
    # Holding a card is a signal, never proof: the record lists what to confirm.
    assert (
        run(U.HIGH, ayushman_card_held="yes", **ADULT)["pmjay"].status is Status.needs_confirmation
    )


def test_pmjay_70_plus_by_age() -> None:
    assert "pmjay_70_plus" in run(U.HIGH, age_years=70, sex="male")
    assert "pmjay_70_plus" not in run(U.HIGH, age_years=69, sex="male")
    assert (
        run(U.HIGH, sex="male")["pmjay_70_plus"].status is Status.needs_confirmation
    )  # age unknown


def test_pmjay_70_plus_not_for_outpatient() -> None:
    assert run(U.MEDIUM, age_years=75)["pmjay_70_plus"].status is Status.not_applicable


# --- Pregnancy ------------------------------------------------------------------------------
@pytest.mark.parametrize("sid", ["jsy", "jssk", "pmmvy", "suman"])
def test_maternity_schemes_only_when_pregnant(sid: str) -> None:
    assert sid in run(U.MEDIUM, pregnant="yes", **WOMAN)
    assert sid not in run(U.MEDIUM, pregnant="no", **WOMAN)


@pytest.mark.parametrize("sid", ["jsy", "jssk", "pmmvy", "suman"])
def test_maternity_schemes_hidden_until_pregnancy_is_recorded(sid: str) -> None:
    assert sid not in run(U.MEDIUM, **WOMAN)


def test_maternity_schemes_with_conditions_need_confirmation() -> None:
    cards = run(U.MEDIUM, pregnant="yes", **WOMAN)
    assert cards["jsy"].status is Status.needs_confirmation  # rules differ by state
    assert cards["pmmvy"].status is Status.needs_confirmation  # category-based eligibility
    assert cards["jssk"].status is Status.possibly_relevant


def test_jssk_covers_sick_infants() -> None:
    assert "jssk" in run(U.HIGH, age_years=0, age_months=5)
    assert "jssk" not in run(U.HIGH, age_years=2, age_months=24, pregnant="no")


def test_pmmvy_excluded_states() -> None:
    assert "pmmvy" not in run(U.MEDIUM, state="TG", pregnant="yes", **WOMAN)
    assert "pmmvy" not in run(U.MEDIUM, state="OD", pregnant="yes", **WOMAN)
    assert "pmmvy" in run(U.MEDIUM, state="UP", pregnant="yes", **WOMAN)


# --- Children, transport --------------------------------------------------------------------
def test_rbsk_by_age() -> None:
    assert "rbsk" in run(U.MEDIUM, age_years=10)
    assert "rbsk" not in run(U.MEDIUM, age_years=19)


def test_ambulance_for_emergency_high_and_pregnancy() -> None:
    assert "ambulance_108_102" in run(U.EMERGENCY, **ADULT)
    assert "ambulance_108_102" in run(U.HIGH, **ADULT)
    assert "ambulance_108_102" not in run(U.MEDIUM, **ADULT)
    assert "ambulance_108_102" in run(U.MEDIUM, pregnant="yes", **WOMAN)


def test_low_urgency_shows_no_hospital_schemes() -> None:
    assert run(U.LOW, **ADULT) == {}


def test_order_free_services_first_cash_last_not_applicable_at_end() -> None:
    ids = list(run(U.HIGH, pregnant="yes", tags={"tb_related"}, **WOMAN))
    pri = {s.id: s.priority for s in SCHEMES}
    ranks = ["free_service", "transport", "hospital_cover", "cash_benefit"]
    applicable = [
        i
        for i in ids
        if run(U.HIGH, pregnant="yes", tags={"tb_related"}, **WOMAN)[i].status
        is not Status.not_applicable
    ]
    assert [ranks.index(pri[i]) for i in applicable] == sorted(
        ranks.index(pri[i]) for i in applicable
    )
