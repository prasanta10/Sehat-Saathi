#!/usr/bin/env bash
# Start the ASR service on the GPU host. Defaults: GPU 0 only, half its memory, local model
# snapshot, Hugging Face offline (no token needed at run time).
set -euo pipefail
cd "$(dirname "$0")"
SITE=".venv/lib/python3.12/site-packages/nvidia"
# ONNX Runtime's CUDA provider needs the cuDNN/cuBLAS libraries that the PyTorch wheels install.
LD_LIBRARY_PATH="$(find "$SITE" -maxdepth 2 -type d -name lib | sed "s#^#$PWD/#" | paste -sd:)${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export ASR_GPU_MEM_FRACTION="${ASR_GPU_MEM_FRACTION:-0.5}"
export ASR_MODEL_DIR="${ASR_MODEL_DIR:-/home3/prasanta_chettri/models/indic-conformer-600m-multilingual}"
export HF_HUB_OFFLINE=1
if [ "$#" -eq 0 ]; then
  set -- .venv/bin/uvicorn asr_service:app --host "${ASR_HOST:-127.0.0.1}" --port "${ASR_PORT:-9000}"
fi
exec "$@"
