# Custom Orchestrator Prototype — Report

**Date:** 2026-07-20
**Scope:** Per `doc/kickoff-brief-custom-orchestrator.md`. Prototype at `orchestrator/` (separate venv, separate from MetaGPT and data-prep).

## 1. Is the JSON schema set workable for the 4 handoffs?

**Yes, largely — with one real caveat found by actually using it.** Four schemas defined (`orchestrator/schemas/`): `LockedSpec`, `UserFlow`, `DesignTokens`, `CodeOutput`.

- **Planning and Design stages worked cleanly on the cloud model on the first attempt, every time** — zero repair loops needed. This is a stark, direct contrast to MetaGPT: the prior trials repeatedly hit `parse_commands` repair cycles and outright protocol failures. A simple "here's your schema, return an instance" contract with a forgiving JSON extractor (handles prose-wrapped/fenced JSON — see `llm_client.extract_json`) was sufficient.
- **The Backend stage (code-bearing) needed two rounds of real iteration** to get a schema-valid response, even from a capable cloud model in earlier testing and especially from the small local model:
  1. First attempt: the model **echoed the schema definition back verbatim** as if that were the answer, instead of producing an instance of it. Fixed by adding a concrete example instance to the prompt and explicitly stating "not the schema itself."
  2. Second attempt: the model produced a real instance, but used **Python triple-quote syntax (`"""..."""`) for the multi-line code content** instead of valid JSON string escaping (`\n`, `\"`) — invalid JSON. Fixed by adding an explicit example showing correctly-escaped multi-line content.

**Takeaway on the schema design itself:** asking any model — cloud or small local — to embed a full multi-line source file as a properly-escaped JSON string value is a real point of friction, independent of model size. It's a **contract design smell**, not just a small-model weakness (see recommendation #5).

## 2. Did the orchestrator work end-to-end with cloud models?

**Yes, confirmed working end-to-end**, after fixing one infra quirk unrelated to the orchestrator's design: the user's local Omniroute router (`My-combo`) round-robins across multiple upstream providers (Cerebras, Cloudflare Workers AI, Pollinations AI, NVIDIA NIM). Whichever provider lacks valid credentials on a given call surfaces as an HTTP **404** with a nested `"[401]: Authentication required..."` message in the body — not a real 401, and not something a naive retry-on-401 check would catch. Fixed with a small retry/backoff wrapper in `llm_client.py` that retries on `{401, 404, 429, 500, 502, 503}` — a natural retry lands on a different (working) upstream provider. This is an infrastructure quirk of the router, not an orchestrator design flaw.

Two other small bugs found and fixed along the way:
- A logging-order bug: `log_stage()` was called *after* schema validation, so validation failures never got logged, hiding the actual bad output. Fixed by logging before validating.
- The same Windows `cp1252` Unicode-encoding crash seen in the MetaGPT trials (a `✅` character in generated content broke `Path.write_text()` without an explicit encoding). Fixed with `encoding="utf-8"` everywhere files are written — a two-line fix, versus MetaGPT where this required an environment-variable workaround (`PYTHONIOENCODING`) because the crash happened deep inside a third-party logging path we didn't control.

## 3. THE key hypothesis test: did the local Ollama model succeed at the Backend stage?

**Mixed, but honestly a clear improvement over MetaGPT — be precise about what "succeeded" means here.**

- **On the tool-calling/protocol dimension — the actual thing this experiment set out to test — yes, unambiguously.** `qwen2.5-coder:1.5b` was never asked to navigate a multi-step ReAct loop or emit `{"command_name": ...}` tool-call arrays. Once the prompt correctly specified "return one JSON object shaped like this, with an example," the local model **did produce a schema-valid `CodeOutput` object** on the final attempt — no crash, no `KeyError`, no framework-level failure. This directly confirms the core hypothesis from `doc/phase1-patch-report.md`: **small models are not incapable of participating in this pipeline — they were specifically incapable of MetaGPT's strict, self-repairing tool-call protocol.** Given a simple, direct, single-turn contract instead, the same model class of failure (structural/protocol failure) did not recur.
- **On code quality/completeness — a separate, softer finding — no, not fully.** The final generated file was a generic Express.js "Hello World" stub, consistent with the spec's chosen stack (Node.js, picked by that run's Planning stage) but **not actually implementing the three required features** (add/list/complete tasks) or touching the specified SQLite database. This is a capability/instruction-following gap, not a protocol failure — the model produced valid, well-formed output that didn't fully do the job.

**Comparison, stated plainly:** MetaGPT's failure was catastrophic and unrecoverable within the run (a Python exception crashing the whole pipeline, caused by a protocol the model could never have been expected to follow reliably). This prototype's remaining gap is qualitatively smaller and iterable: it's a "get better instruction-following or fine-tune for the actual task" problem, addressable through prompting, few-shot examples, or (the project's actual long-term plan) fine-tuning a real backend specialist — not an architectural dead end. That distinction is the main finding of this whole exercise.

## 4. Friction found this session

- OmniRoute's multi-provider round-robin causing intermittent 404-with-nested-401 errors — fixed with retry/backoff.
- Windows `cp1252` Unicode file-write crash — fixed with explicit `utf-8` encoding (recurring class of bug from the MetaGPT trials, but far cheaper to fix here since it's our own code).
- Log-order bug hiding validation failures — fixed by logging before validating.
- Schema-echo issue (model returning the schema instead of an instance) — fixed with a concrete example + explicit instruction.
- JSON-escaping-of-multiline-code issue — fixed (for this run) with an explicit escaping example; flagged below as worth a deeper contract fix rather than continued prompt patching.
- A file-writing bug in the orchestrator itself (didn't create nested parent directories, e.g. `src/index.js`) — fixed with `mkdir(parents=True, exist_ok=True)`.

## 5. Recommendation on next steps

1. **Redesign the code-bearing contract to avoid JSON-embedded multi-line strings entirely.** Rather than asking any model (small or large) to produce a perfectly-escaped JSON string containing a full source file, have specialists emit plain delimited text, e.g.:
   ```
   ---FILE: main.py---
   <raw, unescaped code>
   ---END---
   ```
   and have the orchestrator's own parser split on those delimiters into the `CodeOutput` structure. This sidesteps the escaping failure mode entirely and is a better fit for the project's "narrow, forgiving contract" philosophy — it removes a source of friction that isn't really about model capability at all.
2. **Add stronger content/instruction-following checks, not just schema validation.** Schema validation confirms shape, not correctness — this run showed a schema-valid response that didn't implement the requested features. Consider a lightweight follow-up check (e.g., does the generated code reference each required feature keyword, or a quick execution smoke test) before accepting a stage's output.
3. **Add the Frontend stage**, following the same pattern now proven for Backend.
4. **Begin real specialist fine-tuning**, using the already-verified `data-prep/fastapi-backend-pairs.jsonl` (71 executed-and-verified task→code pairs) as training data — this prototype's finding that small models handle simple direct contracts well (once the contract itself is well-designed) is the green light to proceed with that track rather than revisiting MetaGPT further.
5. **Generalize the retry/backoff wrapper** to all stages by default (currently applied uniformly already, but worth keeping as a standing pattern for any future upstream router quirks) rather than something to rediscover per integration.
