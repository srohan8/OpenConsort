# Kickoff Brief for Claude Code — Delimited-Text Contract Redesign

**Context:** Follow-on to the custom orchestrator prototype (`doc/custom-orchestrator-report.md`). The prototype confirmed the core hypothesis (small models handle simple direct contracts fine; they only fail on strict tool-calling protocols like MetaGPT's RoleZero). But it also found a real, separate friction point: asking any model — cloud or small local — to embed a full multi-line source file as a properly-escaped JSON string value causes failures (schema-echo, and Python triple-quote syntax used instead of JSON escaping). This is a contract design smell, not a model capability problem, and the report's own recommendation #1 is to fix it structurally.

## Goal of this task

Redesign the `CodeOutput` contract (and any other code-bearing handoff) to use **delimited plain text** instead of JSON-embedded escaped strings, removing the escaping failure mode entirely. Re-test the Backend stage against this new contract to confirm the fix holds.

## Steps

1. **Design the delimited-text format.** Per the report's suggestion, something like:
   ```
   ---FILE: path/to/file.py---
   <raw, unescaped code>
   ---END---

   ---FILE: path/to/other_file.py---
   <raw, unescaped code>
   ---END---
   ```
   Confirm this handles multiple files per stage output (a Backend stage may need to produce several files — models, routes, config, etc.), and decide on any needed metadata (e.g., is this a new file or a modification to an existing one?) — extend the delimiter format if needed, but keep it as simple as possible.

2. **Update the orchestrator's parser.** Replace (or supplement) the current JSON-schema-based `CodeOutput` validation with a parser that splits the delimited text into the same internal `CodeOutput` structure the orchestrator already uses downstream — so this is a change to how output is *produced and parsed*, not necessarily to every internal data structure.

3. **Update the Backend stage's prompt** to ask for this delimited format instead of a JSON string field, with a clear example in the prompt (the same lesson from the schema-echo fix — always include a concrete example, not just an abstract description).

4. **Keep the other schemas (LockedSpec, UserFlow, DesignTokens) as JSON** — the report found Planning/Design worked cleanly with the existing JSON approach with zero repair loops. Only the code-bearing contract needs this change; don't fix what isn't broken.

5. **Re-run the Backend stage test** — same test case as the prior report (or a couple of new ones for variety), on both the cloud model and the local `qwen2.5-coder:1.5b`, and confirm:
   - No more schema-echo failures
   - No more escaping-related parse failures
   - The orchestrator correctly reconstructs the file(s) from the delimited output

6. **Note whether the underlying content/correctness gap (shallow stub code) is still present** — expected, since that's a separate, already-flagged issue (recommendation #2 in the prior report), not something this contract change is meant to fix. Just confirm it's unchanged/not made worse, don't try to solve it here.

## What NOT to do in this task

- Don't build the content/instruction-following correctness check yet (separate follow-on task, recommendation #2 from the prior report).
- Don't add the Frontend stage yet (separate follow-on task, recommendation #3).
- Don't start reshaping the training dataset yet — that happens right after this, once the contract format is confirmed stable (this task's output is what that reshaping will be based on).
- Don't touch the Planning/Design JSON schemas — they're working well as-is.

## Definition of done

- A defined delimited-text format for code-bearing outputs, documented (e.g., in the orchestrator's README or a short spec file)
- Updated parser + Backend stage prompt reflecting the new format
- A re-run test confirming the schema-echo and escaping failures no longer occur, on both cloud and local models
- A short report noting: did the fix work as expected? Any new friction found? Confirmation that the content-quality gap (shallow stub code) is unchanged, not solved, by this change.
