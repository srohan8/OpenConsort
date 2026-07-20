# Kickoff Brief for Claude Code — Add Frontend Stage to Orchestrator

**Context:** Runs in parallel with the dataset-reshaping work happening in another session. Independent of it — this task only touches `orchestrator/`, not `data-prep/`. Reference `orchestrator/CONTRACT.md`, `orchestrator/orchestrator.py`, and `doc/custom-orchestrator-report.md` / `doc/delimited-contract-report.md` for the proven Backend-stage pattern this should follow.

## Goal of this task

Add a Frontend stage to the orchestrator, following the exact same proven pattern as the Backend stage: a code-bearing stage using the delimited-text contract (`---FILE: path---` / `---END---`), consuming `LockedSpec` + `DesignTokens` (+ optionally `UserFlow`, since Frontend needs to know navigation/screens, unlike Backend), and producing files via `run_code_stage`.

## Why this should be low-risk

`run_code_stage`, `extract_files`, and the delimited-text contract are already built, tested, and confirmed working on both cloud and local models (see `delimited-contract-report.md` — first-attempt success, no iteration needed). This task is primarily "write a new system prompt and a new call site," not new architecture.

## Steps

1. **Confirm what input the Frontend stage actually needs.** Unlike Backend (`LockedSpec` + `DesignTokens`), Frontend likely also needs `UserFlow` — it needs to know the screens/navigation to actually build routing and pages, not just the design tokens and feature list. Check `orchestrator/schemas/user_flow.schema.json` for its shape and include it in the Frontend prompt's input.

2. **Write `FRONTEND_SYSTEM`**, following the same structure as `BACKEND_SYSTEM` in `orchestrator.py`:
   - Same delimited-text format instructions (`---FILE: <path>---` / `---END---`)
   - Include a concrete example (same lesson as Backend: models need an example, and the example should use an obviously-fake placeholder name so the model doesn't copy it literally — Backend hit this exact issue, already documented in `delimited-contract-report.md` §2, fixed with a clearer placeholder token)
   - State the actual frontend stack from `LockedSpec.stack.frontend` (e.g. React + Vite, per the Phase 1 decision already locked in `architecture.md`) so the model knows what to generate, not a generic frontend
   - Instruct it to implement the actual screens/flow from `UserFlow`, not a placeholder/stub — same "implement the features, not just a stub" instruction that (per the last report) may have incidentally helped Backend's content quality

3. **Add a `frontend` stage entry** to `build_stage_llms()`, following the same pattern as `backend` (support both cloud and an Ollama-routed local model option via a flag, e.g. `--ollama-frontend`).

4. **Add the call site in `main()`** — after the Backend stage runs, call `run_code_stage` for `frontend`, passing `LockedSpec` + `DesignTokens` + `UserFlow` as the input, same pattern as Backend's call.

5. **Test on both cloud and local models**, same verification standard as before:
   - Confirm schema-valid, parseable output (via the real `extract_files` parser, not a stand-in)
   - Confirm files actually get written correctly to the `generated/` output directory
   - Spot-check whether the generated frontend code is at least structurally plausible (imports, component structure) — full correctness-checking is a separate follow-on task (see "What NOT to do" below), but note anything obviously broken

6. **Update `orchestrator/CONTRACT.md`** if anything about the contract needs clarifying for a second code-bearing stage (e.g., confirm nothing stage-specific needs to change — the format itself should already be stage-agnostic).

## What NOT to do in this task

- Don't build the content/instruction-following correctness check yet — still a separate, already-tracked follow-on (recommendation #2 from `custom-orchestrator-report.md`).
- Don't touch the dataset-reshaping work happening in the other session — that's `data-prep/`, this task is `orchestrator/` only.
- Don't try to wire the Backend and Frontend outputs together (e.g., actually connecting the frontend's API calls to the backend's real endpoints) — that's an integration/verification concern for later, not this task. Each stage still just needs to independently produce schema-valid, parseable output for now.
- Don't start any fine-tuning work — unrelated to this task.

## Definition of done

- `FRONTEND_SYSTEM` prompt added, following the Backend pattern
- Frontend stage wired into `build_stage_llms()` and `main()`
- Successful test run producing schema-valid, parseable frontend file(s) on both cloud and local models
- A short report: did it work on the first attempt like Backend did, or did it need iteration? Any new friction specific to frontend code generation (e.g., multi-file component structure, import paths between files)?
