#!/usr/bin/env bash
# Start the language model (vLLM, OpenAI-compatible API) on the GPU host.
# Defaults: GPU 1 only, at most half its memory, local model folder, Hugging Face offline.
set -euo pipefail
cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"
export HF_HUB_OFFLINE=1
export PATH="$PWD/.venv/bin:$PATH"   # vLLM JIT-compiles some kernels with ninja
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
MODEL_DIR="${LLM_MODEL_DIR:-/home3/prasanta_chettri/models/Qwen2.5-7B-Instruct-AWQ}"
exec .venv/bin/vllm serve "$MODEL_DIR" \
  --served-model-name "${LLM_MODEL_NAME:-qwen2.5-7b-instruct-awq}" \
  --host "${LLM_HOST:-127.0.0.1}" --port "${LLM_PORT:-8001}" \
  --gpu-memory-utilization "${LLM_GPU_MEM_FRACTION:-0.5}" \
  --max-model-len "${LLM_MAX_MODEL_LEN:-8192}" \
  --max-num-seqs "${LLM_MAX_NUM_SEQS:-8}" \
  --seed 0 \
  --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}' \
  --generation-config vllm
