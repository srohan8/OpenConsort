# Kickoff Brief for Claude Code — Score Trained Adapter Against Eval Suite

**Context:** The first fully contract-faithful Phase 1 Backend specialist has been trained (LoRA adapter at `fastapi-backend-lora` in Drive, trained on `fastapi-backend-pairs-v3.jsonl`, 54 steps, loss ~0.09 final). It passed one held-out spot-check (a health-check endpoint). Now score it against the full 31-task eval suite (`fastapi-eval-suite-v3.jsonl` or the v2/original version — confirm which is the right one to use, see step 1) to get a real measure of quality, not just one lucky prompt. Reference `doc/architecture.md`, `RESHAPE-V3-REPORT.md`, and the original data-prep brief's eval-suite design for background.

## Goal of this task

Build (or adapt, if one already exists from the original data-prep phase) a script that:
1. Loads the trained base model + LoRA adapter
2. For each of the 31 eval tasks, constructs the real production-shaped prompt (same `BACKEND_SYSTEM` + `LockedSpec`/`DesignTokens` + `### Response:` format used in training/inference)
3. Generates a response
4. Parses it with the real `extract_files` parser (from `orchestrator/llm_client.py`) — same parser production uses, not a reimplementation
5. Runs each task's `check_spec` (the machine-checkable success criteria already defined in the eval suite) against the generated code
6. Reports a pass/fail per task and an overall score

## Steps

1. **Confirm which eval suite file matches the v3 training format.** The original `fastapi-eval-suite.jsonl` (31 tasks) may need the same input-shape reshaping that was done for the training pairs (v2 → v3). Check whether a `fastapi-eval-suite-v3.jsonl` already exists (it was mentioned as a possible output of the dataset-reshaping work) with `system_prompt`/`user_prompt`/`locked_spec`/`design_tokens` fields matching the real contract, alongside its original `check_spec`. If it doesn't exist yet, that's the first thing to produce — reuse the same reshaping approach/script used for the training pairs (`reshape_to_orchestrator_input.py`), applied to the eval suite instead.

2. **Write the scoring script** (e.g. `eval_runner_v3.py` or extend the existing `eval_runner.py` if one exists from the data-prep phase):
   - Loads `Qwen/Qwen2.5-Coder-1.5B` + the trained LoRA adapter from Drive (same loading pattern as the notebook's inference cell)
   - For each task: build the prompt, generate (same generation params as the notebook: `do_sample=False`, reasonable `max_new_tokens`, gradient checkpointing disabled, eval mode — reuse the exact fix from the notebook, don't regress on this)
   - Parse with the real `extract_files` — if parsing fails for a task, that's an automatic fail for that task, log why
   - Write the generated file(s) to a temp directory, then run that task's `check_spec` against it (however the original eval runner does this — likely spins it up with `TestClient` and asserts the expected behavior, per the original data-prep verification standard)
   - Collect pass/fail + any error/failure detail per task

3. **Run it** (in Colab, since it needs the GPU/adapter — can be a new cell in the existing notebook, or a separate script run in the same session) and produce a results table: task name/category, pass/fail, failure reason if applicable.

4. **Compute and report an overall score** (e.g. X/31 passed) and break it down by category (the original 13 categories from `task-categories.md`) so it's clear whether failures cluster in specific areas (e.g., auth-related tasks, DB-related tasks) rather than being evenly spread.

5. **Cross-reference failures against the three known dataset limitations** flagged in `architecture.md`'s Open Risks:
   - Do DB-related eval tasks fail or produce SQLite-specific code where the spec implies PostgreSQL? (tests the SQLite/Postgres gap)
   - Do any eval tasks involve multi-feature specs, and if so, do those fail more than single-feature ones? (tests the `features: [single_task]` training bias)
   - Does anything suggest the model ignores `design_tokens` content, or would design_tokens content plausibly have changed correct behavior? (tests the constant-design_tokens gap — likely low signal for Backend specifically, note if so)

## What NOT to do in this task

- Don't retrain the model based on results yet — this task is scoring only. Retraining/dataset augmentation is a decision for after seeing results.
- Don't fix the PostgreSQL gap as part of this task, even if it shows up as a failure cause — just document it clearly as evidence for that decision.
- Don't modify `orchestrator/llm_client.py` or `CONTRACT.md` — reuse them as-is for parsing.

## Definition of done

- A working scoring script and its full run output (pass/fail per task, category breakdown, overall score)
- A short report answering: what's the overall score? Do failures cluster anywhere? Does the evidence support or undercut any of the three flagged dataset limitations? What's the recommended next action based on these results (e.g., "SQLite tasks fail badly, prioritize the Postgres lane" vs. "results are solid across the board, proceed to Frontend fine-tuning")?
