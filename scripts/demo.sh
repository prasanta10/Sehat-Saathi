#!/usr/bin/env bash
# Run the full demo on the GPU server: IndicConformer ASR (GPU 0) + Qwen2.5-7B-AWQ via vLLM
# (GPU 1), each capped at half its GPU, and the app wired to them with its own demo database.
# Web: http://127.0.0.1:5173  (from a laptop: ssh -L 5173:127.0.0.1:5173 <user>@<server>)
# Reset the demo data first with `make demo-reset`. Ctrl-C stops everything.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/.local/node/bin:$HOME/.local/bin:$PATH"
LOGS="$ROOT/backend/data/demo-logs"; mkdir -p "$LOGS"
trap 'echo "stopping..."; kill 0' EXIT INT TERM

wait_for() {  # url name seconds
  for _ in $(seq 1 "$3"); do curl -sf "$1" >/dev/null && { echo "  $2 ready"; return 0; }; sleep 2; done
  echo "  $2 did not start; see $LOGS"; exit 1
}

echo "starting speech model (GPU 0)..."; "$ROOT/services/asr/run.sh" >"$LOGS/asr.log" 2>&1 &
echo "starting language model (GPU 1)..."; "$ROOT/services/llm/run.sh" >"$LOGS/llm.log" 2>&1 &
wait_for http://127.0.0.1:9000/healthz "speech service" 60
wait_for http://127.0.0.1:8001/v1/models "language model" 240

export DATABASE_URL="sqlite:///$ROOT/backend/demo.db"
export ASR_PROVIDER=indic_conformer_http ASR_BASE_URL=http://127.0.0.1:9000
export LLM_PROVIDER=openai_compatible LLM_BASE_URL=http://127.0.0.1:8001/v1 LLM_MODEL=qwen2.5-7b-instruct-awq
echo "starting app..."
(cd "$ROOT/backend" && uv run uvicorn app.main:app --port 8000 >"$LOGS/api.log" 2>&1) &
wait_for http://127.0.0.1:8000/healthz "API" 60
# Warm the speech model so the first recording on camera is fast.
WARM="$LOGS/warmup.wav"
ffmpeg -loglevel error -y -i "$ROOT/frontend/public/audio/emergency_hi.mp3" -ac 1 -ar 16000 -sample_fmt s16 "$WARM"
curl -s -o /dev/null -X POST http://127.0.0.1:9000/transcribe -F "audio=@$WARM;type=audio/wav" -F language=hi || true
(cd "$ROOT/frontend" && npm run dev -- --host 127.0.0.1 >"$LOGS/web.log" 2>&1) &
wait_for http://127.0.0.1:5173 "web app" 60
echo
echo "Demo running at http://127.0.0.1:5173  —  log in 9000000001 / PIN 1234 (synthetic demo account)"
wait
