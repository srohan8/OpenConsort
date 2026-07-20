# Training-Data-Prep Track — Final Report

Phase 1 FastAPI backend specialist. All outputs in `data-prep/`.

## Deliverables
| # | Deliverable | File | Status |
|---|---|---|---|
| 1 | Task category research | task-categories.md | Done — 13 categories |
| 2 | Verified task→code pairs | fastapi-backend-pairs.jsonl | Done — 71 pairs, all executed & verified |
| 3 | Independent eval suite | fastapi-eval-suite.jsonl | Done — 31 held-out tasks, runner smoke-tested |
| 4 | LoRA/QLoRA Colab notebook | fastapi_lora_qlora_colab.ipynb | Done — valid, syntax-clean, runs on dummy data |

Supporting reusable code: verify_pairs.py (harness), eval_runner.py (eval checker),
candidates_a.py/candidates_b.py, build_dataset.py, build_eval.py, build_notebook.py.
Logs: verification-log.md, verification-log.jsonl.

## Environment
Python 3.12 venv at data-prep/.venv. Installed fastapi, uvicorn, httpx, pytest, pydantic,
python-jose[cryptography], passlib, sqlalchemy, python-multipart, bcrypt==4.0.1 (pinned),
email-validator.

## Task 1 — Categories (13)
crud, pydantic-models, path-query-params, response-status-codes, error-handling,
dependency-injection, auth-jwt, pagination, database-sqlalchemy, background-tasks,
file-upload, routing-structure, middleware-cors. Cross-referenced against the FastAPI
tutorial TOC, common real project structure (models/schemas/crud/api/core/deps), and the
Phase 1 locked stack. Weighting guidance and exclusions (payments, websockets, rate-limit,
frontend) documented in task-categories.md.

## Task 2 — Pairs: 71 generated, 71 kept-verified, 0 failed (final run)
Every kept pair was actually executed via fastapi.testclient.TestClient: snippet exec'd
into an isolated sys.modules-registered module, wrapped in TestClient (fires startup/
shutdown), driven with real requests, responses asserted (status, JSON shape, headers,
side effects). Only passing pairs written to JSONL.

Per-category: crud 8, pydantic-models 7, auth-jwt 7, path-query-params 6, error-handling 6,
dependency-injection 6, response-status-codes 5, pagination 5, database-sqlalchemy 5,
background-tasks 4, file-upload 4, routing-structure 4, middleware-cors 4.

### Failure signal (encountered during iteration)
1. bcrypt/passlib incompatibility (bcrypt>=4.1 breaks passlib version probe + >72-byte
   inputs). Fixed by pinning bcrypt==4.0.1.
2. Pydantic "class not fully defined" — 5 model-body pairs failed until the harness
   registered exec'd snippets in sys.modules so Pydantic could rebuild models. Harness bug,
   not bad code — but proof that real execution catches what eyeballing wouldn't.
3. email-validator missing for EmailStr — installed.
4. Escaped-newline bug in an early CSV upload check — caught by a failed assertion, fixed.

## Task 3 — Eval suite (31 held-out tasks, genuinely independent)
Different resources/behaviors than Task 2 (invoices, bookmarks, events, geo, temperature,
jobs, robots.txt, withdraw/rate-limit, tenant header, dashboards, articles, logs, catalog,
movies, employees, tags, emails, page-view tracking, avatars, csv-import, /api/v2,
request-id, CORS). Each has an http_sequence check_spec run by eval_runner.py: multi-step
sequences with saved variables (capture JWT, reuse as Bearer {tok}) and assertions on
status, json_keys, json_subset, json_equals, json_len, and headers.

Runner validated: reference solutions for auth flow, articles pagination (json_len),
avatar upload, and CORS all returned (True, 'all steps passed'); a deliberately-wrong impl
(200 instead of 202) returned (False, 'step 0: expected status 202, got 200'). Reference
solutions were only for validating the runner — not part of any dataset.

## Task 4 — Colab notebook
22 cells, valid nbformat, all Python cells syntax-clean. transformers + peft (LoRA) +
bitsandbytes (4-bit QLoRA, nf4 + double quant) on Qwen/Qwen2.5-Coder-1.5B. Auto-loads the
real JSONL if uploaded, else 3 embedded dummy pairs. CPU fallback path. Tiny 1-epoch dummy
settings + scaling notes. NOT run here (no GPU); no real training started (deferred).

## Human review before scaling up
1. Consider skewing counts toward the heavy tier (auth/crud/DI/pydantic) when scaling past 71.
2. DB pairs use in-memory SQLite (API-compatible, executable). Locked stack is PostgreSQL —
   add a Postgres-backed verification lane before shipping.
3. Reshape the pairs' task field to mirror the planning→specialist contract once the
   MetaGPT trial locks that format (brief flags this dependency).
4. Pin bcrypt==4.0.1 and email-validator in the training environment.
5. Pairs are single-file for verifiability; add multi-module pairs if the specialist must
   emit project structure (routing-structure is the seed).
