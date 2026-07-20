# Code-Bearing Handoff Contract: Delimited Text Format

**Why:** the JSON-schema `CodeOutput` contract (embedding a full source file as an escaped
JSON string value) caused real failures even outside any tool-calling protocol — models
(cloud and local) echoed the schema back verbatim, or used Python triple-quote syntax
instead of valid JSON escaping for multi-line content. See `doc/custom-orchestrator-report.md`.

Fix: code-bearing stages (Backend, Frontend) respond with **delimited plain text**, not JSON.
No escaping of newlines/quotes is ever required - the model writes code exactly as it would
in a normal code block.

## Format

```
---FILE: path/to/file.py---
<raw, unescaped code - exactly as it should appear in the file>
---END---

---FILE: path/to/other_file.py---
<raw, unescaped code>
---END---
```

Rules:
- One `---FILE: <path>---` / `---END---` block per file. Path is relative, forward slashes.
- Zero or more lines of arbitrary text between the markers - copied verbatim into the file,
  no unescaping needed.
- Multiple files: just repeat the block. No wrapping container, no commas, no JSON at all.
- No metadata beyond the path is required for this prototype (no create-vs-modify flag -
  every run currently targets a fresh generated/ directory, so "modify vs create" doesn't
  yet apply; add a metadata line inside the block, e.g. `---FILE: path (modify)---`, if/when
  the pipeline needs to distinguish that).
- Everything outside `---FILE:.../---END---` blocks (prose, notes, reasoning) is ignored by
  the parser - a model can think out loud before/after/between blocks without breaking parsing.

## Internal representation (unchanged)

The orchestrator still works with the same internal shape after parsing:
```json
{"stage": "backend", "spec_version": 1, "files": [{"path": "...", "content": "..."}]}
```
Only *how this is produced/parsed* changed - `stage` and `spec_version` are supplied by the
orchestrator itself (not the model) since they're pipeline metadata, not something the model
needs to restate. `code_output.schema.json` still documents/validates this internal shape;
it's just no longer what the model is asked to directly emit.

## What did NOT change

`LockedSpec`, `UserFlow`, `DesignTokens` remain plain JSON, per the model's own request/response
- Planning and Design stages proved reliable with a direct JSON contract (zero repair loops on
cloud). Only code-bearing outputs move to delimited text.
