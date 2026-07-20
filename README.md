# OpenConsort

Democratized AI coding on a normal consumer PC — no GPU required — using small,
specialized local models coordinated through stable, versioned contracts instead
of one large general-purpose model doing everything.

See [`doc/architecture.md`](doc/architecture.md) for the full working design
document (goals, decisions, open questions). This README covers what's actually
built and how to run it.

## Status

Early-stage, actively being validated end-to-end. Not production-ready. See
`doc/*-report.md` for what's been tested and confirmed so far.

## Pipeline

```
Planning  ->  Design  ->  Backend  ->  Frontend
```

A fixed, four-stage pipeline (`orchestrator/orchestrator.py`):

- **Planning** — one-line product idea in, `LockedSpec` + `UserFlow` JSON out.
- **Design** — `LockedSpec` + `UserFlow` in, `DesignTokens` JSON out.
- **Backend** — `LockedSpec` + `DesignTokens` in, backend source files out.
- **Frontend** — same pattern as Backend, produces frontend source files.

Each stage has one direct input and one direct output, validated against a
JSON schema (`orchestrator/schemas/`). No tool-calling loop, no shared "team"
LLM config — deliberately simpler than a general agent framework, so a small
local model only ever has to do one narrow job per call.

**Planning/Design** respond with plain JSON. **Backend/Frontend** (code-bearing
stages) respond with a delimited plain-text format instead of JSON-embedded
code — see [`orchestrator/CONTRACT.md`](orchestrator/CONTRACT.md) for why (JSON
escaping of multi-line code was a real, distinct failure mode for small models)
and the exact format:

```
---FILE: path/to/file.py---
<raw, unescaped code>
---END---
```

Each stage's LLM backend is configured independently (`build_stage_llms` in
`orchestrator.py`) — stages can run against a cloud model or a local
[Ollama](https://ollama.com)-served model, mixed per stage, so a single role
can be swapped to local without touching the rest of the pipeline.

## Running the orchestrator

```bash
cd orchestrator
python -m venv .venv
.venv/Scripts/activate      # Windows; use `source .venv/bin/activate` on Unix
pip install openai jsonschema

cp ../.env.example ../.env  # fill in your real API key
python orchestrator.py --idea "A CLI to-do list app that supports adding, listing, and completing tasks"
```

Generated files land in `orchestrator/generated/`; per-stage prompts/responses
are logged to `orchestrator/logs/` for inspection.

To route a stage to a local model, run Ollama (`ollama serve`, with a model
pulled, e.g. `ollama pull qwen2.5-coder:1.5b`) and adjust `build_stage_llms`
in `orchestrator.py`.

## Training data (`data-prep/`)

A curated, **executed-and-verified** FastAPI backend dataset for fine-tuning a
small local specialist model:

- `fastapi-backend-pairs.jsonl` — 71 task→code pairs. Every pair was actually
  run under `TestClient` and asserted against expected behavior before being
  kept; nothing here is "looks plausible."
- `fastapi-eval-suite.jsonl` — 31 held-out tasks, independent of the training
  pairs, each with a machine-checkable multi-step HTTP success criterion.
- `fastapi_lora_qlora_colab.ipynb` — LoRA/QLoRA fine-tuning notebook (HF
  `transformers` + `peft` + `bitsandbytes`) for a small 1–3B base model,
  meant to run on Google Colab (training needs a GPU; local inference doesn't).

The dataset exists in three versions as it was progressively reshaped to match
the real orchestrator contract (see `data-prep/RESHAPE-REPORT.md` and
`RESHAPE-V3-REPORT.md` for what changed and why):

| Version | Shape | Use |
|---|---|---|
| `*.jsonl` (v1) | `{"task": "...", "code": "..."}` | original verified data |
| `*-v2.jsonl` | adds `output` in the delimited-text contract format | contract-shaped completion |
| `*-v3.jsonl` | adds `system_prompt`/`user_prompt` matching the real `LockedSpec`+`DesignTokens` Backend prompt | **current** — matches production input+output shape; what the notebook trains on |

## Repo layout

```
orchestrator/     Fixed-pipeline orchestrator, LLM client, JSON schemas, contract spec
data-prep/        Verified training pairs, eval suite, reshape scripts, LoRA notebook
doc/              Architecture doc, kickoff briefs, and dated trial/test reports
```

`doc/` kickoff briefs (`kickoff-brief-*.md`) scope individual work sessions;
their matching `*-report.md` files record what was actually tested and found.
Read `doc/architecture.md` first for the why, then the reports in date order
for what's been validated so far.

## Secrets

Copy `.env.example` to `.env` and fill in real values — `.env` is gitignored.
Never commit API keys directly into `orchestrator.py` or MetaGPT-style config
files (`config2.yaml` is gitignored for this reason).
