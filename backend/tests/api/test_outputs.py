import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai.interfaces import ProviderError
from app.ai.providers.openai_compatible import OpenAICompatibleWriter
from app.api.deps import writer_dep
from tests.api.helpers import API, answer_all, confirm_and_triage, encounter


def medium_visit(client: TestClient) -> str:
    eid: str = encounter(client, name="Synthetic Kamla", village="Rampur")["id"]
    answer_all(
        client, eid, {"cough_present": "yes", "cough_duration_days": 21, "night_sweats": "unknown"}
    )
    confirm_and_triage(client, eid)
    return eid


def test_plan_for_medium(client: TestClient) -> None:
    eid = medium_visit(client)
    p = client.get(f"{API}/encounters/{eid}/plan").json()
    assert p["facility_level"] == "PHC" and p["target_window"] == "within_24_hours"
    assert p["bring_list"] == ["id_document", "previous_reports"]
    assert p["facility_names"] == []  # no official directory loaded: level only
    assert client.get(f"{API}/encounters/{eid}").json()["status"] == "plan_ready"


def test_template_outputs_are_complete_with_no_model(client: TestClient) -> None:
    eid = medium_visit(client)
    outs = {o["kind"]: o for o in client.post(f"{API}/encounters/{eid}/outputs").json()}
    h = outs["clinician_handoff"]["body"]
    assert outs["clinician_handoff"]["generated_by"] == "template"
    for expected in [
        "Synthetic Kamla",
        "age 40",
        "Rampur",
        "Cough in an adult",
        "Days of cough: 21 days",
        "Has fever",
        "Sweating at night",
        "cough.two_weeks_or_more",
        "ntep_training_modules_1to4",
        "Primary Health Centre",
        "within 24 hours",
        "This is not a diagnosis",
        "Demonstration pathway — not clinically validated",
    ]:
        assert expected in h, expected
    f = outs["family_instructions"]
    assert f["language"] == "hi"
    for expected in ["प्राथमिक स्वास्थ्य केंद्र", "24 घंटे के अंदर", "108", "यह निदान नहीं है", "पहचान पत्र"]:
        assert expected in f["body"], expected
    assert 5 <= len(f["body"].splitlines()) <= 9


def test_emergency_outputs(client: TestClient) -> None:
    eid = encounter(client)["id"]
    client.post(
        f"{API}/encounters/{eid}/emergency", json={"danger_sign_ids": ["general.unconscious"]}
    )
    outs = {o["kind"]: o["body"] for o in client.post(f"{API}/encounters/{eid}/outputs").json()}
    assert (
        "108/112" in outs["clinician_handoff"]
        and "general.unconscious" in outs["clinician_handoff"]
    )
    assert "अभी 108 या 112 पर कॉल करें" in outs["family_instructions"]
    assert "called" not in outs["clinician_handoff"].lower().replace(
        "prompted the family to call", ""
    )


class FakeWriter:
    name = "fake"
    model_rev = "1"

    def __init__(self, transform):  # type: ignore[no-untyped-def]
        self.transform = transform

    async def rewrite(self, kind: str, language: str, text: str) -> str:
        return self.transform(text)  # type: ignore[no-any-return]


@pytest.mark.parametrize(
    ("transform", "failure"),
    [
        (lambda t: t + "\nIt is probably tuberculosis.", "disease_terms"),
        (lambda t: t + "\nदिन में दो बार पैरासिटामोल की गोली दें।", "medicine_terms"),
        (lambda t: t + "\nGive paracetamol 500 mg.", "medicine_terms"),
        (lambda t: t + "\nThe scheme will pay ₹5,00,000.", "money_terms"),
        (
            lambda t: t.replace("This is not a diagnosis. A doctor will examine you.", ""),
            "missing_required_line",
        ),
        (lambda t: t.replace("within 24 hours", "whenever convenient"), "missing_required_line"),
    ],
)
def test_bad_rewrites_fall_back_to_template(client: TestClient, transform, failure: str) -> None:  # type: ignore[no-untyped-def]
    client.app.dependency_overrides[writer_dep] = lambda: FakeWriter(transform)  # type: ignore[attr-defined]
    eid = medium_visit(client)
    outs = {o["kind"]: o for o in client.post(f"{API}/encounters/{eid}/outputs").json()}
    h = outs["clinician_handoff"]
    assert h["generated_by"] == "template"
    assert any(f.startswith(failure) for f in h["check_failures"]), h["check_failures"]
    assert (
        "tuberculosis" not in h["body"] and "paracetamol" not in h["body"] and "₹" not in h["body"]
    )


def test_good_rewrite_is_used(client: TestClient) -> None:
    client.app.dependency_overrides[writer_dep] = lambda: FakeWriter(
        lambda t: t.replace("Reported present", "Present")
    )  # type: ignore[attr-defined]
    eid = medium_visit(client)
    outs = {o["kind"]: o for o in client.post(f"{API}/encounters/{eid}/outputs").json()}
    assert outs["clinician_handoff"]["generated_by"] == "llm"
    assert outs["clinician_handoff"]["check_failures"] == []


def test_writer_down_falls_back(client: TestClient) -> None:
    class Down:
        name, model_rev = "down", "1"

        async def rewrite(self, *a):  # type: ignore[no-untyped-def]
            raise ProviderError("x")

    client.app.dependency_overrides[writer_dep] = lambda: Down()  # type: ignore[attr-defined]
    eid = medium_visit(client)
    outs = client.post(f"{API}/encounters/{eid}/outputs").json()
    assert all(
        o["generated_by"] == "template" and o["check_failures"] == ["writer_unavailable"]
        for o in outs
    )


def test_worker_edit_is_recorded(client: TestClient) -> None:
    eid = medium_visit(client)
    o = client.post(f"{API}/encounters/{eid}/outputs").json()[1]
    r = client.patch(
        f"{API}/encounters/{eid}/outputs/{o['id']}", json={"body": "edited text"}
    ).json()
    assert r["edited_by_worker"] is True and r["body"] == "edited text"
    assert client.get(f"{API}/encounters/{eid}/outputs").json()[1]["body"] == "edited text"


def test_low_family_instructions_list_return_precautions(fixture_client: TestClient) -> None:
    eid = encounter(fixture_client, pathway="fx_with_low", sex=None)["id"]
    facts = {
        "fx_symptom": "yes",
        "fx_severe": "no",
        "fx_marker_high": "no",
        "fx_optional": "no",
        "fx_duration_days": 2,
    }
    fixture_client.patch(
        f"{API}/encounters/{eid}/facts",
        json={"facts": [{"key": k, "value": v} for k, v in facts.items()]},
    )
    confirm_and_triage(fixture_client, eid)
    fam = next(
        o
        for o in fixture_client.post(f"{API}/encounters/{eid}/outputs").json()
        if o["kind"] == "family_instructions"
    )
    assert "परीक्षण सावधानी" in fam["body"] and "घर पर देखभाल" in fam["body"]


async def test_openai_compatible_writer() -> None:
    seen = {}

    def handler(r: httpx.Request) -> httpx.Response:
        seen["body"] = r.read()
        return httpx.Response(200, json={"choices": [{"message": {"content": " rewritten "}}]})

    w = OpenAICompatibleWriter("http://h/v1", "m", transport=httpx.MockTransport(handler))
    assert await w.rewrite("family_instructions", "hi", "text") == "rewritten"
    assert b"Do not add any disease name" in seen["body"]
