import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import API, answer_all, confirm_and_triage, encounter


def medium(client: TestClient) -> str:
    eid: str = encounter(client)["id"]
    client.post(
        f"{API}/encounters/{eid}/capture/text",
        json={"text": "khansi teen hafte se, bus ka kiraya nahi hai"},
    )
    client.post(f"{API}/encounters/{eid}/extract")
    answer_all(client, eid, {"cough_present": "yes", "cough_duration_days": 21})
    confirm_and_triage(client, eid)
    return eid


def test_schemes_after_triage(client: TestClient) -> None:
    eid = medium(client)
    body = client.get(f"{API}/encounters/{eid}/schemes").json()
    cards = {c["id"]: c for c in body["cards"]}
    assert cards["ntep_free_tb_care"]["status"] == "possibly_relevant"
    assert cards["pmjay"]["status"] == "not_applicable"
    assert cards["nikshay_poshan_yojana"]["amounts"][0]["as_of"] == "2024-11-01"
    for c in body["cards"]:
        assert c["sources"] and all(
            s["retrieved_on"] and s["url"].startswith("https://") for s in c["sources"]
        )
    assert body["unparsed_concerns"] == ["bus ka kiraya nahi hai"]


def test_schemes_wait_for_the_urgency_result(client: TestClient) -> None:
    eid = encounter(client)["id"]
    assert client.get(f"{API}/encounters/{eid}/schemes").status_code == 409


def test_scheme_failure_cannot_delay_or_change_triage(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.api.schemes as schemes_api

    def boom(*a, **k):  # type: ignore[no-untyped-def]
        raise RuntimeError("scheme store unavailable")

    monkeypatch.setattr(schemes_api, "load_schemes", boom)
    eid = encounter(client)["id"]
    answer_all(client, eid, {"cough_present": "yes", "rf_breathless": "yes"})
    assert confirm_and_triage(client, eid)["triage"]["result"]["urgency"] == "HIGH"
    e2 = encounter(client)["id"]
    r = client.post(
        f"{API}/encounters/{e2}/emergency", json={"danger_sign_ids": ["general.unconscious"]}
    )
    assert r.json()["triage"]["result"]["urgency"] == "EMERGENCY"


def test_household_attribute_refines_without_touching_the_visit(client: TestClient) -> None:
    eid = encounter(client)["id"]
    answer_all(client, eid, {"cough_present": "yes", "rf_confined_to_bed": "yes"})
    confirm_and_triage(client, eid)
    pid = client.get(f"{API}/encounters/{eid}").json()["person"]["id"]
    before = {c["id"]: c for c in client.get(f"{API}/encounters/{eid}/schemes").json()["cards"]}
    assert "ayushman_card_held" in before["pmjay"]["unknown_facts"]
    client.patch(f"{API}/persons/{pid}", json={"ayushman_card_held": "yes"})
    after = {c["id"]: c for c in client.get(f"{API}/encounters/{eid}/schemes").json()["cards"]}
    assert after["pmjay"]["unknown_facts"] == []
    assert client.get(f"{API}/encounters/{eid}").json()["status"] == "triaged"  # visit not reopened


def test_tell_me_more_returns_only_verbatim_excerpts(client: TestClient) -> None:
    hits = client.get(f"{API}/schemes/search", params={"q": "outpatient OPD"}).json()
    assert hits and all(h["source"]["excerpt"] and h["source"]["url"] for h in hits)
    assert client.get(f"{API}/schemes/search", params={"q": "zzqqnothing"}).json() == []
