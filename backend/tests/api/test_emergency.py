"""Invariant 3 and 4 at the API level: emergency is reachable from every open state, needs one
danger sign only, and does not depend on pathway, confirmation or other facts."""

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import API, answer_all, confirm_and_triage, encounter


def _to_state(client: TestClient, state: str) -> str:
    eid: str = encounter(client)["id"]
    if state == "draft":
        return eid
    if state == "captured":
        client.post(f"{API}/encounters/{eid}/capture/text", json={"text": "synthetic"})
        return eid
    answer_all(client, eid, {"cough_present": "yes", "cough_duration_days": 21})
    if state == "clarifying":
        return eid
    if state == "confirmed":
        client.post(f"{API}/encounters/{eid}/confirm", json={"checked_with_family": True})
        return eid
    confirm_and_triage(client, eid)
    return eid


@pytest.mark.parametrize("state", ["draft", "captured", "clarifying", "confirmed", "triaged"])
def test_emergency_from_every_state(client: TestClient, state: str) -> None:
    eid = _to_state(client, state)
    r = client.post(
        f"{API}/encounters/{eid}/emergency", json={"danger_sign_ids": ["newborn.convulsion"]}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "emergency"
    assert body["triage"]["result"]["urgency"] == "EMERGENCY"
    assert "newborn.convulsion" in [f["id"] for f in body["triage"]["result"]["fired"]]


def test_emergency_without_pathway(client: TestClient) -> None:
    eid = encounter(client, pathway=None)["id"]
    r = client.post(
        f"{API}/encounters/{eid}/emergency", json={"danger_sign_ids": ["general.unconscious"]}
    )
    assert r.json()["triage"]["result"]["urgency"] == "EMERGENCY"


def test_unknown_sign_rejected(client: TestClient) -> None:
    eid = encounter(client)["id"]
    r = client.post(f"{API}/encounters/{eid}/emergency", json={"danger_sign_ids": ["made.up"]})
    assert r.status_code == 400


def test_suggested_danger_sign_answer_is_not_emergency_until_confirmed(client: TestClient) -> None:
    """A danger sign entered as an ordinary answer counts only after the worker confirms."""
    eid = encounter(client)["id"]
    answer_all(
        client, eid, {"cough_present": "yes", "cough_duration_days": 3, "ds_unconscious": "yes"}
    )
    client.post(
        f"{API}/encounters/{eid}/answers", json={"fact_key": "ds_unconscious", "value": "yes"}
    )
    assert client.get(f"{API}/encounters/{eid}").json()["triage"] is None
    res = confirm_and_triage(client, eid)["triage"]["result"]
    assert res["urgency"] == "EMERGENCY"
