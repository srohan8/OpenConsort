# Kickoff Brief for Claude Code — Reshape Training Dataset to Match Contract Format

**Context:** This runs as a separate/parallel session to the delimited-text contract redesign work (`kickoff-brief-delimited-contract.md`), which may still be in progress elsewhere. Reference `doc/architecture.md` and `doc/custom-orchestrator-report.md` for background.

**Dependency check — do this first, don't skip:** This task needs the finalized delimited-text contract format for code-bearing outputs (the `---FILE: path---\n<code>\n---END---` style format, or whatever it ends up as after testing). Before starting, check whether `doc/` or the `orchestrator/` folder has a report or spec file documenting the finalized format (e.g. look for something like `contract-redesign-report.md`, or the updated schema/parser code in `orchestrator/`). 

- **If the finalized format is available:** proceed with the steps below using that exact format.
- **If it is NOT yet available:** do not guess or invent a format. Instead, do the parts of this task that don't depend on it (see "Can start regardless" below), and clearly flag in your report that the final reshaping step is blocked pending the contract format.

## Goal of this task

Reshape the existing training data (`data-prep/fastapi-backend-pairs.jsonl`, 71 verified pairs, and `data-prep/fastapi-eval-suite.jsonl`, 31 tasks) so the `task` field's expected output format matches the real orchestrator contract — not the original ad-hoc format used when the dataset was first built (before the contract was designed).

## Why this matters

The specialist model is meant to be trained to produce output in the *exact* format the orchestrator will actually hand it in production. If the training data still reflects an old/placeholder format, the fine-tuned model would learn to produce output that doesn't match what the real pipeline expects — meaning it would need to be retrained anyway once this mismatch was discovered. This step exists to avoid that wasted cycle.

## Steps

1. **Confirm the exact contract format** (see Dependency check above).
2. **Review the current `fastapi-backend-pairs.jsonl` structure** — recall the existing shape:
   ```json
   {"task": "...", "code": "...", "category": "...", "verified": true, "verification_notes": "..."}
   ```
   Decide what changes: likely `code` needs to be reformatted to match the new delimited-text contract (e.g., wrapped as `---FILE: main.py---\n<code>\n---END---` instead of a raw/JSON-escaped string), and/or the `task` field itself may need restructuring if the real contract expects more structured input (e.g., matching a `LockedSpec`-shaped input) rather than a free-text task description.
3. **Reshape all 71 pairs programmatically** — write a script to transform the existing dataset into the new format rather than manually rewriting each entry. Verify the transform is lossless (no pairs dropped, no code content altered beyond the formatting change).
4. **Re-verify a sample after reshaping** — spot-check (or re-run the original execution/verification harness from the data-prep phase) on a handful of reshaped pairs to confirm the reshaping didn't introduce corruption (e.g., broken delimiters, truncated code).
5. **Reshape `fastapi-eval-suite.jsonl` the same way** — same transform logic, applied to the 31 eval tasks. Keep the `check_spec` structure (the machine-checkable success criteria) intact; only the task/output-format framing should change, not the correctness-checking logic itself.
6. **Output both reshaped files as new versions**, not overwriting the originals — e.g. `fastapi-backend-pairs-v2.jsonl` and `fastapi-eval-suite-v2.jsonl` — so the original verified data is preserved for comparison/rollback if needed.

## Can start regardless (even if the contract format isn't finalized yet)

- Write the reshaping script's scaffolding/structure now, with the actual format substituted in once confirmed — don't wait idle if there's useful groundwork to do.
- Review the current dataset for any other quality issues worth fixing while reshaping anyway (e.g., double-check the PostgreSQL-vs-SQLite gap noted in `architecture.md` — flag it again here, but don't attempt to fix it as part of this task; that's a separate, already-tracked item).

## What NOT to do

- Don't invent or guess the contract format if it's not yet documented — flag the blocker instead.
- Don't fix the PostgreSQL/SQLite gap in this task — separate, already-tracked item.
- Don't start a new fine-tuning run yet — that's the step after this one, once reshaping is verified.
- Don't modify the `check_spec` correctness-checking logic in the eval suite — only the framing/format around it.

## Definition of done

- Confirmation of which contract format version was used (or a clear flag that this is blocked, with what's been done in the meantime)
- `fastapi-backend-pairs-v2.jsonl` and `fastapi-eval-suite-v2.jsonl` — reshaped versions matching the real contract format
- A short verification note confirming the reshape was lossless and a sample was re-checked for correctness
- Original files left untouched for comparison
