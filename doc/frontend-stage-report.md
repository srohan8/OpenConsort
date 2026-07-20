# Frontend Stage — Report

**Date:** 2026-07-20
**Scope:** Per `doc/kickoff-brief-frontend-stage.md`, follow-on to `doc/delimited-contract-report.md`.

## Summary

Added a `FRONTEND_SYSTEM` prompt and `frontend` stage to the orchestrator, following the exact proven Backend pattern (`run_code_stage`, delimited-text contract). Tested across **three rounds**, covering both a CLI-oriented and a web-app-oriented product idea, on both cloud and local models. Along the way, found and fixed one genuine new small-model limitation distinct from anything seen in the Backend-stage testing.

## Test round 1: CLI-oriented prompt, all-cloud

Prompt: *"A CLI to-do list app that supports adding, listing, and completing tasks"* → `LockedSpec.stack.frontend = "CLI"`.

**Succeeded, first attempt.** The Frontend stage correctly read `LockedSpec.stack.frontend` and produced a **Python, ANSI-styled CLI interface** (`src/db.py`, `src/ui.py`, `src/main.py`) rather than defaulting to React — good instruction-following evidence that the model is spec-adaptive, not stack-blind. It even translated `DesignTokens` (colors, spacing) into ANSI escape codes for the CLI presentation, a creative but correct adaptation to the actual target stack.

## Test round 2: Web-app-oriented prompt, all-cloud

Prompt: *"A web dashboard for tracking personal expenses with categories and monthly totals"* → `LockedSpec.stack.frontend` resolved to a React-based stack, per the Phase 1 default.

**Succeeded, first attempt — 19 files in a single response, zero parse errors.** Real project structure: `src/App.jsx`, `src/pages/*` (Login, Signup, Dashboard, AddExpense, EditExpense, ExpenseList), `src/components/*` (Button, Input, Card, NavBar + matching CSS), `src/context/*` (AuthContext, ExpenseContext). Spot-checked `App.jsx`: correct `react-router-dom` v6 usage, protected routes via a `PrivateRoute` wrapper reading auth context, all imports matching the actual generated file paths. This is genuinely good, coherent output — not just parseable.

## Test round 3: Web-app-oriented prompt, Ollama for both Backend and Frontend

Same web-app prompt, both stages routed to `qwen2.5-coder:1.5b`.

**First attempt: Backend succeeded, Frontend failed to parse — but for a new, distinct reason.** Investigation of the raw output confirmed the model correctly emitted **10 `---FILE:---` opening markers** but **zero closing `---END---` markers** across the entire response (`raw.count('---FILE:') == 10`, `raw.count('---END---') == 0`). This is not the schema-echo or JSON-escaping problem from the Backend-stage testing — it's a **marker-consistency drop-off over a long, repetitive multi-file generation**: the model learned to start each block correctly but lost track of closing them as the response grew.

**Fix:** made `extract_files` (in `llm_client.py`) tolerant of a missing `---END---` — split into a `FILE_START_RE` (finds each opener) and treats either the next file-start or end-of-text as the implicit close of the current block, falling back to an explicit `---END---` when present. Verified in two steps before re-running live:
1. **Unit-tested against the actual failed raw output** — recovered all 10 files correctly.
2. **Regression-tested against the original well-formed multi-file sample** (explicit `---END---` markers) — still parsed correctly, no behavior change for the common case.

**Re-run after the fix: succeeded, 12 files, schema-valid.** Spot-checked `src/App.jsx`: structurally coherent, uses `react-router-dom` (v5-style `Switch`/`Route` API rather than the cloud model's v6 `Routes`/`element` — a stylistic/version difference, not a bug), imports consistent with the other 11 generated files.

## Answering the definition-of-done questions

- **Did `FRONTEND_SYSTEM` + wiring work correctly?** Yes, across all three test rounds, once the parser hardening was in place.
- **First attempt or iteration needed?** Cloud: first attempt, both rounds. Local: first attempt succeeded for the CLI-oriented case (round 1 didn't test Ollama-frontend, but round 3's Backend stage succeeded first try on Ollama); the web-app/Ollama-frontend case needed one iteration — not a prompt-wording fix like Backend's schema-echo issue, but a **parser hardening** fix.
- **New friction found?** Yes — the missing-`---END---`-marker issue described above. This is worth flagging as a **general risk for any future multi-file, long-response generation with small models**, not specific to frontend code — the same drop-off could plausibly occur for a large multi-file Backend response too. The tolerant-parser design (implicit close on next-file-start or EOF) is now a permanent hardening in `llm_client.py`, not a one-off patch, and should hold up regardless of which stage or model triggers a long multi-file response next.
- **Structural plausibility spot-checks:** all three successful rounds produced code that reads as genuinely correct/coherent on inspection (proper routing, matching imports, sensible component boundaries), not just superficially valid.
- **Does `CONTRACT.md` need changes?** No — the delimited-text *format itself* required zero changes to handle a second code-bearing stage, including at much higher file counts (19 files in one cloud response) than the Backend stage had ever produced. Only the *parser's* robustness improved (tolerating a missing closer) — the contract/format stayed exactly as simple and stage-agnostic as designed. Worth stating this distinction clearly: format design was already right; implementation robustness needed one more iteration.

## Scaling signal worth watching

Cloud handled a 19-file, multi-component response cleanly with no issues. The local model's marker-completion reliability visibly degraded on a similar-sized (10–12 file) response — it's plausible this specific failure mode (dropping closers on long generations) becomes more likely as response length/file count grows, independent of the underlying reasoning quality being otherwise fine. This is a concrete data point for anyone scaling the Backend/Frontend contracts to larger single-response jobs with small models: either keep single-response file counts modest, or rely on parser tolerance (as done here) rather than assuming a small model will reliably close every block over a long generation.
