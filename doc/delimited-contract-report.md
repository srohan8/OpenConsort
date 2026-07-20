# Delimited-Text Contract Redesign — Report

**Date:** 2026-07-20
**Scope:** Per `doc/kickoff-brief-delimited-contract.md`, follow-on to `doc/custom-orchestrator-report.md`.
**Format spec:** `orchestrator/CONTRACT.md`

## 1. Did the fix work as expected, on both cloud and local models?

**Yes — clean success on the first attempt, on both.**

- **Cloud (`My-combo`):** produced a valid `---FILE: tasks.py---...---END---` block on the first try. No schema-echo, no escaping issue (there's nothing to escape in this format). Parsed and reconstructed correctly.
- **Local (`qwen2.5-coder:1.5b`):** also succeeded on the **first attempt** — a meaningful contrast to the JSON-contract version, which took two rounds of prompt-fixing (schema-echo, then triple-quote/escaping) to get a schema-valid response at all. This time: no iteration needed.

Independent verification: `ollama ps` showed nothing loaded before the run and confirmed the model was invoked during it (same verification method used in the MetaGPT patch trial and the prior orchestrator test).

## 2. New friction found with this format

One small, cosmetic issue, not a failure: the local model copied the **literal placeholder path** from the prompt's format-description section (`path/to/file.py`) instead of choosing a real filename, producing a file at `generated/.../path/to/file.py`. This didn't break parsing or the schema — `FILE_BLOCK_RE` handled the nested path fine — it's purely a "the model pattern-matched an example too literally" issue. Fixed cheaply by rewording the format description to use `<the real path you choose, e.g. app.py>` as a placeholder token instead of a copy-pasteable fake path, and by explicitly telling the model not to reuse the concrete example's filename. Not re-tested after this specific tweak (out of scope to keep re-running for a cosmetic fix), but it's a one-line prompt change with an obvious mechanism, not a new open question.

## 3. Is the content-quality gap (shallow stub code) still present?

**Not present in this run — actually a positive surprise, not something this task tried to fix.** The prior JSON-contract test produced a generic Express "Hello World" stub that ignored the three requested features. This run's local-model output (a Flask app) **implements all three requested features** — `/add_task` (POST), `/list_tasks` (GET), `/complete_task/<id>` (PUT), matching add/list/complete from the LockedSpec.

This is likely not fully attributable to the contract format change alone (model non-determinism plays a role, and the prompt now also includes a one-line reminder — "Implement the features listed in the LockedSpec, not just a placeholder/stub" — added incidentally while rewriting the Backend prompt for the new format). **Don't over-read this as "the content-quality gap is solved"** — it's one run, and the task brief is correct that this should remain a separately-tracked concern (recommendation #2 from the prior report) rather than declared fixed based on a single good result.

## 4. Delimited-text vs. JSON-embedded-code: direct comparison

| | JSON-embedded-code (prior) | Delimited-text (this task) |
|---|---|---|
| Cloud model, first attempt | Worked (in earlier ad-hoc testing) | Worked |
| Local model, attempts needed | 2 rounds (schema-echo, then escaping) | 1 (first attempt succeeded) |
| Failure modes possible | Schema-echo, invalid escaping, malformed JSON | Model not using exact delimiter syntax (didn't occur here), placeholder-path copying (occurred, cosmetic) |
| Parser complexity | `jsonschema` validation + JSON parsing | One regex (`FILE_BLOCK_RE`) + trivial reassembly |
| Robustness to prose-wrapping | Needed careful fenced/brace extraction | Delimiters are found directly in raw text; prose before/after/between blocks is simply ignored |

The hypothesis from the prior report is confirmed: **removing the need to JSON-escape multi-line code content removes a real, distinct failure mode**, and does so with a *simpler* parser than the JSON-schema approach it replaced. This is a clear net improvement, not just a different set of trade-offs.

## 5. Recommendation for next steps

1. **This contract format is stable enough to build on.** Move forward with it as the standard for all code-bearing stages.
2. **Safe to add the Frontend stage next**, using the identical `run_code_stage`/delimited-text pattern already proven for Backend — no new design work needed there, just a new prompt and a call site.
3. **Begin reshaping `data-prep/fastapi-backend-pairs.jsonl` against this contract format** now that it's confirmed stable — per the original kickoff brief's sequencing, this was deliberately deferred until the contract shape settled, and it now has.
4. **Keep the content/instruction-following correctness check as a separate, still-open follow-on** (recommendation #2 from the prior report) — this run's good result is encouraging but not sufficient evidence to consider that gap closed; a repeatable check (e.g., does generated code reference each required feature, or a quick execution smoke test) is still worth building before relying on output quality alone.
