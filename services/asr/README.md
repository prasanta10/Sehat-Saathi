# ASR service (GPU host)

HTTP wrapper around AI4Bharat's `indic-conformer-600m-multilingual`, loaded from a **local
snapshot** — no Hugging Face token or network access at run time.

- `POST /transcribe` — multipart `audio` (16 kHz mono 16-bit WAV, as sent by the app server) and
  `language` (default `hi`) → `{"text", "model_rev", "duration_s", "segments"}`
- `GET /healthz`, `GET /readyz` (ready once the model has loaded on first request)

## Model

- Snapshot: `/home3/prasanta_chettri/models/indic-conformer-600m-multilingual`, commit
  `2a77d305038dfc502fd9464e7d028b90381976cb` (404/404 files verified against the hub on 2026-11-12).
  Downloaded once by a team member with a temporary token; the token is not stored on the server.
- The model's own `from_pretrained` always calls Hugging Face, so `asr_service.py` builds the
  classes in the bundled `model_onnx.py` directly (code reviewed: ONNX Runtime sessions and a
  TorchScript preprocessor; no network or shell use).
- Decoding: CTC. Audio is split at pauses into segments of at most ~10 s (`ASR_MAX_SEGMENT_S`):
  decoding a 20 s clip whole dropped its first ~5 s; 10 s segments did not.

## Run

```
cd services/asr
# one-time: see requirements-gpu.txt for the venv + install commands
./run.sh                      # GPU 0 only, ≤ half its memory, port 9000, HF offline
```

`run.sh` puts the pip-installed cuDNN/cuBLAS libraries on `LD_LIBRARY_PATH` (ONNX Runtime's CUDA
provider needs them) and sets `CUDA_VISIBLE_DEVICES=0`, `ASR_GPU_MEM_FRACTION=0.5`,
`ASR_MODEL_DIR`, `HF_HUB_OFFLINE=1`. Override any of them in the environment.

Then point the app at it: `ASR_PROVIDER=indic_conformer_http ASR_BASE_URL=http://127.0.0.1:9000`.

## Measured (2026-11-12, synthetic espeak Hindi — not real speech)

| | |
| --- | --- |
| GPU memory | ~3.3 GB on GPU 0 (cap 12 GB); GPU 1 unused |
| Model load (first request) | ~8 s |
| 4 s clip / 20 s clip, warm | ~0.2 s / ~0.3 s |
| Through the app (WebM upload → ffmpeg → ASR → stored transcript) | works; 8.8 s on the first request including model load |

Accuracy is **not** measured: the only test audio is a robotic espeak voice, which the model
transcribes poorly (and once turned "बुखार नहीं है" into "वो खान ही है"). Word error rate and
key-fact survival need consented human recordings (`evals/audio/`, open question O5).
