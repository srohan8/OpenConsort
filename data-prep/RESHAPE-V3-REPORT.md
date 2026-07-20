# Dataset Input Reshape — v2 → v3 (real orchestrator prompt shape)

**Date:** 2026-07-20
**Trigger:** review of `orchestrator.py`/`llm_client.py`/schemas showed the Backend
stage's real `user_prompt` is `f"LockedSpec:\n{json.dumps(locked_spec)}\n\nDesignTokens:\n{json.dumps(design_out)}"`
— not the placeholder free-text `task` field v1/v2 trained on.

## What changed

v2 trained the model on `{"task": "plain English", "output": "...delimited..."}`.
In production, the Backend specialist **never sees free text** — it only ever
receives a validated `LockedSpec` + `DesignTokens` pair, via the exact system/user
prompt built in `orchestrator.py`. Training on free-text input would teach the
model an input shape it will never actually receive at inference.

v3 adds, to every row:
- `system_prompt` — **imported directly** from `orchestrator.BACKEND_SYSTEM`, not retyped.
- `locked_spec` — schema-valid (`locked_spec.schema.json`), Phase-1 stack
  (FastAPI/React+Vite/PostgreSQL/JWT, per `architecture.md`), `features: [task]`
  (the original free-text task reused verbatim as the single feature item —
  lossless, matches the schema's own feature-string style, no fabrication).
- `design_tokens` — schema-valid (`design_tokens.schema.json`), a constant
  placeholder object. DesignTokens don't drive backend code content (that's a
  Frontend/UI concern), but the real prompt always includes them, so a constant
  schema-valid object preserves prompt *shape* fidelity without inventing
  per-pair visual fiction the training pairs have no grounding for.
- `user_prompt` — built with the **identical f-string template** as
  `orchestrator.py:211`.
- `input_format` = `"locked_spec+design_tokens-v1"` marker.

Applied identically to both `fastapi-backend-pairs-v2.jsonl` → `-v3.jsonl` (71 rows)
and `fastapi-eval-suite-v2.jsonl` → `-v3.jsonl` (31 rows). All v2 fields preserved
unchanged (asserted field-by-field); v2/v1 files untouched.

## Why this avoids a second reshape-and-retrain cycle

- `BACKEND_SYSTEM` and both JSON schemas are **loaded/imported from the live
  `orchestrator/` files**, not hand-copied — if the real prompt or schema
  changes, re-running `reshape_to_orchestrator_input.py` regenerates v3 correctly
  instead of silently drifting.
- The reshape script **asserts** `user_prompt` is byte-reproducible from
  `build_user_prompt(locked_spec, design_tokens)` (the same template as
  `orchestrator.py`), and that `system_prompt == BACKEND_SYSTEM` exactly.
- Every `locked_spec`/`design_tokens` object is validated against the real
  `jsonschema` schema files before being written — a malformed spec fails the
  script rather than silently entering the training set.

## Verification performed

1. **Ground-truth fidelity** (`reshape_to_orchestrator_input.py`, runs at build
   time): every row's `user_prompt` reproduced exactly by the same f-string
   template used in `orchestrator.py:211`; `system_prompt` exact-matches the
   imported `BACKEND_SYSTEM` constant; embedded `locked_spec`/`design_tokens`
   JSON parses back out of the prompt string identical to the structured fields.
2. **Losslessness**: every field present in v2 is asserted unchanged in v3
   (task, code, output, category, verified, verification_notes, file_path,
   contract_format) — 71/71 backend rows, 31/31 eval rows.
3. **Schema validation**: every `locked_spec` and `design_tokens` object
   validated against `orchestrator/schemas/locked_spec.schema.json` and
   `design_tokens.schema.json` via `jsonschema.validate` — 102/102 pass.
4. **Manual inspection** of a sample row confirms shape matches production
   exactly (see example below).
5. **Notebook wiring** (`data-prep/patch_notebook.py`, applied once): the
   Colab notebook's `DATA_PATH` now points at `fastapi-backend-pairs-v3.jsonl`,
   and `format_example()` builds `prompt` from `system_prompt + user_prompt`
   (falling back to the old task/code shape only for its embedded dummy pairs,
   which predate the reshape). **Ran `format_example` against real v3 data
   outside the notebook** (no GPU needed for this check) and confirmed: real
   newlines present, `completion == output` field, prompt text matches the
   live `BACKEND_SYSTEM` + LockedSpec/DesignTokens JSON exactly.

## Sample row (`fastapi-backend-pairs-v3.jsonl`, line 1)

```
user_prompt:
LockedSpec:
{"version": 1, "product_type": "web_app", "stack": {"backend": "FastAPI", "frontend": "React + Vite", "database": "PostgreSQL", "auth": "JWT-based", "payments": null}, "features": ["Create a FastAPI app with an in-memory list of items and a GET /items endpoint that returns all items."]}

DesignTokens:
{"version": 1, "spec_version": 1, "colors": {...}, "typography": {...}, "spacing": {...}}
```

## Flags for human review

1. **`design_tokens` is a constant placeholder across all 71+31 rows.** If
   design-token *diversity* matters for training (e.g. testing whether the
   Backend specialist correctly ignores irrelevant DesignTokens content), that
   would need deliberately varied — not fabricated-per-pair — tokens. Left as-is
   here since DesignTokens has no bearing on correct backend code.
2. **`features: [task]` is a single-feature list.** Real LockedSpecs from the
   Planning stage will usually list multiple features per build. This dataset's
   pairs are each a single isolated task, so a single-feature list is the
   honest mapping — not a shortcut. Worth knowing if a future dataset wants to
   train on multi-feature specs producing multi-file output.
3. Same PostgreSQL/SQLite gap as before — still unaddressed, still out of scope
   here.
4. `patch_notebook.py` is a one-off patch script (kept for reference/
   re-application if the notebook is regenerated from scratch); it's not part
   of the reusable pipeline.

## Files

| File | Status |
|------|--------|
| `fastapi-backend-pairs-v3.jsonl` | NEW — 71 rows, real orchestrator input shape |
| `fastapi-eval-suite-v3.jsonl` | NEW — 31 rows, same input restructuring |
| `fastapi_lora_qlora_colab.ipynb` | MODIFIED — trains on v3 system/user_prompt+output |
| `reshape_to_orchestrator_input.py` | reshape script (imports real BACKEND_SYSTEM + schemas) |
| `patch_notebook.py` | one-off notebook patch (kept for reference) |
| v1/v2 files | untouched |
