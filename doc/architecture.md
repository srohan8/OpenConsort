# Democratized AI Coding on a Normal PC — Working Document

*Last updated: 2026-07-18*

## Goal

Democratize AI-assisted software development so it runs on a normal consumer PC — no GPU required, modest RAM footprint — using small, specialized local models instead of one large general-purpose model.

---

## Core Concept

Instead of training one large LLM to know everything (like cramming a tutorial's worth of facts into weights), build a system of **small, specialized models**, each strong at a narrow job, coordinated through **stable, versioned contracts** rather than live inference-based mediation. This mirrors how real software teams work: agree on the contract once, build in parallel against it, integrate at the end.

---

## Architecture Overview

```
User (voice/text) 
      ↓
[Planning / Requirements Model]  ← asks narrowing questions, produces spec
      ↓
   Locked Spec (contract) — includes chosen language/framework combo
      ↓
   ┌─────────────────────┐
   │  Backend Specialist  │  (e.g., Python + FastAPI)
   └─────────────────────┘
   ┌─────────────────────┐
   │ Frontend Specialist  │  (e.g., React + Vite)
   └─────────────────────┘
      ↓
   Connector Artifact (OpenAPI-style contract, generated at planning time)
      ↓
   Integration / Verification pass (schema validation, not live mediation)
```

### Key principle
The "connector" is **not a live model in the runtime path**. It's a static, versioned schema/contract generated once during planning. Both specialist models build against it independently — no per-exchange round-trip, no compounding latency.

---

## Orchestration Strategy: Build on MetaGPT, Not From Scratch *(SUPERSEDED — see Open Risks section: decision reversed 2026-07-20 to a custom orchestrator after the patch trial; this section kept as history/rationale for why MetaGPT was tried first)*

**Decision: start by cloning and building on top of MetaGPT rather than writing an orchestrator from scratch.**

**What MetaGPT is:** `github.com/FoundationAgents/MetaGPT` (old `geekan/MetaGPT` URL redirects here). MIT licensed, free for commercial use and modification. A Python framework (`pip install metagpt`) that takes a one-line requirement and routes it through role-based agents (Product Manager, Architect, Project Manager, Engineer) following a structured SOP, outputting user stories, requirements docs, data structures, APIs, and code. Configurable against OpenAI, Azure, **or Ollama** as the LLM backend — meaning it can be pointed at local models instead of a cloud API.

**Why reuse rather than build from scratch:**
- Orchestration (agent handoffs, SOP sequencing, role structure) is undifferentiated work — not where this project's actual value is. The value is in the small-model specialization and low-resource local-first design.
- The LLM-backend swap point is clean: MetaGPT already abstracts "which model answers this role's calls" via config, so routing each role to a fine-tuned SLM (via Ollama) instead of GPT-4 is a config/adapter change, not a framework rewrite.
- Gets a working end-to-end pipeline fast (even with a placeholder cloud model first), letting the pipeline *shape* get validated before months are spent training specialists.

**What needs to be added on top (real work, not free):**
1. Clone MetaGPT, run a baseline project with a cloud model first to learn its role/SOP structure firsthand.
2. Add a **new Design role** — doesn't exist in MetaGPT today (its roles are PM/Architect/PM/Engineer, not Designer). See "Design Role — Build vs. Reuse" below for what to use here.
3. Point each role's LLM config at locally-served fine-tuned models (via Ollama) once trained.
4. Likely need to adjust MetaGPT's default prompts/SOPs per role to match the narrower input/output format each fine-tuned specialist expects.
5. Add the strict contract/schema layer (API contract, design tokens) as structured hand-offs between roles — MetaGPT's default hand-offs are more document-based (markdown specs) than strict schema-validated JSON; this is likely the biggest customization needed.

**Validation plan before fully committing:** attempt the Ollama-swap on a single role first (e.g., just the Engineer role) as a small proof-of-concept, to find out early whether MetaGPT bends toward the small-model/low-latency/strict-contract design goals, or whether its assumptions (built around larger cloud-shaped LLM calls) fight against the low-RAM local-first target enough to justify a lighter custom orchestrator instead.

**Gap confirmed: MetaGPT does not interactively ask the user clarifying questions.** It takes a one-line requirement and the Product Manager agent writes the PRD itself — inferring details and filling gaps autonomously, without pausing to ask the human user anything. Its "Anything UNCLEAR" step is an agent checking its own draft for ambiguity and clarifying it internally (agent reasoning about its own output, or agent-to-agent), not a turn back to the human. The framework is explicitly designed to minimize back-and-forth, including with the user — agents pull from a shared information pool rather than asking and waiting for replies. This conflicts directly with this project's core premise: a real upfront requirements interview (narrowing questions, waiting for the user's actual answers) is the highest-leverage piece of the whole system, and it's not something MetaGPT does today.

**Required customization: a real two-tier requirements-interview process, not MetaGPT's current one-shot PM inference.**

1. **Tier 1 — Upfront, before the coding stack is decided.** Before any language/framework/design combo is locked, the requirements model interviews the user with plain-language narrowing questions (product type, core features, scope, style preferences, etc.), waits for actual answers, and only then produces the locked spec — including the stack and vertical choices covered elsewhere in this document. This replaces MetaGPT's current one-line-prompt-to-PRD behavior for the PM role.
2. **Tier 2 — Mid-development, smaller-scope version of the same process.** When the user wants to change or add something while specialists are already building (e.g., "actually, add social login" or "change the layout to X"), the system runs a **lighter version of the same interview process** — narrowing questions scoped only to the change being requested, not a full re-interview — before updating the spec. This produces a **new versioned spec/contract bump** (consistent with the "new cycle, not a live patch" principle already established for scope changes), rather than silently mutating the running build or having a specialist guess at the new intent.

**Implication for the pipeline:** the Planning/Requirements role needs two modes — a full upfront interview mode, and a lightweight delta-interview mode triggered by mid-build change requests — both producing the same kind of locked, versioned contract output that downstream specialists consume. This is a meaningful build item on top of MetaGPT's default PM role, not a minor prompt tweak.

**Refinements to the two-tier process (decided, to implement alongside the above):**

1. **Triage step needed before routing to full-interview vs. delta-interview.** A mid-build request isn't always clearly one or the other — "add a contact form" is obviously a delta, but "make this a marketplace instead of a portfolio" is a full re-plan (new vertical, likely new design specialist, possibly new stack), and there's a real gray zone in between (e.g., "add user accounts and a dashboard"). The planning model itself should classify which mode a mid-build request needs, rather than assuming the user will self-classify correctly.

2. **Delta requests must define what existing work gets regenerated vs. kept.** If a delta changes something specialists already built against (e.g., the design system, or an API shape), the process needs to explicitly resolve what's invalidated and must be redone versus what's still valid — otherwise "smaller process" quietly becomes "regenerate everything anyway" and the intended savings disappear.

3. **Delta interviews should be scoped to the diff, not a full re-run.** The delta process only needs the specific change plus a reference to the current locked spec version — not re-asking the full original set of upfront questions. "Smaller" means smaller in scope of *what's asked*, not just fewer total back-and-forth turns.

4. **Every change (delta or full re-plan) must be explained back to the user in plain, user-flow terms before it's confirmed and applied** — not as a technical diff, but as what actually changes for someone using the resulting app. Base the explanation on the user flow / screens affected, not internal spec fields. Example pattern: *"With this change, a user signing up will now go through 3 screens (enter email → verify → set password) instead of 2 (enter email → set password). Confirm this is what you want?"* This applies to both the full-interview and delta-interview paths — the user always sees a concrete before/after of their actual experience, in plain language, and must confirm before the new spec version is locked and specialists proceed.

## User Flow — A Distinct, User-Facing Artifact

The user flow (sequence of steps/screens a person goes through in the resulting app — e.g., sign up → verify → dashboard, or browse → cart → checkout → confirmation) is a **Planning/Requirements-model output**, not a Design-model output. It's about behavior and sequence ("what happens and in what order"), not visual appearance ("what it looks like") — so it's produced during the requirements interview, before the Design role runs.

**Decision: the user flow is a distinct, explicitly named, versioned artifact — not buried inside the locked spec document.**

**Updated pipeline placement:**
```
Planning/Requirements Model
      ↓
   Locked Spec — includes product type, language/framework combo, features/scope
      ↓
   USER FLOW (steps/screens, navigation logic) ← distinct artifact, versioned
      ↓
   ┌──────────────────────┐
   │   Design Model         │ → consumes the user flow; designs the actual
   └──────────────────────┘    screens/visuals for each step in it (tokens, layout, components)
      ↓
   ┌─────────────────────┐        ┌──────────────────────┐
   │  Backend Specialist   │        │  Frontend Specialist  │ ← consumes user flow (navigation/
   └─────────────────────┘        └──────────────────────┘    routing logic) + design tokens
```

**Why a distinct artifact, not a section of the spec:**
- Makes it possible to diff between versions (old flow vs. new flow) cleanly — required for the plain-language "3 screens instead of 2" confirmation pattern already decided above.
- Design model, frontend specialist, and backend specialist all consume it directly as a defined input, rather than each parsing it out of a larger spec document.

**Elevated role: the user flow is a primary, user-facing, interactive artifact — not just an internal pipeline document.**
- **Every change the platform user makes has a traceable impact on the user flow.** This is treated as close to universally true — feature additions/removals, screen changes, navigation changes all route through an update to this artifact, which is what then triggers the plain-language confirmation step ("this now takes 3 steps instead of 2").
- **The user flow should be presented as an interactive, visual map** the platform user can actually see and explore — not just referenced abstractly in a confirmation prompt. Think an interactive flow/node diagram (screens as nodes, transitions as connections) that updates as the app evolves, rather than a static text description.
- This makes the user flow function as the platform user's primary mental model of "what am I building" — likely the single most important artifact to show them directly, more so than the design tokens or the API contract, since it's the one expressed in terms of their own app's behavior rather than technical implementation.

**Open question to resolve:** exact visual/interaction format for this map (e.g., a simple directed graph the user can click into per-screen, vs. a linear step list, vs. something closer to a sitemap) — worth prototyping a few formats against real example flows before committing to one.

## Testing Log

Running record of what's been tried and the outcome, starting with the planned MetaGPT single-role trial. Update after every real test — this document should reflect validated findings, not just design intentions, once testing begins.

| Date | What was tested | Result | What worked | What didn't / open issue |
|---|---|---|---|---|
| 2026-07-20 | Training data prep track (Claude Code, parallel to MetaGPT trial) — task categories, task→code pairs, eval suite, Colab notebook | Completed. 13 researched FastAPI categories; 71 executed-and-verified backend task→code pairs (0 failed in final run); 31-task independent eval suite (runner validated against both a correct reference solution and a deliberately-wrong implementation); working LoRA/QLoRA Colab notebook, dummy-data-runnable | Verification was real, not eyeballed — each pair executed in an isolated module and driven with `TestClient` asserting status/shape/headers/side-effects. Caught genuine bugs during iteration (bcrypt≥4.1/passlib breakage, Pydantic model-rebuild issues, missing email-validator). Eval suite independence actually tested, not just asserted. File formats matched spec (JSONL for data files, `.ipynb` for notebook, `.md` for category doc). | Two open gaps flagged — see Open Risks below (DB pairs use in-memory SQLite, not the locked PostgreSQL stack; `task` field format needs reshaping once MetaGPT trial locks the contract shape). Not yet independently spot-checked by a human — recommended before fully trusting the "0 failed" claim. |
| 2026-07-20 | MetaGPT single-role Ollama swap trial (Claude Code) | Completed — swap did NOT work as originally scoped, but root cause fully diagnosed. Real architecture mismatch found: main-branch MetaGPT runs a TeamLeader/RoleZero single-agent system, not the assumed PM→Architect→PM→Engineer pipeline; code-writing role is `Engineer2`. Confirmed no clarifying questions asked (as expected). Handoffs are loose ReAct-style JSON tool-calls embedded in free text, not clean docs or strict schema. | Ollama itself confirmed working standalone (served `qwen2.5-coder:1.5b` correctly). Root cause precisely traced: `config2.yaml`'s per-role `roles:` override is dead code — never read by `context.py`/`role.py` to construct a per-role LLM instance. | Real friction found: typer/click version conflict, Windows console-encoding crash, and a serious silent-failure bug (agent's Terminal tool ran a Unix `pwd` command that broke on Windows, silently preventing a file write while the agent reported success). See Open Risks below — decision on MetaGPT reopened, not settled. |
| 2026-07-20 | First real LoRA/QLoRA training run on the 71-pair FastAPI dataset (Qwen2.5-Coder-1.5B, 3 epochs, Colab) | **Success — first genuine end-to-end validation of the training pipeline.** Loss dropped healthily from ~0.87 to ~0.07-0.13 over 54 steps (3 epochs). Inference sanity check produced correct, clean FastAPI code for a held-out prompt ("Create a FastAPI GET /health endpoint") — correct imports, decorator, and return value, no repetition or garbage. | Confirms three things at once: label-masking fix works (model generates code, not memorized prompt text); the small 71-example dataset is enough to teach a recognizable, correct pattern; a real bug was found and fixed along the way (see next column) rather than silently producing bad results. | Root cause of an earlier "garbage output" run (repeating digits) was diagnosed and fixed: `prepare_model_for_kbit_training()` enables gradient checkpointing by default, which silently forces `use_cache=False` during generation, breaking KV caching. Fix: call `model.gradient_checkpointing_disable()` + `model.eval()` before generating — now baked into the notebook. This result is on the SQLite/provisional-task-format version of the dataset — still needs the Postgres verification lane and task-field reshaping (per earlier entries) before this counts as the real Phase 1 specialist. |
| 2026-07-20 | Custom orchestrator prototype (Planning→Design→Backend, simple direct contracts, no tool-calling protocol) built and tested with both cloud and local (`qwen2.5-coder:1.5b`) models, per `doc/kickoff-brief-custom-orchestrator.md`. Full report: `doc/custom-orchestrator-report.md`. | **Core hypothesis confirmed, with an honest caveat.** Planning/Design stages worked cleanly on cloud with zero repair loops (vs. MetaGPT's frequent repair cycles). Backend stage on the local model needed 2 rounds of prompt iteration (schema-echo, then JSON-escaping of multi-line code) but ultimately produced schema-valid, protocol-compliant output — no crash, unlike MetaGPT's `KeyError: 'command_name'` failure. Final generated code was structurally valid and stack-consistent but functionally shallow (a stub, didn't implement the 3 requested features). | Confirms the core hypothesis from the MetaGPT patch trial: small models fail on strict tool-call protocols, not on simple direct task→JSON contracts. 4 JSON schemas defined and workable. Found and fixed: an OmniRoute multi-provider round-robin causing intermittent 404s (retry/backoff), a Windows unicode file-write bug (same class as MetaGPT's, far cheaper to fix here), a logging-order bug hiding validation failures, and a missing-parent-directory file-write bug. | Code-bearing contracts that embed multi-line source as an escaped JSON string are a real friction point for small models (and arguably any model) — recommended fix is a delimited-text contract instead of JSON-embedded code, not further prompt patching. Content/instruction-following (did it implement the actual features) is a separate, still-open gap from schema/protocol compliance — schema validation alone doesn't catch a shallow-but-valid response. |

| 2026-07-20 | MetaGPT per-role LLM wiring patch trial (Claude Code, bounded timebox) | Completed — patch worked (routing confirmed real, two independent ways), but the pipeline still failed for a deeper reason: RoleZero's strict `{"command_name": ...}` tool-call protocol vs. the small model's natural prose+code response. Run crashed (`KeyError: 'command_name'`). **Decision made: pivot to a custom orchestrator** (see Open Risks below). | Patch was cheap (~15 lines, 1 file) and verified genuinely working via `OllamaLLM` instance check + independent `ollama ps` system check. The generated code itself (read in isolation) was correct — confirms small models can code, the blocker is protocol rigidity, not coding ability. | MetaGPT's RoleZero tool-calling contract is built for GPT-4-class models and isn't forgiving of a small model's natural response format; repair-retry logic made it worse, not better. This is exactly the "narrow, forgiving contract" problem the architecture doc anticipated — confirms the custom-orchestrator pivot rather than continuing to adapt MetaGPT. |
| 2026-07-20 | Delimited-text contract redesign for code-bearing stages (`---FILE:---`/`---END---`, replacing JSON-embedded escaped code), per `doc/kickoff-brief-delimited-contract.md`. Full report: `doc/delimited-contract-report.md`, format spec: `orchestrator/CONTRACT.md`. | **Clean success, first attempt, on both cloud and local models** — a real improvement over the JSON-contract version, which took 2 rounds of prompt-fixing for the local model. No schema-echo, no escaping failures (nothing to escape in this format). Local model's generated code this run also implemented all 3 requested features (not just a stub) — encouraging, but not claimed as the content-quality gap being solved (still separately tracked). | Confirms the prior report's hypothesis: removing JSON-string-escaping requirements for code content removes a real failure mode, with a *simpler* parser (one regex) than the JSON-schema approach it replaced. One minor, cheaply-fixed cosmetic issue: model copied a literal placeholder path (`path/to/file.py`) from the prompt's format description instead of choosing a real filename. | Content/instruction-following correctness (does the code actually implement the spec) remains a separate, still-open concern from contract/schema compliance — one good run isn't sufficient evidence to consider it solved. Next: add Frontend stage using the same proven pattern; begin reshaping `data-prep/fastapi-backend-pairs.jsonl` against this now-stable contract format. |
| 2026-07-20 | Frontend stage added to orchestrator (same `run_code_stage`/delimited-text pattern as Backend), tested across 3 rounds (CLI-oriented cloud, web-app-oriented cloud, web-app-oriented Ollama for both stages), per `doc/kickoff-brief-frontend-stage.md`. Full report: `doc/frontend-stage-report.md`. | **Succeeded in all 3 rounds, after one parser-hardening fix.** CLI-oriented prompt: cloud correctly produced a Python/ANSI-styled CLI frontend (spec-adaptive, not React-blind). Web-app prompt on cloud: first-attempt success, 19 files, genuine coherent React Router app (protected routes, context providers, consistent cross-file imports). Web-app prompt on Ollama (both stages local): Backend succeeded first try; Frontend initially failed — model emitted 10 `---FILE:---` openers but 0 `---END---` closers across the long multi-file response. Fixed by making `extract_files` tolerant of a missing closer (next-file-start or EOF as implicit end); verified against both the failed raw output and the original well-formed case before re-running live, then succeeded with 12 files. | `CONTRACT.md`'s delimited-text *format* needed zero changes for a second code-bearing stage, even at much higher file counts (19 files) than Backend had ever produced — strong evidence the format is genuinely stage-agnostic and scales. The new failure mode (marker-consistency drop-off on long generations) is distinct from anything found in Backend testing (not schema-echo, not escaping) — a small-model reliability issue tied to response length, not stage type. | The tolerant-parser fix is now a permanent hardening, not a one-off patch — likely relevant to any future long, multi-file single-response generation regardless of stage or model. Cloud handled 19 files cleanly; local model's marker-completion reliability visibly degraded around 10-12 files — worth watching as a scaling limit if larger single-response jobs are asked of small models later. |

| 2026-07-20 | Dataset reshaped to v3 (mirrors real orchestrator prompt exactly — `system_prompt`=`BACKEND_SYSTEM` imported from `orchestrator.py`, `user_prompt`=identical f-string to `orchestrator.py:211`, sourced from ground truth, not guessed), then a full LoRA/QLoRA retrain on the real 71-pair v3 dataset (Qwen2.5-Coder-1.5B, 3 epochs) and tested against a genuinely held-out `LockedSpec`/`DesignTokens` pair (health-check feature, not in training data). | **Milestone: first fully validated, contract-faithful Phase 1 Backend specialist result.** Training: 54 steps, loss 0.81→~0.06-0.14, matching the healthy shape of the earlier proof-of-concept run. Inference on the held-out spec produced a perfectly-formed `---FILE: main.py---...---END---` block: correct imports, correct route, and even added `status_code=status.HTTP_200_OK` explicitly (better than a bare-minimum answer). No schema-echo, no escaping issues, no marker-consistency drift. | Confirms the full chain end-to-end: real orchestrator contract → byte-verified contract-faithful training data → correctly-trained model → correct behavior on genuinely unseen input. Two real bugs hit and fixed along the way during Colab iteration (both process, not data, issues): (1) training initially ran on only 3 dummy pairs because the dataset cell wasn't re-run after the real file was uploaded — fixed by re-running from the dataset-load cell forward; (2) the inference test cell still used the old `### Task:` prompt template after the reshape — fixed to build the real `BACKEND_SYSTEM` + `LockedSpec`/`DesignTokens` + `### Response:` format. | This result still inherits the three previously-flagged dataset limitations (SQLite vs. locked PostgreSQL stack; `design_tokens` constant across all 71 rows; `features` single-item per row) — per the "let evaluation drive iteration" principle, these are deliberately NOT being fixed speculatively. Next: score this adapter against the full 31-task eval suite (v3) to get real signal on whether these limitations actually matter, before deciding whether to augment the dataset further. |

---

## Open Risks — Status Notes

**Triage step (delta vs. full re-plan):** Partially addressed, not resolved. A dependency-graph/static-analysis tool (not the LLM) should determine which files/contracts are actually touched by a proposed change — this removes blind guessing about technical impact and gives the planning model concrete, verifiable input (see "User asks for a change — file impact" discussion). But the *threshold judgment* — how much technical impact counts as a delta versus requiring a full re-plan — is still a real decision the planning model has to make, and still needs testing against messy, ambiguous real requests before it can be trusted. Tool-assisted, not tool-solved.

**Decision: defer building the delta path for now.** The delta-vs-full-replan threshold can't be well-designed from a whiteboard — it needs real messy examples to calibrate. Until then:
- Mid-build changes always go through the full requirements-interview path (Tier 1 style), even for small requests. This is safe-by-default (slower, but correct) rather than a fast-but-risky shortcut that might quietly produce a broken app.
- **Scope limit on this fallback:** reusing the full-interview *mechanism* applies to feature/scope clarification only — it must NOT re-ask product type or re-trigger stack/language/framework selection, since those are locked at project start and aren't part of a mid-build change.
- Every mid-build change gets logged (see Testing Log) with: what was asked, what a dependency-graph tool showed as affected, and whether the full re-plan was proportionate or excessive in hindsight — building the real calibration data needed to design the eventual delta mechanism from evidence, not guesswork.

**Candidate tool for the eventual dependency-graph/impact-analysis step: [Graphify](https://github.com/Graphify-Labs/graphify)** (MIT licensed, 91.8k stars). Parses a codebase locally via tree-sitter AST — no LLM call needed for code, nothing leaves the machine, ~40 languages supported — into a real queryable knowledge graph (not a vector index). Every edge tagged `EXTRACTED` (explicit in source) or `INFERRED` (resolved by graphify). Directly relevant commands: `graphify explain "<concept>"` (all connections to a concept), `graphify path "A" "B"` (trace connection between two things), `graphify query "<question>"` (scoped subgraph for a plain-language question) — close to exactly the "given a proposed change, what's actually affected" capability the deferred triage mechanism needs. Also integrates with 20+ AI assistants including Hermes (already in use for NOOK). Caveat: it's a developer-facing CLI tool, so using it here means repurposing its graph-building/query engine as a backend service for the pipeline's impact-analysis step, not using its CLI UX directly with end users — real integration work, not drop-in. Worth evaluating when the deferred delta mechanism is revisited.

**Per-vertical/per-stack model proliferation:** Concern is substantially reduced by a deliberate product decision — the platform recommends the stack based on product type rather than letting users pick freely, so the number of combos (N) is controlled directly rather than growing to cover arbitrary permutations. Start with a small, curated set (e.g., one combo initially, expanding only to cover the main product-type buckets already identified). The operational-tax concern would resurface only if stack choice is later exposed directly to users — treat that as a deliberate future decision, not something to drift into.

**End-to-end validation:** Partially achieved. The first real LoRA/QLoRA training run (see Testing Log, 2026-07-20) is the first genuine end-to-end validation of a piece of the pipeline — training worked, and a fixed generation bug produced correct FastAPI output. The MetaGPT orchestration piece, however, is now a reopened decision (see below), so "end-to-end" for the full multi-agent pipeline is still not validated.

**MetaGPT orchestration decision — RESOLVED: pivot to a lighter, custom orchestrator (2026-07-20).**

Full history: the single-role Ollama swap trial found a real architecture mismatch (main-branch MetaGPT runs TeamLeader/RoleZero, not the assumed PM→Architect→PM→Engineer pipeline; code role is `Engineer2`), loose ReAct-style handoffs instead of clean contracts, and a serious Windows-specific silent-failure bug. A follow-on bounded patch trial then tested whether the per-role LLM routing gap (`config2.yaml`'s dead `roles:` override) was fixable:

- **The patch itself was cheap and verified genuinely working** — ~15 lines changed in one file (`metagpt/software_company.py`), no framework internals touched. Verified two independent ways: unit-level (`Engineer2(config=...).llm` was a real `OllamaLLM` instance) and system-level (`ollama ps` showed `qwen2.5-coder:1.5b` loaded and active mid-run, outside MetaGPT's own self-reporting).
- **But the pipeline still failed, for a deeper reason:** the small local model answered the coding request with normal prose + a code block (a reasonable answer to "write a to-do app") instead of RoleZero's required strict `{"command_name": "Engineer2.write_new_code", ...}` JSON tool-call format. MetaGPT's repair-retry mechanism then confused the model further, and the run crashed (`KeyError: 'command_name'`) — no file was ever written.
- **Critically, the code itself (read in isolation) was correct and reasonable.** This is not "small models can't code" — it's "small models can't reliably navigate a rigid, GPT-4-class tool-calling protocol they weren't designed around." This is exactly the "small models need narrow, forgiving contracts" problem this architecture was already built to avoid (see Design Specialist, User Flow, and Combo sections' emphasis on simple, structured task→code contracts rather than open-ended tool-calling).

**Decision: build a lighter, purpose-built orchestrator instead of continuing to force local specialists through MetaGPT's RoleZero protocol.** The project's actual pipeline (Planning → Design → Backend → Frontend, each consuming a simple, structured contract) is narrower in scope than MetaGPT's general software-company simulation, and a custom orchestrator handing each specialist a direct task→code contract (rather than requiring strict multi-field tool-call JSON) is expected to be less total work than continuing to adapt MetaGPT or fine-tune every specialist to nail its protocol. MetaGPT remains useful as a reference for *ideas* (SOP structuring, role separation) but is no longer the implementation base.

**Next step:** sketch/prototype the minimal custom orchestrator needed for the Phase 1 case specifically, per `kickoff-brief-custom-orchestrator.md`.



**Training data — PostgreSQL verification gap (found 2026-07-20):** The 71 verified FastAPI task→code pairs use in-memory SQLite for DB-related tasks — executable and API-compatible, but not the locked Phase 1 stack (PostgreSQL). Before scaling the dataset up or using it for real training, add a Postgres verification lane so DB pairs are confirmed against the actual production database, not just a compatible substitute.

**Training data — contract-format dependency (found 2026-07-20):** The `task` field format in the training pairs/eval suite is provisional. It should be reshaped to mirror the actual planning-model → specialist-model handoff contract once the MetaGPT trial locks that format (markdown spec vs. structured JSON, exact schema) — now more uncertain given the trial found handoffs are loose ReAct-style JSON-in-free-text, not a clean schema. This reshaping step is on hold pending the reopened MetaGPT decision above.

**First real training run — SQLite/provisional-format caveat (found 2026-07-20):** The successful LoRA training run (see Testing Log) used the current 71-pair dataset as-is — meaning it inherits both gaps above. This run validates the *training pipeline mechanics* (masking, gradient-checkpointing fix, LoRA setup), not a finished, production-ready specialist. Retraining is expected once the Postgres lane and task-field reshaping are resolved.

**Decision: Phase 1 / first combo = Web app (SaaS-style / dashboard).**



This confirms as an official decision what has been the implicit default throughout this document (base-model discussion, training pipeline example, and the combo table's own build-order reading).

**Why web app is the right phase 1 choice:**
- Highest demand bucket per the table above — the most common "I want to build an app" request across tutorials, bootcamps, and indie builders, higher than portfolio, e-commerce, or blog.
- Simplest stack of the options — no payments module required (optional, not mandatory for this vertical), simpler auth (JWT, no complex role hierarchy), no SEO/SSR complexity that e-commerce/blog need.
- Clean proving ground for every other open piece — the design specialist, the user flow artifact, the requirements interview, MetaGPT integration, and the Graphify dependency-graph tooling all need one full working example to validate against. A web app is the simplest case that still exercises all of them (real backend, real frontend, real user flow, real design system) without e-commerce's payment complexity or mobile's native tooling on top.

**What Phase 1 locks in concretely:**
- Backend specialist: **FastAPI**
- Frontend specialist: **React + Vite**
- Database: **PostgreSQL**
- Auth: **JWT-based**
- Payments: **not included in Phase 1** (optional for this vertical anyway, and deferred per the shared Payments Module open item above)
- Design specialist: **SaaS/dashboard-oriented design system** — not portfolio's expressive style or e-commerce's conversion-focused style

---

## Design Role — Build vs. Reuse

Rather than training a design-system specialist model from scratch immediately, existing open-source "design skill" kits can serve as the **prompt/knowledge layer** for the Design role inside the MetaGPT-based orchestration — running on a fine-tuned SLM, but not requiring a from-scratch dataset/fine-tune to get started.

| Project | What it does | Relevance |
|---|---|---|
| **`plugin87/ux-ui-agent-skills`** | Structured instruction/knowledge kit producing DTCG-format design tokens (colors, typography, spacing, shadows, borders, breakpoints, motion) in a 3-tier architecture (Primitive → Semantic → Component); designs components Atom-to-Template (Atomic Design) with variants, states, token mapping, accessibility specs; "Adapter Protocol" targets React+Tailwind, Next.js, Vue, Svelte, React Native, and more. Pure instruction/knowledge layer — no runtime or dependencies. | **Most directly usable** — already outputs in a contract form the frontend specialist could consume, matching the Design role's intended job. |
| **`voltagent/awesome-design-md`** | Curated collection of "DESIGN.md" files — plain-text design system docs extracted from real sites (Stripe, Vercel, Notion, Linear, etc.), a concept introduced by Google Stitch. Drop one in and an agent builds UI matching that visual language. | Reference dataset — useful as seed examples for training a design specialist later, and as inspiration for token output format. |
| **`nextlevelbuilder/ui-ux-pro-max-skill`** | Fully open source; covers 84 UI styles and 192 product types with stack-specific guidelines across 22 frameworks; generates tailored UI rules/patterns/logic via CLI. | Notably already organizes by **product type** — lines up directly with the vertical-forking approach (portfolio vs. e-commerce vs. SaaS) planned for the Design role. |
| **Anti-AI-slop design linter** (offline, deterministic, 152 rules/160 brand specs, never calls an LLM) | Catches generic/undifferentiated "AI-generated UI" output after generation. | Useful as a **verification** layer paired with the Design role, not a replacement — catches drift after the fact, same role as the planned Integration/Verification pass for the API contract. |

**Revised build plan for Design role:** use `ux-ui-agent-skills` (or similar) as the initial prompt/knowledge layer for the Design role running on the chosen SLM, rather than building a design dataset and fine-tuning from zero. Layer project-specific/vertical-specific fine-tuning on top later only if the generic version proves insufficiently distinctive per vertical.

---

## Prior Art / Related Projects

Existing work validating (and partially covering) pieces of this architecture:

- **MetaGPT** (see Orchestration Strategy above) — role-based multi-agent software company simulation; closest structural match to the planning→design→backend→frontend pipeline.
- **AgenticDev** — Python framework orchestrating 4 LLM agents (architect, developer, tester, etc.) using an "Agent as Tool" pattern; architect produces a technical spec before implementation, similar to the "lock the contract" approach here.
- **"Small Language Models are the Future of Agentic AI"** (NVIDIA-affiliated paper) — argues SLMs are well-suited for routine code generation, boilerplate tasks, and structured responses based on predefined templates; directly supports the core thesis of this project.
- **MATS** (Multi-agent Text2SQL framework) — uses specialized agent roles specifically to compensate for small models' weaker generalization, with RL aligned to execution feedback; different domain, same underlying logic (specialize narrowly to make small models competitive with large ones).

**Notable gaps found (i.e., where this project isn't just replicating existing work):**
- No existing project combining tiny-model-per-language/framework specialization with a strict no-GPU, 8–16GB RAM target — most local-coding-agent writeups assume a beefy Mac (unified memory) or a discrete GPU.
- No dedicated design-system specialist *model* found in the multi-agent frameworks reviewed (MetaGPT/AgenticDev have Architect/Engineer roles but no trained Designer role) — though the design-skill-kit projects above (ux-ui-agent-skills etc.) partially fill this gap as a prompt-layer solution.
- No existing project forking a design/UI model specifically by **product vertical** (portfolio vs. e-commerce vs. SaaS) — existing frameworks fork by *role* (PM, architect, engineer, QA), not by *product type*, though `ui-ux-pro-max-skill`'s product-type organization is a partial precedent.

---

## Training Infrastructure & Pipeline

**Training approach:** Fine-tune existing small open base models (e.g., Qwen2.5-Coder 1.5B/3B, MiniCPM5-1B) via **LoRA/QLoRA** rather than full fine-tuning or training from scratch. Freezes the base model, trains small adapter layers — far cheaper compute-wise, and produces a small (tens of MB) adapter file rather than a full new model.

**Training compute: Google Colab Pro (~$10/month)** — decided as feasible.
- Free tier (T4 GPU) works for early experimentation but has usage limits and can disconnect mid-session.
- Pro tier chosen for real iterative training runs — longer runtimes, priority GPU access, fewer disconnects.
- CPU-only training (e.g., on the ThinkCentre or any non-GPU normal PC) is not practical — training needs forward *and* backward passes and is dramatically slower on CPU (days–weeks vs. hours). This is a training-time-only constraint; it does not affect the "runs on a normal PC" goal for end users, since only *inference* needs to run locally — the LoRA adapter produced by Colab training gets downloaded and run locally on CPU.

**Standard stack:** Hugging Face `transformers` + `peft` (LoRA) + `bitsandbytes` (4-bit quantization for QLoRA). Well-documented Colab notebook templates exist for this exact workflow.

**Pipeline steps:**
1. Pick a base model per specialist (backend, frontend)
2. Build a narrow, curated task→code dataset (quality/consistency matters more than volume — a few thousand clean examples beats a large noisy scrape)
3. LoRA/QLoRA fine-tune on Colab (rough estimate: 1–3 hours for a few thousand examples on a 1–3B model)
4. Download the resulting adapter; run locally (base model + adapter) for inference/testing
5. Build an evaluation suite (~20–50 realistic held-out tasks) and actually **execute** generated code against it — not just eyeball it — to measure real quality
6. Iterate primarily on **dataset quality**, not hyperparameters, based on where evaluation shows failures

**Note on architecture fit:** one shared base model + multiple small LoRA adapters (one per language/framework specialty) is likely a better fit than fully separate model files per specialist — lighter on RAM, avoids model-swap overhead, and matches the LoRA training approach above.

---

## Design Specialist

A dedicated **design model**, separate from the frontend-code specialist, is responsible for defining the design system (visual language) before any component code is written — mirroring how a designer/design-system owner works ahead of engineers on a real team.

**Why this needs its own model, not a frontend responsibility:**
- Different skill entirely — frontend-code is about *implementing* components correctly (state, props, hooks, structure); design system work is about *deciding* the visual language (color palette, typography scale, spacing system, component variants, accessibility contrast) before any component exists.
- Runs earlier in the pipeline, not alongside frontend — the frontend specialist should *consume* the design system as a contract, the same way it consumes the API contract from the connector.
- Prevents generic, undifferentiated "AI-generated UI" — without a dedicated design pass, output risks inconsistent spacing, arbitrary color choices, no coherent visual identity project-to-project.

**Output/contract:** A structured **design tokens** artifact (color palette, typography scale, spacing units, border radii, component variant rules) in a format like JSON, a Tailwind config, or CSS custom properties — consumed as a constraint by the frontend specialist, not reinvented per component.

**Updated pipeline:**
```
Planning/Requirements Model
      ↓
   Locked Spec (includes product type, language/framework combo)
      ↓
   ┌──────────────────────┐
   │   Design Model         │ → outputs Design System contract (tokens, components, layout rules)
   └──────────────────────┘
      ↓
   ┌─────────────────────┐        ┌──────────────────────┐
   │  Backend Specialist   │        │  Frontend Specialist  │ ← consumes Design System contract
   └─────────────────────┘        └──────────────────────┘
      ↓                                   ↓
   Connector Artifact (API contract between backend/frontend)
      ↓
   Integration / Verification pass
```

**Key distinction: design forks by vertical, not by tech stack.** Design system needs vary far more by product type (portfolio vs. e-commerce vs. SaaS dashboard) than by language/framework combo — a portfolio site's design system differs a lot from an e-commerce site's regardless of whether the backend is FastAPI or Django. This means the design model is likely the **first specialist to fork by vertical**, using the same selection mechanism (planning model picks based on product type) but a different fork axis than the backend/frontend combo table.

**Concrete example — why "UX/UI" isn't one universal skill:**

| Dimension | Portfolio site | E-commerce |
|---|---|---|
| **Primary UX goal** | Showcase, impression, narrative flow | Conversion, trust, frictionless transaction |
| **Layout patterns** | Large imagery, generous whitespace, asymmetric/artistic grids, scroll-driven storytelling | Dense grids (product cards), predictable repeated patterns, clear visual hierarchy for price/CTA |
| **Typography** | Expressive, often bold/editorial — personality matters | Highly legible, conservative, optimized for scanning (price, specs) over personality |
| **Color system** | Can be bold, moody, high-contrast, artistic | Usually calmer with one strong accent color reserved for CTAs (buy button) — restraint is the norm |
| **Component vocabulary** | Hero sections, image galleries, timeline/story components, minimal forms | Product cards, cart/checkout flows, filters, ratings/reviews, quantity selectors, trust badges |
| **Interaction patterns** | Scroll animations, hover reveals, transitions — delight-oriented | Fast load, minimal animation friction, predictable click targets — speed-oriented |
| **Information density** | Low — space to breathe | High — comparisons, specs, filtering |
| **Accessibility priorities** | Matters, but lower stakes (browsing) | Higher stakes — checkout accessibility failures directly cost conversions, often real WCAG compliance requirements |

**Why this requires a different fine-tune, not just a different prompt:** if the underlying goal changes ("impress" vs. "convert"), the model needs different internalized design priors, not just different vocabulary. A model trained mostly on conversion-optimized e-commerce patterns will default to dense, CTA-driven, restrained layouts even when asked for a portfolio site, because that's the pattern it reverts to. Same failure mode in reverse for a portfolio-tuned model asked to build a checkout flow. This is the same underlying dynamic as the backend/frontend base-model selection — training data mix determines what a model treats as "normal," and normal-for-portfolio genuinely conflicts with normal-for-ecommerce in places.

**Practical implication:** likely a "portfolio design specialist" and an "e-commerce design specialist" as separate fine-tunes (or separate LoRA adapters on a shared design-focused base model), selected by the planning model based on product type — same selection mechanism as language/framework, different fork axis.

---

## Decisions Made So Far

1. **No GPU requirement.** Target CPU-only inference on consumer hardware.
2. **RAM target: 8–16GB.** 16GB is the comfortable starting point; 8GB is the stretch goal to hit later.
3. **Model swapping is avoided by design** — the planning model selects which 2 (or N) specialists are needed *once*, at the start of a project. Those stay loaded for the project's lifecycle. No runtime swapping between many models.
4. **Language/framework combos are locked early in the requirements flow**, ideally with the platform recommending a default based on product type — not left ambiguous until later.
5. **First combo to build and train: to be finalized, leaning Python (FastAPI) + React (Vite)** — chosen for: largest training data footprint, most common "build a web app" default, well-supported by existing small open base models to fine-tune from.
6. **Scope specialists narrowly from day one** — not "Python" broadly, but a specific framework (e.g., FastAPI vs Flask vs Django are different enough to matter). Same for frontend (React vs Next.js vs plain Vite+React).
7. **Caching is a hard requirement** — once a combo is downloaded for a user, it must never re-download.
8. **Show real download progress**, not a spinner (e.g., "Downloading Python backend model (1.2GB/2.4GB)...").
9. **Start the model download as soon as the combo is locked in the requirements flow** — not after planning fully ends. Overlap download time with remaining planning conversation.
10. **Ship the most common combo pre-bundled** in the base install (zero wait for majority case); fetch other combos on demand.

---

## Base Model Candidates

Different models have real strengths/weaknesses per task — even within "coding" — due to differences in training data mix and architecture. This means **the best base model is likely different per specialist role** (backend vs. frontend), and possibly **different per vertical/product type** (see Combo vs. Product Type table above), not one universal winner picked once.

| Candidate | Size | Architecture | Strengths | Notes / Caveats |
|---|---|---|---|---|
| **MiniCPM5-1B** (OpenBMB/Tsinghua) | 1.08B dense | Standard Llama-style | Highest Artificial Analysis Intelligence Index score (17.9) of any open model ≤1B; strongest reported gains in agentic tool use, code generation, competition math; OpenBMB average benchmark score 42.57 vs. 35.61 next-best in class | Standard architecture = runs cleanly on existing GGUF/llama.cpp/Ollama tooling, no custom kernels needed; ships with official fine-tuning "Agent Skills"/cookbooks. **Current default candidate for backend specialist.** |
| **LFM2.5-8B-A1B** (Liquid AI) | 8.3B total / ~1.5B active (MoE) | Mixture-of-Experts | Strong on instruction-following, agentic tasks, and speed (213 tok/s on phone CPU, 42 tok/s on Raspberry Pi 5); beats models twice its size on instruction-following/tool use | MoE may be trickier to LoRA fine-tune than a dense model — verify tooling maturity before committing. Worth benchmarking against MiniCPM5-1B once eval suite exists. |
| **Qwen3.5-0.8B** | ~0.8B dense | Standard | General-purpose, some multimodal capability, next-best on Intelligence Index after MiniCPM5-1B among small models | Clear step down from MiniCPM5-1B on code/agentic benchmarks specifically — reasonable lightweight fallback only if a smaller footprint is needed. |
| **Gemma 4 E2B** | ~2.3B effective | Dense + multimodal | Multimodal (text+image+audio), demoed fully on-device (Raspberry Pi 5, Jetson Orin Nano) | Modest for text-only tasks — not a strong fit unless image/audio input becomes a requirement. |
| **HRM-Text-1B** (sapientinc) | ~1.15B | Hierarchical/recurrent reasoning model | Tuned for reasoning efficiency (MATH/DROP) and data efficiency | Non-standard architecture — likely less mature tooling/community support for fine-tuning/deployment than a plain transformer. |

**Selection approach (not a one-time global pick):**
1. Pick 1–2 candidate base models per specialist **role** (backend vs. frontend) — don't assume one winner fits both.
2. Fine-tune each candidate on the same narrow dataset for that role.
3. Run the held-out eval suite (see Training Infrastructure & Pipeline section) against each candidate.
4. Pick per-role based on actual eval results, not benchmark reputation alone.
5. As additional verticals/combos are added (per the Combo vs. Product Type table), re-run this same comparison rather than assuming the first combo's winning models generalize — e.g., a model well-suited to FastAPI backend logic may not be the best choice for a Django-heavy e-commerce specialist, and a React specialist may not be the best base for a later Next.js or React Native specialist.

**Working hypothesis to test, not assume:** MiniCPM5-1B's demonstrated code/agentic strength makes it the safer default for backend specialists (API logic, tool use, structured task completion). Frontend/UI generation draws on different skills (visual/layout reasoning, component composition) that aren't as clearly reflected in current benchmarks — explicitly test MiniCPM5-1B against at least one alternative (e.g., LFM2.5) on React-specific tasks before locking it in as the frontend specialist too.

## Dependency-Graph Tooling: Graphify

**Tool identified: `Graphify-Labs/graphify`** (MIT licensed, PyPI package `graphifyy`) — directly usable for the triage step's "which files are actually affected" problem.

**What it does:** Turns a codebase into a queryable knowledge graph, parsed locally via tree-sitter AST (no LLM needed for code, nothing leaves the machine), covering ~40 languages. Builds `calls`/`imports`/`inherits`/`mixes_in` relationships between files/modules; every edge is tagged `EXTRACTED` (explicit in source) or `INFERRED` (derived), so what's fact vs. derived is always traceable. Supports direct queries: `graphify path "A" "B"` traces the actual dependency path between two things; `graphify explain "X"` shows everything connected to a node.

**Role in the pipeline:** when a mid-build change request comes in, query Graphify against the current codebase to get a real, traceable list of affected files/modules — replacing blind LLM guessing about scope/impact. The planning model then uses that concrete impact list (not just the raw user request) to make the delta-vs-replan judgment (see Open Risks — Status Notes; this makes triage tool-assisted, not tool-solved — the threshold judgment itself is still deferred per the "no delta path yet" decision above).

**Integration approach: direct Python import (preferred), not just CLI/subprocess.**
- `graphifyy` is a real PyPI package, 100% Python — installable and importable directly (`pip install graphifyy`) rather than only shelled out to as an external CLI.
- Fallback/alternative: MCP server mode (`python -m graphify.serve graph.json`) — treat Graphify as a service the orchestration layer calls as a tool. Lower integration risk but adds a subprocess/serialization boundary. Keep this as a documented fallback, not a discarded option.

**Caveat and de-risking plan:** Graphify's public docs describe CLI/skill usage, not a documented stable library API — internal functions could shift between versions without a deprecation path. Mitigations, in order:
1. **Pin the exact version** integrated against; upgrade deliberately with re-testing, not automatically.
2. **Wrap it behind a thin internal adapter module** (e.g., `deps_graph.py` exposing only `get_affected_files(...)`, `get_dependency_path(a, b)`) — isolates breakage to one file if Graphify's internals change.
3. **Prefer their actually-documented stable surface where possible** — the `graph.json` output format (also used by their Neo4j/FalkorDB/MCP integrations) is the part implicitly committed to stability; design the adapter to read/write this format rather than depending on arbitrary internal function names.
4. **Add a smoke test** in the project's own test suite that runs Graphify against a known sample project after every version bump, checking expected output shape.
5. **Keep the MCP/subprocess path as a safety net** — fall back to it if a future version breaks the direct-import integration.

---

## Combo vs. Product Type

Full tech stack per product type — backend/frontend framework plus database, auth, and payments — since a real product needs more than just the two specialist models. Same principle as the backend/frontend/design forking already decided: **database and auth patterns are also product-type-dependent, not universal.**

| Product Type | Backend | Frontend | Database | Auth | Payments | Other Key Pieces | Why This Pairing | General Demand Signal |
|---|---|---|---|---|---|---|---|---|
| **Portfolio / personal site** | None, or minimal (Flask if a contact form needs server logic) | Next.js (static export) or React+Vite | None, or not needed | None | None | Image/asset hosting (static CDN), SEO meta tags | Mostly static content, minimal server logic; static-site generation is the standard pattern | Very high volume of use cases, but often served by no-code tools (Squarespace, Webflow) rather than custom code — moderate demand for a coding tool specifically |
| **E-commerce** | Django (or FastAPI if headless) | Next.js (SSR/SEO) | PostgreSQL (relational — orders, inventory, users) | Session/JWT-based, often via Django's built-in auth | **Required** — Stripe or similar (see Payments Module below) | Cart/session state, inventory management, order emails (transactional email service), search/filtering | Commerce needs strong data modeling, admin tooling, and SEO-friendly rendering — Django's batteries-included nature and Next.js's SSR are the common real-world pairing | High demand; but also heavily served by Shopify/WooCommerce — custom-code demand concentrated among sellers wanting more control |
| **Web app (SaaS-style, dashboards, tools)** | FastAPI (async, API-first, fast to iterate) | React + Vite (SPA, fast dev loop) | PostgreSQL (most common default for structured app data) | JWT-based, often with role/permission levels | Optional — Stripe if subscription/billing is part of the product (see Payments Module below) | API rate limiting, background job queue, possibly WebSockets for real-time features | This is the "generic CRUD app with an API" case — FastAPI+React is close to the modern default for this shape | Highest overall demand — this is the most common "I want to build an app" request across tutorials, bootcamps, and indie builders |
| **Mobile app** | FastAPI (or shared with web app backend) | React Native (shares React mental model, cross-platform) | PostgreSQL (shared backend) | JWT/token-based (mobile-appropriate, e.g. refresh tokens) | Depends on app type — in-app purchases via App Store/Play Store APIs if applicable | Push notifications, offline-sync handling, App Store/Play Store deployment pipeline | Mobile needs a native/cross-platform frontend, not a web frontend — React Native reuses React concepts, easing the framework jump | High and growing demand, but meaningfully different tooling (Xcode/Android SDK dependencies) — likely a later-phase addition, not first combo |
| **Blog / content site** | Django (if custom CMS) or none (if static) | Next.js (SSG/ISR, excellent for content + SEO) | PostgreSQL or none (if fully static/markdown-based) | Admin-only auth (not end-user facing) | None | RSS feed, SEO/sitemap generation, comment system (optional) | Content-heavy sites lean hard on static generation and SEO; Next.js dominates this space in real-world usage | High demand, but often satisfied by existing CMS platforms (WordPress, Ghost) — moderate demand for fully custom code |
| **Internal tool / admin panel** | Django (admin panel built-in) or FastAPI + a UI kit | React + Vite, or server-rendered Django templates | PostgreSQL | Simple auth, often single-role or a few fixed roles | None | Often lower priority on polish/performance, higher priority on quick CRUD scaffolding | Low external users, speed-to-build matters more than polish — Django's built-in admin is a strong shortcut here | Steady, consistent demand (every company needs a few) but lower glamour/visibility than consumer apps |

**Reading for combo build order:**
- **FastAPI + React/Vite** covers the highest-demand bucket (general web apps/SaaS/dashboards) — confirms it as the right first combo.
- **Django** becomes the stronger fit once e-commerce, blogs, or admin panels enter scope — candidate **second backend specialist**.
- **Next.js** is the recurring frontend choice whenever SEO/content-rendering matters — candidate **second frontend specialist** after plain React+Vite.
- **Mobile (React Native)** is high-demand but structurally different enough (native build tooling, device SDKs) to treat as a later phase.

**Decision: Payments (Stripe integration) is a shared, separately-maintained module — not duplicated per backend specialist.**
Rather than training every backend specialist (FastAPI, Django, future ones) to independently know "how to integrate Stripe," payments is treated as its own narrow, well-defined, high-stakes capability that any backend specialist calls into when a product's spec requires it. Rationale:
- It shows up across multiple product types (e-commerce checkout, SaaS subscription billing, mobile in-app purchases) — building it once and sharing it avoids duplicating training/maintenance effort across every backend specialist.
- Money handling is high-stakes and benefits from being maintained, tested, and updated as a single well-audited module rather than N separately-trained copies that could drift or handle edge cases inconsistently.
- This is the same "narrow shared capability" pattern already used for other cross-cutting concerns in this architecture (e.g., the dependency-graph tool) — specialize narrowly, share what's genuinely common.

**Open item:** decide the payments module's interface — likely a defined contract (similar to the API/design-token contracts elsewhere in this pipeline) that a backend specialist's generated code calls into, rather than the backend specialist generating raw Stripe integration code itself.

---


## Open Questions / To Be Decided

- [ ] Final first combo: confirm exact stack (e.g., FastAPI + React/Vite vs alternatives)
- [ ] What counts as "good at Python backend" for training scope — REST APIs? Auth? DB access patterns? Testing? Needs explicit definition before fine-tuning.
- [ ] Base model to fine-tune from for each specialist (candidates: Qwen family, MiniCPM5-1B, CodeLlama family — needs evaluation)
- [ ] Exact schema/format for the planning model's output (the "contract" both specialists consume) — this is reused for every future combo, so needs to be right early
- [ ] Exact schema/format for the connector artifact (OpenAPI-style contract between backend/frontend)
- [ ] Model file format / runtime (GGUF via llama.cpp/Ollama vs other) — likely GGUF given RAM/CPU targets
- [ ] Quantization level per model (Q4/Q5 tradeoff between size and quality)
- [ ] How new requirements mid-build are handled — treated as a new cycle (versioned spec bump), not a live patch to a running contract
- [ ] Long-term model library maintenance plan — this is an ongoing content/training pipeline problem, not a one-time build, as more language/framework combos are added
- [ ] Default combo bundling strategy — which combo(s) ship pre-installed vs fetched on demand, and how that decision gets revisited as usage data comes in

---

## Principles to Preserve As the System Grows

- **Contract stability during a build cycle.** No live renegotiation of API shape mid-build. New requirements = new cycle, not a mutation of the current one.
- **Planning/requirements model is the highest-leverage component** — more important to get right than the coding specialists themselves, because planning errors are invisible until much later (correctly-built wrong thing), while specialist errors are usually visible immediately (code doesn't run).
- **Small models should stay narrow.** Resist the urge to make any one specialist "know a bit of everything" — narrowness is what keeps them fast, small, and low-error.
- **Retrieval/lookup is a fallback, not the default path.** Local, pre-scoped knowledge (or a fast local index) should handle the common case; live web lookup only for things that are genuinely dynamic (e.g., current library versions, live docs).
- **Schema validation is necessary but not sufficient.** Confirming a stage's output matches the expected shape (valid JSON, correct fields, well-formed delimited text) only proves the *format* is right — it says nothing about whether the *content* actually does what was asked. The custom orchestrator prototype (2026-07-20) demonstrated this directly: the Backend stage produced a schema-valid, protocol-compliant response that was still a shallow stub, not an implementation of the requested features. Every specialist stage — Backend, Frontend, Design, and any future stage (e.g., Payments) — needs an appropriate correctness check beyond shape-matching: for code, this might mean executing it and checking behavior (as already required for training-data verification) or checking for required feature markers; for design tokens, it might mean checking accessibility contrast ratios or completeness against the requested component list. Treat "passed schema validation" and "actually correct" as two separate gates, not one.
