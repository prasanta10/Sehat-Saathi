import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import session_dep
from tests.api.conftest import login
from tests.api.helpers import API, answer_all, confirm_and_triage, encounter


def anon(client: TestClient) -> TestClient:
    c = TestClient(client.app)
    return c


def test_unauthenticated_requests_are_refused_but_health_and_content_are_open(
    client: TestClient,
) -> None:
    c = anon(client)
    assert c.get(f"{API}/encounters").status_code == 401
    assert c.get(f"{API}/persons").status_code == 401
    assert c.get("/healthz").status_code == 200
    assert c.get(f"{API}/content/bundle").status_code == 200  # danger signs must load without login


def test_login_failures_lock_the_account(client: TestClient) -> None:
    c = anon(client)
    for _ in range(5):
        assert (
            c.post(f"{API}/auth/login", json={"phone": "9000000002", "pin": "9999"}).status_code
            == 401
        )
    r = c.post(f"{API}/auth/login", json={"phone": "9000000002", "pin": "1234"})
    assert r.status_code == 429 and r.json()["code"] == "locked"


def test_unknown_phone_and_wrong_pin_look_the_same(client: TestClient) -> None:
    c = anon(client)
    a = c.post(f"{API}/auth/login", json={"phone": "9111111111", "pin": "1234"})
    b = c.post(f"{API}/auth/login", json={"phone": "9000000001", "pin": "0000"})
    assert a.status_code == b.status_code == 401 and a.json()["code"] == b.json()["code"]


def test_refresh_rotates_and_logout_revokes(client: TestClient) -> None:
    c = anon(client)
    t = c.post(f"{API}/auth/login", json={"phone": "9000000001", "pin": "1234"}).json()
    t2 = c.post(f"{API}/auth/refresh", json={"refresh_token": t["refresh_token"]}).json()
    assert (
        c.post(f"{API}/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401
    )  # single use
    h = {"Authorization": f"Bearer {t2['access_token']}"}
    assert c.get(f"{API}/me", headers=h).json()["role"] == "worker"
    assert c.post(f"{API}/auth/logout", headers=h).status_code == 204
    assert c.get(f"{API}/me", headers=h).status_code == 401


def test_pins_are_argon2_hashed(client: TestClient) -> None:
    session = next(client.app.dependency_overrides[session_dep]())  # type: ignore[attr-defined]
    hashes = [r[0] for r in session.execute(text("select pin_hash from workers"))]
    assert hashes and all(h.startswith("$argon2id$") for h in hashes)


def test_a_worker_cannot_read_another_workers_data(client: TestClient) -> None:
    eid = encounter(client)["id"]
    pid = client.get(f"{API}/encounters/{eid}").json()["person"]["id"]
    other = anon(client)
    login(other, "9000000002", "1234")
    assert other.get(f"{API}/encounters/{eid}").status_code == 404
    assert other.get(f"{API}/persons/{pid}").status_code == 404
    assert eid not in [e["id"] for e in other.get(f"{API}/encounters").json()]
    assert pid not in [p["id"] for p in other.get(f"{API}/persons").json()]
    assert other.post(f"{API}/encounters", json={"person_id": pid}).status_code == 404
    for path in ("next-question", "outputs"):
        assert other.get(f"{API}/encounters/{eid}/{path}").status_code == 404
    assert (
        other.post(
            f"{API}/encounters/{eid}/emergency", json={"danger_sign_ids": ["general.unconscious"]}
        ).status_code
        == 404
    )


def test_admin_endpoints_need_admin_role(client: TestClient) -> None:
    assert client.get(f"{API}/admin/audit").status_code == 403
    assert client.get(f"{API}/admin/replay").status_code == 403


SENTINEL = "ZZSENTINEL"


@pytest.fixture
def admin(client: TestClient) -> TestClient:
    a = anon(client)
    login(a, "9000000009", "4321")
    return a


def test_audit_trail_records_the_visit_without_patient_text(
    client: TestClient, admin: TestClient
) -> None:
    eid = encounter(client, name=f"{SENTINEL} Name", village=f"{SENTINEL} Village")["id"]
    client.post(
        f"{API}/encounters/{eid}/capture/text",
        json={"text": f"{SENTINEL} teen hafte se khansi hai"},
    )
    client.post(f"{API}/encounters/{eid}/extract")
    answer_all(client, eid, {"cough_present": "yes"})
    confirm_and_triage(client, eid)
    events = admin.get(f"{API}/admin/audit", params={"encounter_id": eid}).json()
    actions = [e["action"] for e in events]
    for a in (
        "encounter_created",
        "capture_text",
        "extraction",
        "fact_set",
        "facts_confirmed",
        "triage",
    ):
        assert a in actions, a
    triage = next(e for e in events if e["action"] == "triage")
    assert triage["versions"]["ruleset_version"].startswith("sha256:")
    assert (
        next(e for e in events if e["action"] == "extraction")["versions"]["prompt_version"]
        == "extract_v3"
    )
    assert SENTINEL not in str(events)
    assert "khansi" not in str(events)


def test_audit_log_is_append_only(client: TestClient) -> None:
    encounter(client)
    session = next(client.app.dependency_overrides[session_dep]())  # type: ignore[attr-defined]
    with pytest.raises(Exception, match="append-only"):
        session.execute(text("update audit_events set action='x'"))
    session.rollback()
    with pytest.raises(Exception, match="append-only"):
        session.execute(text("delete from audit_events"))


def test_replay_reproduces_every_stored_triage(client: TestClient, admin: TestClient) -> None:
    for answers in (
        {"cough_duration_days": 21},
        {"rf_breathless": "yes"},
        {"night_sweats": "unknown"},
        {},
    ):
        eid = encounter(client)["id"]
        answer_all(client, eid, {"cough_present": "yes", **answers})
        confirm_and_triage(client, eid)
    e2 = encounter(client)["id"]
    client.post(
        f"{API}/encounters/{e2}/emergency", json={"danger_sign_ids": ["pregnancy.bleeding"]}
    )
    r = admin.get(f"{API}/admin/replay").json()
    assert r["checked"] >= 5 and r["mismatched"] == 0


def test_export_then_delete_a_person(client: TestClient, admin: TestClient) -> None:
    eid = encounter(client, name="Synthetic Delete Me")["id"]
    client.post(f"{API}/encounters/{eid}/capture/text", json={"text": "khansi"})
    pid = client.get(f"{API}/encounters/{eid}").json()["person"]["id"]
    client.post(f"{API}/encounters/{eid}/consents", json={"kind": "store_record", "granted": True})
    exported = admin.get(f"{API}/admin/persons/{pid}/export").json()
    assert exported["person"]["name"] == "Synthetic Delete Me"
    assert exported["encounters"][0]["captures"][0]["transcript"] == "khansi"
    assert admin.delete(f"{API}/admin/persons/{pid}").status_code == 204
    assert client.get(f"{API}/encounters/{eid}").status_code == 404
    events = admin.get(f"{API}/admin/audit", params={"action": "person_deleted"}).json()
    assert events[0]["person_id"] == pid and "Synthetic Delete Me" not in str(events)


def test_retention_purge(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import timedelta

    from app.config import get_settings
    from app.jobs.purge_records import purge_old_encounters
    from app.store.models import Encounter

    old = encounter(client)["id"]
    new = encounter(client)["id"]
    client.post(f"{API}/encounters/{old}/consents", json={"kind": "record_audio", "granted": True})
    session = next(client.app.dependency_overrides[session_dep]())  # type: ignore[attr-defined]
    e = session.get(Encounter, old)
    e.created_at = e.created_at - timedelta(days=400)
    session.commit()
    monkeypatch.setattr(get_settings(), "encounter_retention_days", 365)
    assert purge_old_encounters(session, get_settings()) == 1
    assert client.get(f"{API}/encounters/{old}").status_code == 404
    assert client.get(f"{API}/encounters/{new}").status_code == 200
