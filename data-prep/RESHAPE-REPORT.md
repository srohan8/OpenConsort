# Dataset Reshape to Contract Format — Report

**Date:** 2026-07-20
**Brief:** `doc/kickoff-brief-reshape-dataset.md`
**Contract source:** `orchestrator/CONTRACT.md` + `doc/delimited-contract-report.md`

## Dependency check — RESOLVED (not blocked)

The finalized code-bearing contract format **is documented and confirmed stable**:

- `orchestrator/CONTRACT.md` specifies the delimited-text format.
- `doc/delimited-contract-report.md` reports it succeeded first-try on both cloud
  and local models and explicitly recommends (rec #1 "stable enough to build on",
  rec #3 "begin reshaping `fastapi-backend-pairs.jsonl` against this contract now").
- The production parser (`orchestrator/llm_client.py` → `extract_files` /
  `FILE_BLOCK_RE`) is the authority I verified against.

**Contract format used:** `delimited-text-v1`
```
---FILE: <path>---
<raw, unescaped code>
---END---
```

## What changed

**Backend pairs** (`fastapi-backend-pairs-v2.jsonl`, 71 rows):
- Added `output` — the code expressed in the delimited contract format. This is the
  real training *completion*: exactly what the Backend specialist must emit and what
  the orchestrator parses in production (the notebook currently trains on the raw
  `code` field; point it at `output` for contract-faithful training).
- Added `file_path` = `main.py` (single-file FastAPI apps; matches the schema's own
  `main.py` example) and `contract_format` = `delimited-text-v1`.
- **Every original field preserved** (`task`, `code`, `category`, `verified`,
  `verification_notes`) — reshape is additive/lossless, not destructive.

**Eval suite** (`fastapi-eval-suite-v2.jsonl`, 31 rows):
- Added `contract_format` = `delimited-text-v1` marker only.
- `task` and `check_spec` left **byte-identical** (asserted). Eval tasks carry no
  reference-code payload — only a runtime `check_spec` — so there is nothing to
  re-delimit; the check logic is output-format-agnostic (it parses whatever the
  model emits at eval time and runs the http_sequence). Per the brief, correctness-
  checking logic was not touched.

## Verification — lossless + re-executed

1. **Full-dataset byte-identity via the REAL parser** (`reshape_to_contract.py`):
   all 71 `output` blocks were parsed with the genuine `extract_files` and each
   reconstructs to exactly one file at `main.py` whose content is **byte-identical**
   to the original `code`. 0 failures. This is the strongest possible corruption/
   truncation/broken-delimiter check — the production parser itself round-trips it.
2. **Sample re-execution** (`verify_reshaped_sample.py`): 8 pairs across 8 categories
   were parsed, checked for delimiter leakage into content, reconstructed, and run
   under FastAPI `TestClient`. All 8 instantiate the app, mount their routes, and
   serve `/openapi.json` — **8/8 execute clean**.
3. **Counts + originals**: v2 files have identical row counts (71 / 31). Original
   files unchanged (md5 `122a3fc6…` backend, `264aa92e…` eval).

## Decisions & flags for human review

1. **`task` field kept as natural-language instruction, not restructured into a full
   `LockedSpec` JSON.** The brief listed that as an optional "and/or". I did NOT do it
   because the source pairs contain no LockedSpec fields (product_type, features,
   stack, etc.) — fabricating them per-pair would inject invented signal into clean
   verified data. If contract-faithful *input* framing is wanted later, it should be
   generated deliberately (e.g. planning-model-derived specs), not guessed here. The
   notebook's `### Task:` prompt maps cleanly to the current free-text `task`.
2. **Filename choice `main.py` is uniform.** Real specialist output lets the model pick
   the path; if you want path diversity in training, vary `file_path` per pair.
3. **PostgreSQL vs SQLite gap** (from `architecture.md`) — re-flagged as instructed,
   **not fixed here** (separate tracked item). DB-category pairs still use in-memory
   SQLite; add a Postgres verification lane before shipping DB specialists.
4. **Notebook not modified** — reshaping only, per "don't start fine-tuning yet".
   To train on the contract format, change the notebook's `completion = ex["code"]`
   to `ex["output"]` (and load the `-v2` file).

## Files

| File | Status |
|------|--------|
| `fastapi-backend-pairs-v2.jsonl` | NEW — 71 pairs, contract `output` added |
| `fastapi-eval-suite-v2.jsonl` | NEW — 31 tasks, contract tag added |
| `fastapi-backend-pairs.jsonl` | unchanged (original preserved) |
| `fastapi-eval-suite.jsonl` | unchanged (original preserved) |
| `reshape_to_contract.py` | reshape script (verifies via real parser) |
| `verify_reshaped_sample.py` | step-4 execution re-check |
