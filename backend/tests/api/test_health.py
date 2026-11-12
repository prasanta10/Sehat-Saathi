from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz() -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_healthz_under_api_prefix() -> None:
    assert client.get("/api/v1/healthz").status_code == 200


def test_readyz_with_mocks_is_ok() -> None:
    body = client.get("/readyz").json()
    assert body["status"] == "ok"
    assert {p["name"] for p in body["providers"]} == {"asr", "llm"}
