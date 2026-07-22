# Eval-Scoring Script — Report

**Date:** 2026-07-20/21
**Scope:** Per `doc/kickoff-brief-eval-scoring.md`.

## What was built

`data-prep/eval_runner_v3.py` — a scoring runner for `fastapi-eval-suite-v3.jsonl` against the trained Backend specialist. Reuses (does not reimplement) `_fmt`/`_jsonpath`/`_OPS` from `eval_runner.py` and `extract_files` from `orchestrator/llm_client.py`. Adds a multi-file-capable app loader (`load_app_from_files`) since production output can be more than one file, `build_prompt` matching the exact v3 training format, and `score_task`/`score_all` scoring functions with category breakdown.

A new cell was added to `fastapi_lora_qlora_colab.ipynb` (section 11) that loads the trained adapter via `PeftModel.from_pretrained`, wraps it in a `generate_fn`, and calls `score_all` — plus a section 12 cell cross-referencing failures against the three flagged dataset limitations (SQLite/Postgres gap, single-feature bias, design_tokens content).

## Verification performed (without GPU access)

This local environment has no GPU/Colab access, so the trained adapter itself could not be run from here. Instead, the **checker logic** was verified against hand-written reference solutions — same standard as the original `eval_runner.py` validation:
- A correct single-file solution → passed
- A correct **multi-file** solution using a cross-file relative import (`from models import Bookmark`) → passed, confirming the new multi-file loader genuinely resolves imports, not just falling through to a single-file path
- A deliberately-wrong solution (missing `status_code=201`) → failed with the exact expected reason
- A garbled/non-delimited response → failed gracefully as a parse failure, not a crash

All 4 cases behaved exactly as expected. `score_all`'s aggregation was also tested end-to-end against the full 31-task suite with a fake always-fails generator, confirming correct category/overall counting.

## Status

The script is built and its logic is verified. Actually scoring the real trained adapter requires running the new notebook cell in Colab (where the GPU and the adapter in Drive both live) — that execution step is outside what this local session can perform. **Superseded in practice:** the follow-on Round 1/Round 2 augmentation work (see `doc/architecture.md` Testing Log and `doc/round2-augmentation-report.md`) did run real scoring against the trained adapter in Colab and got concrete results (8/31 → 13/31 after Round 1), confirming the eval runner works end-to-end in its intended environment.
