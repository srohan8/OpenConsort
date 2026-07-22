# Kickoff Brief for Claude Code — Round 2 Dataset Augmentation + Permanent Eval Runner

**Context:** Round 1 targeted augmentation (2026-07-21) improved the trained Backend specialist from 8/31 to 13/31 on the eval suite. Full history in `doc/architecture.md`'s Testing Log (search "Round 1 targeted dataset augmentation") and `doc/roadmap.md`. Key lesson from Round 1: **single examples per failure pattern don't teach a generalizable rule** — e.g., 3 SQLAlchemy-specific fixes fully resolved that category, but the same underlying "references something without defining/importing it" bug recurred in unrelated categories (`pydantic-models`, `error-handling`), and single field-placement fixes didn't stop that pattern from recurring elsewhere either.

This task has two parts: (1) generate and verify a Round 2 batch of *varied* examples targeting the remaining failure patterns, and (2) turn the ad-hoc eval-scoring logic (currently re-pasted into Colab each session) into a permanent, reusable script.

## Part 1: Round 2 Dataset Augmentation

### Failure patterns to target (from the Round 1 rescoring — see `architecture.md` Testing Log for full detail)

**Priority 1 — Field placement (now the dominant failure pattern, 7+ occurrences in the last scoring run):**
Model puts a required field in the wrong location (query vs. body vs. path) or omits it entirely. Generate **4-6 varied examples**, not 1-2 — vary:
- The HTTP method (GET with query params, POST with body fields, PUT/PATCH with path + body combined)
- Field names and types (don't reuse `latitude`/`longitude` or `year` from Round 1 — use different field names each time so the model learns the *rule*, not the *specific fields*)
- At least one example with a required field in each of: query-only, body-only, path-only, and a mixed case (e.g., an ID in the path + additional fields in the body)

**Priority 2 — Undefined-name/missing-import generalization:**
This bug is NOT SQLAlchemy-specific — it recurred with `HTTPException`, `Profile`, `RateLimited` in unrelated categories. Generate **3-5 varied examples across DIFFERENT categories** (not more SQLAlchemy — deliberately pick categories like `pydantic-models`, `error-handling`, `dependency-injection`) that each demonstrate complete, self-consistent code where every custom class/exception/import used is actually defined/imported. The goal is reinforcing "always define everything you reference" as a general habit, not fixing one more category.

**Priority 3 — Business-logic depth (unchanged since Round 1, single examples didn't move these):**
Generate **2-3 additional, more varied examples** for:
- Auth/permission enforcement (403 or 401 when a check fails) — vary the check condition (role-based, ownership-based, header-based) rather than repeating the same X-Role pattern from Round 1
- Rate limiting or other request-count-based logic (429) — vary the trigger condition
- Pagination correctness — specifically: returning the TRUE total count (not the page size), and validating page/limit bounds (422 on invalid input) — Round 1's single example didn't fix this, so add 2 variations with different validation rules

### Verification requirement (non-negotiable, same standard as Round 1 and the original data-prep)

**Every new example must be actually executed via `TestClient` and confirmed to pass its own check_spec before being added to the dataset.** Do not add anything based on visual plausibility alone. Follow the same pattern as the Round 1 examples (see `candidate_sqlalchemy_examples.py` and `candidate_buckets_1_2_4_examples.py` if available in the project history/uploads, or reconstruct the pattern: write code + check_spec, execute via `TestClient`, assert against check_spec steps, only keep if it passes).

### Output

Append the verified new examples to `fastapi-backend-pairs-v3.jsonl`, matching the exact existing schema (`task`, `code`, `category`, `verified`, `verification_notes`, `output`, `file_path`, `contract_format`, `system_prompt`, `locked_spec`, `design_tokens`, `user_prompt`, `input_format` — check an existing row for the exact format before writing new ones). Confirm:
- All rows (old + new) share identical key sets
- Every new row's `output` field round-trips correctly through the real `extract_files` parser and matches its `code` field exactly
- Report the final row count and a category breakdown

## Part 2: Permanent, Reusable Eval Runner

### Problem being solved

The eval-scoring logic (parsing generated code, running it via `TestClient`, checking against each task's `check_spec` with `$.field` capture/`{var}` substitution) currently only exists as ad-hoc cells pasted into Colab each session, and gets lost whenever cells are cleaned up — this has happened twice already, wasting time re-deriving/re-pasting the same logic.

### What to build

A committed script (e.g. `data-prep/eval_runner.py` or `orchestrator/eval_runner.py` — pick the more sensible location given the project structure) containing:
- The `extract_files` parser (reuse from `orchestrator/llm_client.py` — import it, don't duplicate it, so it can't drift from the real parser)
- `load_app_from_files(files)` — writes generated files to a temp dir, imports the entrypoint module, returns the `app` object
- `run_check_spec(app, check_spec)` — executes the multi-step HTTP sequence via `TestClient`, handling `$.field` capture and `{var}` substitution between steps, returns (pass/fail, error detail)
- A CLI or simple function entrypoint that: takes a path to an eval suite JSONL file + a way to generate model output (either a pre-computed `results` structure, or a callable that generates given a prompt), runs scoring across all tasks, and prints the same kind of pass/fail + category breakdown + failure-detail report used so far

### Why this matters going forward

Every future retrain (Round 2, Round 3, Frontend once it's trained, etc.) needs this exact same scoring logic. Having it as one committed, tested script means: no more re-pasting into Colab from scratch, no risk of the scoring logic subtly drifting between rounds, and it becomes something that could eventually be imported directly into the Colab notebook (`!git clone` or upload the script) rather than manually reconstructed.

## What NOT to do in this task

- Don't retrain the model yet — this task only produces the augmented dataset and the eval runner script. Retraining happens after, in Colab (GPU required).
- Don't touch the PostgreSQL verification gap — separate, already-tracked item.
- Don't start the Frontend training dataset — separate, already-tracked item.
- Don't modify `orchestrator/llm_client.py` or `CONTRACT.md` — reuse `extract_files` from there as-is.

## Definition of done

- Round 2 examples generated, each executed and verified via `TestClient` before being added
- Appended to `fastapi-backend-pairs-v3.jsonl`, schema-consistent, round-trip verified
- A permanent `eval_runner.py` (or similarly named) script committed to the project, containing the parser/loader/scorer logic, reusable across future rounds
- A short report: how many new examples added per priority bucket, final dataset size, and confirmation the eval runner works (e.g., a quick smoke test against a couple of known-good/known-bad examples)
