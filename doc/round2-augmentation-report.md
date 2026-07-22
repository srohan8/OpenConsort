# Round 2 Dataset Augmentation + Permanent Eval Runner — Report

**Date:** 2026-07-22
**Scope:** Per `doc/kickoff-brief-round2-augmentation.md`, follow-on to Round 1 (`doc/architecture.md` Testing Log, 2026-07-21: 8/31 → 13/31).

## Part 1: Round 2 Dataset Augmentation

### New examples added per priority bucket

All 11 examples were written as complete FastAPI reference solutions with matching `check_spec`s, executed via `TestClient`, and confirmed to pass **before** being added — nothing here is trusted on visual plausibility alone (`data-prep/round2_examples.py` holds the source; `data-prep/build_and_append_round2.py` did the verify-then-append).

**Priority 1 — Field placement (5 examples, target range was 4–6):**
| # | Method/placement | Task | Category |
|---|---|---|---|
| 1 | GET, query-only | `/search?keyword=...` (422 if missing) | `path-query-params` |
| 2 | POST, body-only | `/reviews` `{rating, comment}` (422 if missing) | `pydantic-models` |
| 3 | DELETE, path-only | `/sessions/{session_id}` (204/404) | `crud` |
| 4 | PUT, path+body mixed | `/accounts/{account_id}` `{balance}` | `crud` |
| 5 | PATCH, path+body mixed | `/orders/{order_id}` `{status}` | `crud` |

Field names deliberately varied and none reused from Round 1's `latitude`/`longitude`/`year` — `keyword`, `rating`/`comment`, `session_id`, `account_id`/`balance`, `order_id`/`status` — per the brief's instruction to teach the placement *rule*, not memorize specific field names.

**Priority 2 — Undefined-name/missing-import generalization (3 examples, target range was 3–5, deliberately NOT more SQLAlchemy):**
| # | Pattern demonstrated | Category |
|---|---|---|
| 6 | Custom `InvalidCoupon` exception, properly defined + registered handler | `pydantic-models` |
| 7 | Custom `RateLimited` exception, properly defined + registered handler | `error-handling` |
| 8 | Custom `require_admin` dependency function, properly defined + used via `Depends` | `dependency-injection` |

Each demonstrates the general habit ("always define/import everything you reference") across categories Round 1's SQLAlchemy-only fix never touched.

**Priority 3 — Business-logic depth (3 examples, target range was 2–3):**
| # | Behavior | Variation from Round 1 | Category |
|---|---|---|---|
| 9 | Ownership-based 403 (`X-User-Id` must match resource owner) | Not the `X-Role` header pattern from Round 1 | `auth-jwt` |
| 10 | Per-client rate limit → 429 after 3 requests | Trigger condition varied (per-`X-Client-Id`, not a global counter) | `error-handling` |
| 11 | Pagination with TRUE total count (not page size) + 422 on invalid `page`/`limit` | 2 validation rules in one example (page<1, limit>100) | `pagination` |

### Verification results

All 11 examples: **verified twice** — once standalone (`round2_examples.py` + `eval_runner.run_eval`), once again independently at append time inside `build_and_append_round2.py` (re-running `run_eval` right before writing to disk, belt-and-suspenders against any edit-after-verify drift). All 11 passed both times, first attempt, no fixes needed.

### Output confirmation

- **All rows (old + new) share identical key sets** — asserted programmatically in `build_and_append_round2.py`, not just visually checked.
- **Every new row's `output` field round-trips through the real `extract_files` parser and matches its `code` field exactly** — asserted per-row before any row was written (a mismatch would have raised `AssertionError` and aborted the whole append, not silently written bad data).
- **Final row count: 93** (82 existing + 11 new).
- **Category breakdown (full dataset, all 93 rows):**

| Category | Count |
|---|---|
| `crud` | 12 |
| `error-handling` | 10 |
| `pydantic-models` | 10 |
| `auth-jwt` | 8 |
| `database-sqlalchemy` | 8 |
| `path-query-params` | 8 |
| `dependency-injection` | 7 |
| `pagination` | 7 |
| `response-status-codes` | 6 |
| `background-tasks` | 5 |
| `file-upload` | 4 |
| `middleware-cors` | 4 |
| `routing-structure` | 4 |

## Part 2: Permanent, Reusable Eval Runner

`data-prep/eval_runner_v3.py` is now the committed, permanent scoring script (chosen location: `data-prep/`, alongside the dataset it scores — the "more sensible location" call per the brief, since `orchestrator/` shouldn't depend on `data-prep`-specific eval-suite conventions). It already existed from the prior eval-scoring task; this task refactored and hardened it to match the brief's exact spec:

- **`extract_files`** — imported from `orchestrator/llm_client.py`, not duplicated (unchanged, still the exact production parser).
- **`load_app_from_files(files)`** — writes generated files to a temp dir, imports the entrypoint module, returns the `app` object. (Renamed from `_load_app_multifile` to match the brief's suggested name exactly.)
- **`run_check_spec(app, check_spec)`** — newly extracted as its own function (previously inlined inside the multi-file runner) so "load an app" and "drive it through a check_spec" are two separately-reusable, separately-testable pieces, per the brief's explicit ask. Handles `$.field` capture and `{var}` substitution between steps, same semantics as the original `eval_runner.py`.
- **CLI entrypoint** — `python eval_runner_v3.py --smoke-test` (no GPU needed, validates the checker itself) or `python eval_runner_v3.py --eval-suite <path> --results <path>` (scores pre-computed model outputs saved from a Colab run) — covers both callable-generator and pre-computed-results usage the brief asked for.

### Smoke test confirmation

Ran `python eval_runner_v3.py --smoke-test` against 4 hand-written cases:

```
[OK] single-file correct: passed=True (expected True)
[OK] multi-file correct (cross-file import): passed=True (expected True)
[OK] deliberately wrong (missing 201): passed=False (expected False) - step 0: expected status 201, got 200
[OK] garbled / unparseable: passed=False (expected False) - parse failure: No ---FILE: ... --- blocks found

SMOKE TEST: PASSED
```

All 4 outcomes matched expectations exactly, confirming: correct code passes, incorrect code fails with the right reason, cross-file imports genuinely resolve (not a false positive from falling back to single-file), and malformed output fails gracefully rather than crashing. Also re-ran the full 31-task aggregation path (`score_all`) against a fake always-fails generator to confirm no regression from the refactor — still reports 31/31 total correctly.

### Why this matters going forward

This closes the "re-pasted into Colab each session, lost twice already" problem the brief described. Every future retrain (Round 3, Frontend once trained, etc.) can `!git clone`/upload this one file and call `score_all`/`score_from_precomputed` rather than reconstructing the scoring logic from memory.

## What was NOT done (per the brief's explicit scope limits)

- No retraining — this task only produced the augmented dataset (93 rows) and the eval runner script. Retraining Round 2 is a separate next step, in Colab (GPU required).
- PostgreSQL verification gap untouched — still a separately-tracked item.
- Frontend training dataset not started — separate item.
- `orchestrator/llm_client.py`/`CONTRACT.md` untouched — `extract_files` reused as-is.

## Recommended next step

Retrain on the 93-row dataset (Colab, same LoRA/QLoRA pipeline as Round 1) and rescore against `fastapi-eval-suite-v3.jsonl` using the now-permanent `eval_runner_v3.py`. Given Round 1's pattern (single examples didn't generalize, but this round deliberately used 3-5 varied examples per pattern instead of 1-2), the clearest signal to watch for is whether the **field-placement** failure cluster (7+ occurrences, now targeted with 5 varied examples) shows a meaningfully larger improvement than Round 1's single-example fixes did — that would validate the "varied examples teach the rule" hypothesis directly.
