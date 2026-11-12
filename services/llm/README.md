# Language model service (GPU host)

vLLM's OpenAI-compatible server running **Qwen/Qwen2.5-7B-Instruct-AWQ** (Apache-2.0, not gated),
downloaded once to `/home3/prasanta_chettri/models/Qwen2.5-7B-Instruct-AWQ` at commit
`b25037543e9394b818fdfca67ab2a00ecc7dd641`.

```
cd services/llm
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements-gpu.txt
./run.sh        # GPU 1 only, ≤ half its memory, port 8001, HF offline
```

App settings: `LLM_PROVIDER=openai_compatible LLM_BASE_URL=http://127.0.0.1:8001/v1 LLM_MODEL=qwen2.5-7b-instruct-awq`
(or just `make demo`, which starts both model servers and the app).

## Settings that matter (each found by evaluation, 2026-11-12)

- `--gpu-memory-utilization 0.5` → ~12.1 GB on GPU 1 (team limit: half of each GPU).
- `--structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}'` — with free
  whitespace allowed, the model sometimes emitted tabs until the token limit (11% of cases).
- The app asks for a **fixed slot per fact** (an object keyed by fact, all required), not a list:
  the list shape let the model loop, repeat or skip keys. Length-bounded strings; `max_tokens` 1500.

## Evaluation (synthetic text cases, `make eval`)

| Configuration | Precision | Recall | Made-up facts | Negation flips | Malformed | Under-triage |
| --- | --- | --- | --- | --- | --- | --- |
| prompt v1, list schema | 78.3% | 56.4% | 31 | 2 | 2.9% | 0 |
| prompt v2, list schema, AI may not deny red flags | 93.4% | 60.3% | 5 | 2 | 11.4% | 0 |
| + fixed slots, no free whitespace | 92.6% | 79.6% | 9 | 5 | 0% | 0 |
| + evidence must agree with yes/no; duration ⇒ present; required evidence words | 99.4% | 75.6% | 1 | 0 | 0% | 0 |
| + prompt v3 (copy exactly, same script); spelling-tolerant, near-exact evidence; numbers parsed from transcript words | **100%** | **76.5%** | **0** | **0** | **0%** | **0** |

All safety gates pass with the last configuration (first time). Found from the team's own recordings:
the model rewrote "तीन दिन" (3 days) as "teen hafte" (3 weeks) and miscopied "हफ्ते" as "हफ्टे";
numbers are now always parsed by code from the transcript's own words.

In earlier rounds the prompt-injection case (adv01) produced a made-up fact; with prompt v3 it no
longer does, but evidence checks cannot rule this out in general — the worker's confirmation does.
Reports: `evals/report/2026-11-12-openai_compatible*.md`. Synthetic, mostly template-generated cases;
not reviewed by a Hindi speaker; not clinical validation.

Speed: ~2–4 s per extraction on an RTX 3090.
