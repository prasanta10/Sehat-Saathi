"""Pregnancy check-up and sick child pathways, end to end through the API (mock providers)."""

from fastapi.testclient import TestClient

from tests.api.helpers import API, answer_all, confirm_and_triage, encounter


def _extract(client: TestClient, eid: str, text: str) -> dict:  # type: ignore[type-arg]
    client.post(f"{API}/encounters/{eid}/capture/text", json={"text": text})
    r = client.post(f"{API}/encounters/{eid}/extract")
    assert r.status_code == 200, r.text
    return r.json()["encounter"]  # type: ignore[no-any-return]


def test_extraction_only_assigns_a_pathway_that_fits_the_person(client: TestClient) -> None:
    text = "Synthetic: khansi teen din se"
    adult = encounter(client, None, age_years=45, sex="male")
    assert _extract(client, adult["id"], text)["pathway_id"] == "adult_cough"
    child = encounter(client, None, age_years=2, age_months=26, sex="male")
    assert _extract(client, child["id"], text)["pathway_id"] == "sick_child"
    # A newborn fits neither cough pathway: none is chosen; the worker decides.
    baby = encounter(client, None, age_years=0, age_months=0, sex="female")
    assert _extract(client, baby["id"], text)["pathway_id"] is None


def test_pregnancy_visit_asks_danger_signs_first_and_refers_unregistered(
    client: TestClient,
) -> None:
    eid = encounter(client, "pregnancy_checkup", age_years=24, sex="female", pregnant="yes")["id"]
    asked = answer_all(client, eid, {"anc_registered": "no", "pregnancy_month": 3})
    assert asked[0] == "ds_preg_bleeding"
    assert "anc_checkups_done" not in asked  # only asked once registered
    res = confirm_and_triage(client, eid)["triage"]["result"]
    assert res["urgency"] == "MEDIUM"
    assert [f["id"] for f in res["fired"]] == ["preg.not_registered"]
    assert res["facility_level"] == "SC_HWC"


def test_pregnancy_severe_anaemia_is_an_emergency(client: TestClient) -> None:
    eid = encounter(client, "pregnancy_checkup", age_years=24, sex="female", pregnant="yes")["id"]
    answer_all(client, eid, {"ds_preg_severe_anaemia": "yes"})
    res = confirm_and_triage(client, eid)["triage"]["result"]
    assert res["urgency"] == "EMERGENCY"
    assert [f["id"] for f in res["fired"]] == ["pregnancy.severe_anaemia"]


def test_sick_child_with_diarrhoea_and_sunken_eyes_is_high(client: TestClient) -> None:
    eid = encounter(client, "sick_child", age_years=1, age_months=18, sex="female")["id"]
    asked = answer_all(client, eid, {"diarrhoea_present": "yes", "child_sunken_eyes": "yes"})
    assert asked[0] == "ds_child_not_able_to_drink_or_feed"
    assert "cough_duration_days" not in asked  # cough was "no"
    res = confirm_and_triage(client, eid)["triage"]["result"]
    assert res["urgency"] == "HIGH"
    assert [f["id"] for f in res["fired"]] == ["child.diarrhoea_dehydration"]
    assert (res["facility_level"], res["target_window"]) == ("CHC", "today")
