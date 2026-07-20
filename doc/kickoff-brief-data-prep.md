# Kickoff Brief for Claude Code — Phase 1 Parallel Track: Training Data Prep

**Context:** This runs in parallel with the separate MetaGPT trial (`claude-code-kickoff-brief.md`). It does not depend on that trial's outcome. Reference `democratized-ai-coding-architecture.md` for full background if needed.

**Scope:** FastAPI backend specialist only, for now (Phase 1 combo = FastAPI + React/Vite web app; this brief covers the backend half).

**Model recommendation:** Use a higher-tier model (e.g. Opus, or your best available option) for the category research, task→code pair generation/verification, and eval suite steps below — this phase is a one-time curation/verification investment where correctness matters more than speed or cost, unlike the actual product's end-user inference. A lighter/default model is fine for the Colab environment setup step.

## Task 1 — Task category research (do this first, don't skip)

Before generating any task→code pairs, research real-world FastAPI project structure and common patterns — don't invent categories from general knowledge alone. Look at actual FastAPI documentation, popular open-source FastAPI repos, and common tutorial/course structures to identify the real, representative task categories (e.g., CRUD endpoints, auth/JWT, pagination, DB models via SQLAlchemy/Pydantic, error handling, dependency injection, background tasks, etc.). Propose a category list with a brief rationale for each, and check it against what actual FastAPI codebases commonly need — not just what sounds plausible.

**Output format: Markdown** (`task-categories.md`) — this is a reference document for human review, not machine-consumed, so a written list with rationale is correct here.

## Task 2 — Task→code pairs (the highest-risk step — be rigorous)

For each category from Task 1, generate a batch of task descriptions paired with FastAPI code. Critical requirement: **every code sample must be actually executed and verified to run correctly** before being counted as a clean example — not just visually plausible. Set up a way to run each generated FastAPI snippet (e.g., spin it up and hit it with test requests) and only keep pairs that pass. Log which ones failed and why — that's useful signal too, not just discarded output.

Target: start with a modest batch (e.g., 50-100 verified pairs) rather than trying to hit "a few thousand" in one pass. Quality and real diversity matter more than volume at this stage — report back with a sample so quality can be checked before scaling up.

**Output format: JSONL** (`fastapi-backend-pairs.jsonl`), one JSON object per line — this feeds directly into the fine-tuning pipeline (Hugging Face `transformers`/`peft`), so it must be structured data, not markdown or prose. Each line should look like:
```json
{"task": "Create a FastAPI endpoint that returns a paginated list of users", "code": "...", "category": "pagination", "verified": true, "verification_notes": "ran with uvicorn, tested GET /users?page=1&limit=10, returned 200 with expected shape"}
```
Do not output this as markdown code blocks or a written report — it must be directly loadable as structured records (e.g. via `json.loads` per line).

## Task 3 — Evaluation suite (build independently from Task 2)

Build a held-out set of ~20-50 realistic FastAPI tasks that the eventual fine-tuned model will be tested against. Important: **these must be genuinely independent of the training pairs from Task 2** — different specific tasks, not held-out copies of the same patterns — so the eval is a real test of generalization, not something the model could pass by memorization or coincidence. Each eval task should have a way to programmatically check correctness (e.g., run the generated code, verify expected behavior), not just human eyeballing.

**Output format: JSONL** (`fastapi-eval-suite.jsonl`), same structured-record principle as Task 2 — this needs to be programmatically run against a model later, not read by a person. Each line should include the task prompt plus a machine-checkable success criterion, e.g.:
```json
{"task": "Create a FastAPI endpoint for user login that returns a JWT", "category": "auth", "check_type": "http_test", "check_spec": {"method": "POST", "path": "/login", "expected_status": 200, "expected_keys": ["access_token", "token_type"]}}
```

## Task 4 — Colab Pro environment setup

Set up the training environment: Colab Pro (~$10/month, already decided), with the standard fine-tuning stack — Hugging Face `transformers` + `peft` (LoRA) + `bitsandbytes` (for QLoRA 4-bit quantization). Find/adapt a working notebook template for LoRA fine-tuning a small (1-3B) model, and confirm it runs end-to-end (even on placeholder/dummy data) before real training data is ready. This is lower-risk, mechanical setup — default model tier is fine here.

**Output format: Jupyter notebook** (`.ipynb`) — an actual working Colab notebook, not a markdown description of one. It should be uploadable to Colab and run as-is (with dummy data as a placeholder for now).

## What NOT to do yet

- Don't start the actual LoRA fine-tuning training run — that's intentionally deferred until the MetaGPT trial confirms the contract/handoff format the specialist's training examples should mirror.
- Don't build frontend (React/Vite) task pairs yet — backend (FastAPI) only for this pass.
- Don't try to hit large dataset volume in the first pass — small, verified batch first, then scale.

## Definition of done for this task

- A researched, justified list of FastAPI task categories
- A first verified batch of task→code pairs (50-100), with a clear log of what passed/failed verification
- An independent eval suite of 20-50 tasks with programmatic correctness checks
- A working Colab notebook environment for LoRA fine-tuning, tested end-to-end on dummy data
