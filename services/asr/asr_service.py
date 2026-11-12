"""ASR HTTP service for the GPU host. See README.md."""

from __future__ import annotations

import array
import importlib.util
import io
import os
import types
import wave
from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI, Form, HTTPException, UploadFile

SAMPLE_RATE = 16_000
# Whole-clip decoding drops the start of 20 s clips (measured 2026-11-12); ~10 s segments do not.
MAX_SEGMENT_S = float(os.environ.get("ASR_MAX_SEGMENT_S", "10"))
MODEL_ID = os.environ.get("ASR_MODEL_ID", "ai4bharat/indic-conformer-600m-multilingual")
MODEL_REVISION = os.environ.get("ASR_MODEL_REVISION", "2a77d305038dfc502fd9464e7d028b90381976cb")
MODEL_DIR = os.environ.get("ASR_MODEL_DIR", "")  # local snapshot; no network or token at run time
GPU_MEM_FRACTION = float(os.environ.get("ASR_GPU_MEM_FRACTION", "0.5"))
DECODING = os.environ.get("ASR_DECODING", "ctc")
# The 22 language codes on the model card. English is not among them.
LANGUAGES = {
    "as", "bn", "brx", "doi", "gu", "hi", "kn", "kok", "ks", "mai", "ml",
    "mni", "mr", "ne", "or", "pa", "sa", "sat", "sd", "ta", "te", "ur",
}  # fmt: skip


class SpeechModel(Protocol):
    revision: str

    def transcribe(self, samples: list[float], language: str) -> str: ...


class IndicConformer:
    """Loads the model from a local snapshot (ASR_MODEL_DIR). The model's own ``from_pretrained``
    always calls Hugging Face, so the classes in its bundled ``model_onnx.py`` (reviewed: ONNX
    Runtime sessions and a TorchScript preprocessor, no network or shell use) are built directly.
    GPU memory is capped at ASR_GPU_MEM_FRACTION of the (single visible) GPU."""

    def __init__(self) -> None:
        import onnxruntime as ort
        import torch

        if not MODEL_DIR or not (Path(MODEL_DIR) / "model_onnx.py").exists():
            raise RuntimeError("set ASR_MODEL_DIR to the downloaded model folder")
        self._torch = torch
        providers: list[object] = ["CPUExecutionProvider"]
        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(GPU_MEM_FRACTION, 0)
            limit = int(torch.cuda.get_device_properties(0).total_memory * GPU_MEM_FRACTION)
            providers = [
                (
                    "CUDAExecutionProvider",
                    {
                        "device_id": 0,
                        "gpu_mem_limit": limit,
                        "arena_extend_strategy": "kSameAsRequested",
                    },
                ),
                "CPUExecutionProvider",
            ]
        spec = importlib.util.spec_from_file_location(
            "indic_asr_model_onnx", Path(MODEL_DIR) / "model_onnx.py"
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        def session(path: str, providers_: object = None, **kw: object) -> object:
            return ort.InferenceSession(path, providers=providers, **kw)

        mod.ort = types.SimpleNamespace(
            InferenceSession=lambda path, providers=None, **kw: session(path, **kw)
        )
        self.model = mod.IndicASRModel(
            mod.IndicASRConfig(ts_folder=MODEL_DIR, FRAME_DURATION_MS=0.08)
        )
        self.revision = f"{MODEL_ID}@{MODEL_REVISION}"

    def transcribe(self, samples: list[float], language: str) -> str:
        wav = self._torch.tensor(samples, dtype=self._torch.float32).unsqueeze(
            0
        )  # [1, N] at 16 kHz
        with self._torch.inference_mode():
            return str(self.model(wav, language, DECODING))


def read_wav(data: bytes) -> list[float]:
    try:
        with wave.open(io.BytesIO(data)) as w:
            if w.getframerate() != SAMPLE_RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
                raise HTTPException(400, "expected 16 kHz mono 16-bit WAV")
            pcm = array.array("h", w.readframes(w.getnframes()))
    except (wave.Error, EOFError) as e:
        raise HTTPException(400, "unreadable WAV") from e
    return [s / 32768.0 for s in pcm]


def segment(
    samples: list[float], max_s: float | None = None, frame_s: float = 0.03
) -> list[tuple[int, int]]:
    """Split at the quietest frame before each max_s boundary (energy-based VAD, no model)."""
    frame = int(SAMPLE_RATE * frame_s)
    limit = int(SAMPLE_RATE * (max_s or MAX_SEGMENT_S))
    out: list[tuple[int, int]] = []
    start = 0
    while len(samples) - start > limit:
        window_start = start + limit // 2
        best, best_energy = start + limit, float("inf")
        for f in range(window_start, start + limit - frame, frame):
            e = sum(x * x for x in samples[f : f + frame])
            if e < best_energy:
                best, best_energy = f + frame // 2, e
        out.append((start, best))
        start = best
    if len(samples) > start:
        out.append((start, len(samples)))
    return out


def create_app(model: SpeechModel | None = None) -> FastAPI:
    app = FastAPI(title="Sehat Saathi ASR")
    state: dict[str, Any] = {"model": model}

    def get_model() -> SpeechModel:
        if state["model"] is None:
            state["model"] = IndicConformer()
        m: SpeechModel = state["model"]
        return m

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, Any]:
        return {"ready": state["model"] is not None}

    @app.post("/transcribe")
    async def transcribe(audio: UploadFile, language: str = Form("hi")) -> dict[str, Any]:
        if language not in LANGUAGES:
            raise HTTPException(400, "unsupported language")
        samples = read_wav(await audio.read())
        m = get_model()
        segments = segment(samples)
        texts = [m.transcribe(samples[a:b], language).strip() for a, b in segments]
        return {
            "text": " ".join(t for t in texts if t),
            "model_rev": m.revision,
            "duration_s": len(samples) / SAMPLE_RATE,
            "segments": [
                {"start_s": a / SAMPLE_RATE, "end_s": b / SAMPLE_RATE, "text": t}
                for (a, b), t in zip(segments, texts, strict=True)
            ],
        }

    return app


# The model loads on the first request, so importing this module needs no GPU.
app = create_app()
