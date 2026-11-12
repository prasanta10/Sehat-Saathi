"""All five urgency results through the API. LOW needs a pathway with an explicit low-care rule;
real content has none (no official source), so this uses the synthetic fixture content."""

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import API, confirm_and_triage, encounter

BASE = {"fx_symptom": "yes", "fx_severe": "no", "fx_marker_high": "no", "fx_optional": "no"}


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        ({**BASE, "fx_duration_days": 12}, "MEDIUM"),
        ({**BASE, "fx_duration_days": 2}, "LOW"),
        ({**BASE, "fx_marker_high": "yes"}, "HIGH"),
        ({**BASE, "fx_severe": "yes"}, "EMERGENCY"),
        ({**BASE, "fx_duration_days": 5}, "INCOMPLETE"),
    ],
)
def test_each_result(fixture_client: TestClient, facts: dict, expected: str) -> None:  # type: ignore[type-arg]
    eid = encounter(fixture_client, pathway="fx_with_low", sex=None)["id"]
    edits = [{"key": k, "value": v} for k, v in facts.items()]
    assert (
        fixture_client.patch(f"{API}/encounters/{eid}/facts", json={"facts": edits}).status_code
        == 200
    )
    assert confirm_and_triage(fixture_client, eid)["triage"]["result"]["urgency"] == expected
