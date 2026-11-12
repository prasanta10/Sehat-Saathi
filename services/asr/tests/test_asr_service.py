"""ASR service contract, with a stand-in model (the real model runs only on the GPU host)."""

import array
import io
import sys
import wave
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asr_service import SAMPLE_RATE, create_app, segment


class FakeModel:
    revision = "fake@0"

    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    def transcribe(self, samples: list[float], language: str) -> str:
        self.calls.append((len(samples), language))
        return f"seg{len(self.calls)}"


def wav(seconds: float, rate: int = SAMPLE_RATE, silence_at: float | None = None) -> bytes:
    n = int(seconds * rate)
    pcm = array.array("h", [(8000 if (i // 40) % 2 else -8000) for i in range(n)])
    if silence_at is not None:
        s = int(silence_at * rate)
        for i in range(s, min(n, s + rate // 2)):
            pcm[i] = 0
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def test_transcribe_short_clip() -> None:
    model = FakeModel()
    c = TestClient(create_app(model))
    r = c.post(
        "/transcribe", files={"audio": ("a.wav", wav(2), "audio/wav")}, data={"language": "hi"}
    )
    assert r.status_code == 200
    assert r.json()["text"] == "seg1" and r.json()["model_rev"] == "fake@0"
    assert model.calls == [(2 * SAMPLE_RATE, "hi")]


def test_long_clip_is_segmented_at_a_pause(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import asr_service

    monkeypatch.setattr(asr_service, "MAX_SEGMENT_S", 25.0)
    model = FakeModel()
    c = TestClient(create_app(model))
    r = c.post(
        "/transcribe",
        files={"audio": ("a.wav", wav(40, silence_at=20), "audio/wav")},
        data={"language": "hi"},
    ).json()
    assert r["text"] == "seg1 seg2"
    first_end = r["segments"][0]["end_s"]
    assert 20 <= first_end <= 20.5  # split inside the silence


def test_rejects_wrong_format_and_language() -> None:
    c = TestClient(create_app(FakeModel()))
    assert (
        c.post(
            "/transcribe", files={"audio": ("a.wav", wav(1, rate=44100), "audio/wav")}
        ).status_code
        == 400
    )
    assert (
        c.post("/transcribe", files={"audio": ("a.wav", b"junk", "audio/wav")}).status_code == 400
    )
    assert (
        c.post(
            "/transcribe", files={"audio": ("a.wav", wav(1), "audio/wav")}, data={"language": "xx"}
        ).status_code
        == 400
    )


def test_segments_cover_everything() -> None:
    samples = [0.1] * (SAMPLE_RATE * 61)
    segs = segment(samples)  # default ~10 s
    assert segs[0][0] == 0 and segs[-1][1] == len(samples)
    assert all(b - a <= SAMPLE_RATE * 10 for a, b in segs) and len(segs) >= 7
    assert all(segs[i][1] == segs[i + 1][0] for i in range(len(segs) - 1))
