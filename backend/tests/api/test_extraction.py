from fastapi.testclient import TestClient

from app.ai.interfaces import ProviderError
from app.api.deps import extractor_dep
from tests.api.helpers import API, answer_all, confirm_and_triage, encounter

TEXT = "Synthetic: teen hafte se khansi hai, bukhar nahi hai. Raat ko pasina aata hai. Bus ka kiraya nahi hai."


def test_extract_suggests_facts_with_evidence(client: TestClient) -> None:
    eid = encounter(client)["id"]
    client.post(f"{API}/encounters/{eid}/capture/text", json={"text": TEXT})
    r = client.post(f"{API}/encounters/{eid}/extract")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["degraded"] is False
    assert body["encounter"]["status"] == "extracted"
    facts = {f["key"]: f for f in body["encounter"]["facts"]}
    assert facts["cough_duration_days"]["value"] == 21
    assert facts["cough_duration_days"]["status"] == "suggested"
    assert facts["cough_duration_days"]["origin"] == "extracted"
    assert "teen hafte" in facts["cough_duration_days"]["evidence"]
    assert "blood_in_sputum" not in facts
    assert body["unparsed_concerns"] == ["Bus ka kiraya nahi hai"]
    assert body["encounter"]["unparsed_concerns"] == ["Bus ka kiraya nahi hai"]
    # suggested facts are not asked again, but are not used for urgency until confirmed
    asked = answer_all(client, eid, {})
    assert "cough_duration_days" not in asked and "fever_present" not in asked
    assert client.get(f"{API}/encounters/{eid}").json()["triage"] is None
    res = confirm_and_triage(client, eid)["triage"]["result"]
    assert res["urgency"] == "MEDIUM"


def test_worker_can_reject_a_suggestion(client: TestClient) -> None:
    eid = encounter(client)["id"]
    client.post(f"{API}/encounters/{eid}/capture/text", json={"text": TEXT})
    client.post(f"{API}/encounters/{eid}/extract")
    body = client.post(f"{API}/encounters/{eid}/facts/night_sweats/reject").json()
    assert {f["key"]: f["status"] for f in body["facts"]}["night_sweats"] == "rejected"
    q = client.get(f"{API}/encounters/{eid}/next-question").json()
    assert "night_sweats" in q["remaining"]  # a rejected suggestion is asked again


def test_extraction_after_worker_answers_is_refused(client: TestClient) -> None:
    eid = encounter(client)["id"]
    client.post(f"{API}/encounters/{eid}/capture/text", json={"text": TEXT})
    client.post(f"{API}/encounters/{eid}/answers", json={"fact_key": "night_sweats", "value": "no"})
    r = client.post(f"{API}/encounters/{eid}/extract")
    assert r.status_code == 409  # already clarifying: the worker's answers stand
    facts = {f["key"]: f for f in client.get(f"{API}/encounters/{eid}").json()["facts"]}
    assert (
        facts["night_sweats"]["value"] == "no"
        and facts["night_sweats"]["origin"] == "clarification"
    )


class Failing:
    name = "failing"
    model_rev = "x"

    async def extract(self, *a, **k):  # type: ignore[no-untyped-def]
        raise ProviderError("down")


def test_llm_down_mid_visit_degrades_to_manual_path(client: TestClient) -> None:
    client.app.dependency_overrides[extractor_dep] = lambda: Failing()  # type: ignore[attr-defined]
    eid = encounter(client)["id"]
    client.post(f"{API}/encounters/{eid}/capture/text", json={"text": TEXT})
    r = client.post(f"{API}/encounters/{eid}/extract")
    assert r.status_code == 200
    assert r.json()["degraded"] is True and r.json()["reason"] == "provider_unavailable"
    assert r.json()["encounter"]["status"] == "captured"
    answer_all(client, eid, {"cough_present": "yes", "cough_duration_days": 21})
    assert confirm_and_triage(client, eid)["triage"]["result"]["urgency"] == "MEDIUM"


def test_parse_answer(client: TestClient) -> None:
    eid = encounter(client)["id"]
    r = client.post(
        f"{API}/encounters/{eid}/parse-answer",
        json={"fact_key": "cough_duration_days", "text": "teen hafte"},
    ).json()
    assert r == {"understood": True, "value": 21, "approximate": False}
    r = client.post(
        f"{API}/encounters/{eid}/parse-answer",
        json={"fact_key": "cough_duration_days", "text": "kuch din"},
    ).json()
    assert r["understood"] is False
    r = client.post(
        f"{API}/encounters/{eid}/parse-answer", json={"fact_key": "night_sweats", "text": "nahi"}
    ).json()
    assert r["value"] == "no"
    # nothing was stored
    assert all(
        f["key"] != "night_sweats" for f in client.get(f"{API}/encounters/{eid}").json()["facts"]
    )
