import subprocess
from pathlib import Path

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.ai.interfaces import ProviderError
from app.ai.providers.indic_conformer_http import IndicConformerHTTP
from app.api.deps import asr_dep
from app.config import get_settings
from tests.api.helpers import API, answer_all, confirm_and_triage, encounter


@pytest.fixture(scope="module")
def webm() -> bytes:
    """One second of tone, encoded as WebM/Opus like a browser MediaRecorder upload."""
    out = subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:a",
            "libopus",
            "-f",
            "webm",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    return out.stdout


@pytest.fixture(autouse=True)
def audio_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "audio"
    monkeypatch.setattr(get_settings(), "audio_dir", d)
    monkeypatch.setattr(get_settings(), "audio_retention", "delete_on_confirm")
    monkeypatch.setattr(get_settings(), "audio_encryption_key", Fernet.generate_key().decode())
    return d


def upload(
    client: TestClient, eid: str, data: bytes, path: str = "capture/audio"
) -> httpx.Response:
    return client.post(
        f"{API}/encounters/{eid}/{path}", files={"audio": ("rec.webm", data, "audio/webm")}
    )


def consent(client: TestClient, eid: str, granted: bool = True) -> None:
    r = client.post(
        f"{API}/encounters/{eid}/consents", json={"kind": "record_audio", "granted": granted}
    )
    assert r.status_code == 201


def test_recording_needs_consent(client: TestClient, webm: bytes) -> None:
    eid = encounter(client)["id"]
    r = upload(client, eid, webm)
    assert r.status_code == 403 and r.json()["code"] == "consent_required"
    consent(client, eid, granted=False)
    assert upload(client, eid, webm).status_code == 403
    # declining leads cleanly to typing
    assert (
        client.post(f"{API}/encounters/{eid}/capture/text", json={"text": "khansi hai"}).json()[
            "status"
        ]
        == "captured"
    )


def test_record_transcribe_extract(client: TestClient, webm: bytes, audio_dir: Path) -> None:
    eid = encounter(client)["id"]
    consent(client, eid)
    r = upload(client, eid, webm)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["degraded"] is False
    cap = body["encounter"]["captures"][0]
    assert cap["kind"] == "audio" and cap["has_audio"] is True
    assert cap["transcript"].startswith("[mock ASR]")
    stored = list(audio_dir.rglob("*.wav.enc"))
    assert len(stored) == 1
    assert not stored[0].read_bytes().startswith(b"RIFF")  # encrypted at rest
    plain = Fernet(get_settings().audio_encryption_key.encode()).decrypt(stored[0].read_bytes())
    assert plain.startswith(b"RIFF")
    ex = client.post(f"{API}/encounters/{eid}/extract").json()
    facts = {f["key"]: f["value"] for f in ex["encounter"]["facts"]}
    assert facts["cough_duration_days"] == 21 and facts["fever_present"] == "no"


def test_audio_deleted_on_confirm(client: TestClient, webm: bytes, audio_dir: Path) -> None:
    eid = encounter(client)["id"]
    consent(client, eid)
    upload(client, eid, webm)
    answer_all(client, eid, {"cough_present": "yes", "cough_duration_days": 21})
    out = confirm_and_triage(client, eid)
    assert out["captures"][0]["has_audio"] is False
    assert list(audio_dir.rglob("*.wav.enc")) == []


def test_transcript_edit_keeps_original(client: TestClient, webm: bytes) -> None:
    eid = encounter(client)["id"]
    consent(client, eid)
    cap = upload(client, eid, webm).json()["encounter"]["captures"][0]
    r = client.patch(
        f"{API}/encounters/{eid}/captures/{cap['id']}", json={"transcript": "दो हफ़्ते से खांसी है"}
    )
    c = r.json()["captures"][0]
    assert c["transcript"] == "दो हफ़्ते से खांसी है"
    assert c["transcript_original"].startswith("[mock ASR]")


class DownASR:
    name = "down"

    async def transcribe(self, audio: bytes, language: str):  # type: ignore[no-untyped-def]
        raise ProviderError("down")


def test_asr_down_degrades_and_stores_nothing(
    client: TestClient, webm: bytes, audio_dir: Path
) -> None:
    client.app.dependency_overrides[asr_dep] = lambda: DownASR()  # type: ignore[attr-defined]
    eid = encounter(client)["id"]
    consent(client, eid)
    r = upload(client, eid, webm).json()
    assert r["degraded"] is True and r["reason"] == "asr_unavailable"
    assert r["encounter"]["captures"] == [] and r["encounter"]["status"] == "draft"
    assert list(audio_dir.rglob("*.wav.enc")) == []


def test_unreadable_audio(client: TestClient) -> None:
    eid = encounter(client)["id"]
    consent(client, eid)
    r = upload(client, eid, b"not audio at all")
    assert r.status_code == 400 and r.json()["code"] == "unreadable_audio"


def test_spoken_answer_is_not_stored(client: TestClient, webm: bytes, audio_dir: Path) -> None:
    eid = encounter(client)["id"]
    consent(client, eid)
    r = upload(client, eid, webm, "spoken-answer").json()
    assert r["understood"] is True and r["text"]
    assert list(audio_dir.rglob("*.wav.enc")) == []
    assert client.get(f"{API}/encounters/{eid}").json()["captures"] == []


def test_emergency_needs_no_consent(client: TestClient) -> None:
    """Invariant 4: consent never stands between the worker and the emergency result."""
    eid = encounter(client)["id"]
    consent(client, eid, granted=False)
    r = client.post(
        f"{API}/encounters/{eid}/emergency", json={"danger_sign_ids": ["general.unconscious"]}
    )
    assert r.json()["triage"]["result"]["urgency"] == "EMERGENCY"


def test_purge_keep_days(
    client: TestClient, webm: bytes, audio_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import timedelta

    from app.services.speech import purge_expired_audio
    from app.store.models import Capture

    monkeypatch.setattr(get_settings(), "audio_retention", "keep_days:7")
    eid = encounter(client)["id"]
    consent(client, eid)
    upload(client, eid, webm)
    session_gen = client.app.dependency_overrides  # type: ignore[attr-defined]
    from app.api.deps import session_dep

    session = next(session_gen[session_dep]())
    cap = session.query(Capture).one()
    assert purge_expired_audio(session, get_settings()) == 0
    cap.created_at = cap.created_at - timedelta(days=8)
    session.commit()
    assert purge_expired_audio(session, get_settings()) == 1
    assert list(audio_dir.rglob("*.wav.enc")) == []


async def test_indic_conformer_http_provider() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.content
        return httpx.Response(
            200, json={"text": "तीन हफ़्ते से खांसी", "model_rev": "abc123", "duration_s": 1.0}
        )

    asr = IndicConformerHTTP("http://gpu-host:9000", transport=httpx.MockTransport(handler))
    t = await asr.transcribe(b"RIFF....", "hi")
    assert seen["url"] == "http://gpu-host:9000/transcribe"
    assert b'name="language"' in seen["body"] and b"hi" in seen["body"]
    assert t.text == "तीन हफ़्ते से खांसी" and t.model_rev == "abc123"
    bad = IndicConformerHTTP(
        "http://x", transport=httpx.MockTransport(lambda r: httpx.Response(503))
    )
    with pytest.raises(ProviderError):
        await bad.transcribe(b"x", "hi")


def test_no_key_means_audio_never_written(
    client: TestClient, webm: bytes, audio_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "audio_encryption_key", "")
    eid = encounter(client)["id"]
    consent(client, eid)
    r = upload(client, eid, webm).json()
    assert r["encounter"]["captures"][0]["has_audio"] is False
    assert not audio_dir.exists() or list(audio_dir.rglob("*")) == []


def test_recording_duration_is_real(client: TestClient, webm: bytes) -> None:
    from app.ai.audio import to_wav_16k_mono

    _, duration = to_wav_16k_mono(webm)
    assert 0.9 < duration < 1.2  # the fixture is one second long
