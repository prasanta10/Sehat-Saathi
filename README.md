# Sehat Saathi

A voice-first assistant for ASHA and other frontline health workers. The worker records what a family says during a home visit (in Hindi); Sehat Saathi turns it into confirmed facts, an urgency level, a referral plan, and information about government schemes that may help.

## How it works

1. **Speak or type.** Speech is transcribed on our own GPU server by AI4Bharat IndicConformer.
2. **Suggested facts.** A local language model (Qwen2.5-7B-Instruct, AWQ) suggests facts, each tied to the exact words it came from. Anything not said stays unknown.
3. **Questions.** The app asks only what is still missing, starting with danger signs.
4. **Worker confirms.** Nothing is used until the worker has checked it with the family.
5. **Urgency from rules, not AI.** A deterministic rules engine, built from official Government of India guidelines with page references, gives the urgency and the place to go.
6. **Plan and support.** Instructions for the family, a note for the doctor, and scheme cards marked "may help" or "needs checking", never "eligible".

A danger-sign checklist is on every screen and works with no network and no AI.

## Design principles

- AI suggests; the worker confirms; rules decide urgency.
- Unknown stays unknown: missing facts give "more information needed", never "low".
- Any danger sign means emergency, immediately.
- No diagnosis, no medicines, no promised money.
- Every rule and scheme statement cites an official source (`knowledge/references/`).
- Hindi and English throughout.
- Synthetic data only.

The current pathway (adult cough) is a **draft**: it is shown with a "demonstration pathway — not clinically validated" banner until a clinician reviews it.

## Stack

| Part | Technology |
| --- | --- |
| Web app | React 19, TypeScript, Vite, Tailwind, TanStack Query, i18next |
| API | FastAPI, Pydantic v2, SQLAlchemy + Alembic (SQLite) |
| Speech | `ai4bharat/indic-conformer-600m-multilingual` (ONNX, CTC), `services/asr` |
| Language model | `Qwen/Qwen2.5-7B-Instruct-AWQ` on vLLM with JSON-schema constrained output, `services/llm` |
| Content | YAML rules, pathways, danger signs, schemes and references, validated against `schemas/` |

All AI calls go through provider interfaces with deterministic mocks, so the app and the full test suite run on a laptop without a GPU or network.

## Running

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node.js 24.

```bash
make setup    # install backend and frontend dependencies
make dev      # API on :8000 and web app on :5173, with mock AI providers
make seed     # synthetic demo accounts and people (login 9000000001 / PIN 1234)
make check    # lint, type checks, backend, frontend and end-to-end tests
```

With the real models on a GPU server (two GPUs, each used up to half):

```bash
make demo-reset   # fresh demo database
make demo         # speech model (GPU 0), language model (GPU 1), API and web app
make eval         # score extraction on the synthetic evaluation set
```

See `services/asr/README.md` and `services/llm/README.md` for model setup. Settings are listed in `.env.example`.

## Repository layout

```
backend/     FastAPI app: rules engine, extraction pipeline, schemes, storage, tests
frontend/    React web app and Playwright end-to-end tests
services/    GPU services: speech (IndicConformer) and language model (vLLM)
rules/       Fact registry, danger signs, pathways, output checks
knowledge/   Official references (with verbatim excerpts), schemes, facilities
schemas/     JSON Schemas for all content files
evals/       Synthetic evaluation cases and reports
```

## Team

Vedant Agrawal and Prasanta Chettri, M.Tech Signal Processing, IISc.
