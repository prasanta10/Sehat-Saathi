"""Invariant 9: no real patient data in the repository, fixtures, logs, or prompts to hosted APIs.

- Logs from a whole visit contain none of the seeded sentinel strings (names, transcript, values).
- Seed people are flagged synthetic; hosted LLMs are blocked for non-synthetic encounters
  (tests/unit/test_orchestrator.py::test_hosted_provider_blocked_unless_allowed_and_synthetic).
"""

import io
import logging

from fastapi.testclient import TestClient

from app.logging_setup import JsonFormatter
from app.seed import SYNTHETIC_PEOPLE
from tests.api.helpers import API, answer_all, confirm_and_triage, encounter

SENTINELS = ["QQNAMEQQ", "QQVILLAGEQQ", "QQTRANSCRIPTQQ"]


def test_logs_from_a_full_visit_contain_no_patient_text(client: TestClient) -> None:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    loggers = [
        logging.getLogger(n)
        for n in (
            "sehat",
            "sehat.http",
            "sehat.ai",
            "sehat.speech",
            "uvicorn",
            "uvicorn.access",
            "",
        )
    ]
    for lg in loggers:
        lg.addHandler(handler)
    try:
        eid = encounter(client, name=SENTINELS[0], village=SENTINELS[1])["id"]
        client.post(
            f"{API}/encounters/{eid}/capture/text",
            json={"text": f"{SENTINELS[2]} teen hafte se khansi hai"},
        )
        client.post(f"{API}/encounters/{eid}/extract")
        answer_all(client, eid, {"cough_present": "yes"})
        confirm_and_triage(client, eid)
        client.post(f"{API}/encounters/{eid}/outputs")
        client.post(
            f"{API}/persons", json={"name": "", "village": SENTINELS[1]}
        )  # validation error path
    finally:
        for lg in loggers:
            lg.removeHandler(handler)
    out = buf.getvalue()
    assert '"route": "/encounters/{encounter_id}/extract"' in out  # logging really ran
    assert '"request_id": "-"' not in out
    for s in SENTINELS:
        assert s not in out
    assert "khansi" not in out


def test_seed_people_are_synthetic() -> None:
    assert all("(synthetic)" in p["name"] for p in SYNTHETIC_PEOPLE)
