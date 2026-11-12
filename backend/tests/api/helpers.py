from typing import Any

from fastapi.testclient import TestClient

API = "/api/v1"


def person(client: TestClient, **kw: Any) -> dict[str, Any]:
    body = {
        "name": "Synthetic Person",
        "age_years": 40,
        "sex": "female",
        "village": "Testpur",
        "synthetic": True,
    }
    body.update(kw)
    r = client.post(f"{API}/persons", json=body)
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def encounter(
    client: TestClient, pathway: str | None = "adult_cough", **pkw: Any
) -> dict[str, Any]:
    p = person(client, **pkw)
    r = client.post(
        f"{API}/encounters", json={"person_id": p["id"], "language": "hi", "pathway_id": pathway}
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def answer_all(
    client: TestClient, eid: str, answers: dict[str, Any], default: Any = "no"
) -> list[str]:
    """Walk next-question, answering from ``answers`` or ``default``. Returns keys asked."""
    asked = []
    for _ in range(100):
        q = client.get(f"{API}/encounters/{eid}/next-question").json()
        if q["done"]:
            return asked
        key = q["fact_key"]
        asked.append(key)
        value = answers.get(key, default if q["input"] in ("tristate", None) or q["options"] else 0)
        r = client.post(f"{API}/encounters/{eid}/answers", json={"fact_key": key, "value": value})
        assert r.status_code == 200, r.text
    raise AssertionError("question loop did not finish")


def confirm_and_triage(client: TestClient, eid: str) -> dict[str, Any]:
    assert (
        client.post(
            f"{API}/encounters/{eid}/confirm", json={"checked_with_family": True}
        ).status_code
        == 200
    )
    r = client.post(f"{API}/encounters/{eid}/triage")
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]
