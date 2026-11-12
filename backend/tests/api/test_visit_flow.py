from fastapi.testclient import TestClient

from tests.api.helpers import API, answer_all, confirm_and_triage, encounter


def test_typed_visit_reaches_medium(client: TestClient) -> None:
    enc = encounter(client)
    eid = enc["id"]
    assert enc["status"] == "draft"
    # person facts are carried over as suggestions
    assert {f["key"]: f["value"] for f in enc["facts"]}["age_years"] == 40
    r = client.post(
        f"{API}/encounters/{eid}/capture/text", json={"text": "Synthetic: khansi teen hafte se"}
    )
    assert r.json()["status"] == "captured"
    asked = answer_all(
        client, eid, {"cough_present": "yes", "cough_duration_days": 21, "fever_present": "no"}
    )
    assert asked[0] == "cough_present" or asked[0].startswith("rf_")
    out = confirm_and_triage(client, eid)
    assert out["status"] == "triaged"
    res = out["triage"]["result"]
    assert res["urgency"] == "MEDIUM"
    assert [f["id"] for f in res["fired"]] == ["cough.two_weeks_or_more"]
    assert res["review_status"] == "draft"
    assert all(f["status"] in ("confirmed", "unknown") for f in out["facts"])


def test_red_flags_are_asked_before_other_questions(client: TestClient) -> None:
    eid = encounter(client)["id"]
    client.post(
        f"{API}/encounters/{eid}/answers", json={"fact_key": "cough_present", "value": "yes"}
    )
    q = client.get(f"{API}/encounters/{eid}/next-question").json()
    assert q["fact_key"] == "rf_breathless"
    assert q["options"] == ["yes", "no", "unknown"]
    assert q["ask"]["hi"] and q["ask"]["en"]
    assert "urgency" not in q  # interim results are never exposed


def test_triage_requires_confirmation(client: TestClient) -> None:
    eid = encounter(client)["id"]
    answer_all(client, eid, {"cough_present": "yes", "cough_duration_days": 21})
    r = client.post(f"{API}/encounters/{eid}/triage")
    assert r.status_code == 409
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "not_confirmed"
    r = client.post(f"{API}/encounters/{eid}/confirm", json={"checked_with_family": False})
    assert r.status_code == 400
    assert r.json()["code"] == "not_checked_with_family"


def test_dont_know_is_not_asked_again_and_gives_incomplete(client: TestClient) -> None:
    eid = encounter(client)["id"]
    asked = answer_all(
        client, eid, {"cough_present": "yes", "cough_duration_days": 5, "night_sweats": "unknown"}
    )
    assert asked.count("night_sweats") == 1
    res = confirm_and_triage(client, eid)["triage"]["result"]
    assert res["urgency"] == "INCOMPLETE"
    assert "night_sweats" in res["missing_fact_keys"]


def test_editing_after_triage_reopens_and_supersedes(client: TestClient) -> None:
    eid = encounter(client)["id"]
    answer_all(client, eid, {"cough_present": "yes", "cough_duration_days": 21})
    confirm_and_triage(client, eid)
    r = client.patch(
        f"{API}/encounters/{eid}/facts",
        json={"facts": [{"key": "rf_confined_to_bed", "value": "yes"}]},
    )
    body = r.json()
    assert body["status"] == "clarifying"
    assert body["triage"] is None
    assert confirm_and_triage(client, eid)["triage"]["result"]["urgency"] == "HIGH"


def test_pathway_change_reopens(client: TestClient) -> None:
    enc = encounter(client, pathway=None)
    q = client.get(f"{API}/encounters/{enc['id']}/next-question").json()
    assert q["needs_pathway"] is True
    r = client.patch(f"{API}/encounters/{enc['id']}", json={"pathway_id": "adult_cough"})
    assert r.json()["pathway_id"] == "adult_cough"


def test_invalid_values_are_rejected_without_echo(client: TestClient) -> None:
    eid = encounter(client)["id"]
    r = client.post(
        f"{API}/encounters/{eid}/answers",
        json={"fact_key": "cough_duration_days", "value": "teen hafte"},
    )
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_fact_value"
    r = client.post(f"{API}/encounters/{eid}/answers", json={"fact_key": "made_up", "value": "yes"})
    assert r.json()["code"] == "unknown_fact"
    r = client.post(f"{API}/persons", json={"name": "", "age_years": "SENTINEL-AGE"})
    assert r.status_code == 422
    assert "SENTINEL" not in r.text


def test_unknown_encounter_is_404(client: TestClient) -> None:
    assert client.get(f"{API}/encounters/nope").status_code == 404


def test_bundle_and_reference(client: TestClient) -> None:
    b = client.get(f"{API}/content/bundle").json()
    assert "adult_cough" in b["pathways"]
    assert len(b["danger_signs"]["signs"]) >= 30
    ref = client.get(f"{API}/references/ntep_training_modules_1to4").json()
    assert ref["url"].startswith("https://tbcindia.mohfw.gov.in/")
