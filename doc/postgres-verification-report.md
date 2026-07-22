# PostgreSQL Verification Lane — Report

**Date:** 2026-07-22
**Scope:** Per `doc/kickoff-brief-postgres-verification.md`.

## Setup: no Docker needed

Docker was not available on this machine (`docker` not found via Bash or PowerShell). Rather than installing Docker Desktop (heavy) or native PostgreSQL as a persistent Windows service (conflicts with the brief's explicit "don't require a permanent Postgres service running 24/7"), used **`pgserver`** — a Python package that runs a real, embedded PostgreSQL server (actual Postgres binaries, not a mock/compatibility shim) against a throwaway data directory, with no system install, no admin rights, no background service. Verified working: started a server, ran a query, cleaned up — all in a few lines, fully reproducible, arguably an even better fit for "throwaway container for verification purposes" than the suggested Docker command.

```python
import pgserver, tempfile
db = pgserver.get_server(tempfile.mkdtemp())
print(db.get_uri())   # postgresql://postgres:@127.0.0.1:PORT/postgres
db.cleanup()
```

Driver installed: `psycopg2-binary` (sync), per the brief's default preference — nothing in the codebase suggested an async requirement.

## Rows identified and affected

**8 rows** in `fastapi-backend-pairs-v3.jsonl` had `category == "database-sqlalchemy"`: 5 original (rows 50–54, from the initial data-prep phase) plus 3 added in Round 1 (rows 71–73) — more than the brief's "~6 rows" estimate, but all genuinely DB-related.

Two variants of the SQLite engine setup existed across these 8 rows:
- Rows 50–54: `create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)` (in-memory SQLite)
- Rows 71–73: `create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})` (file-based SQLite — notably, all 3 rows pointed at the **same** `./test.db` filename, a latent cross-contamination risk if ever run in the same working directory, incidentally resolved by moving off SQLite entirely)

## What changed

For all 8 rows, only the connection/engine-setup layer changed — models, routes, and business logic are byte-identical to before:

- `create_engine("sqlite://...", ...)` → `create_engine(os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/appdb"))` — env-var driven, matching the `.env`/`os.getenv(...)` convention already established in `orchestrator.py`'s `_load_dotenv()` pattern, with a sensible literal fallback.
- `connect_args={"check_same_thread": False}` — removed (SQLite-specific, meaningless for Postgres).
- `poolclass=StaticPool` and its import — removed (SQLite-in-memory-specific workaround, not needed for a real server-based Postgres).
- `ilike` usage (rows 54 and 71) — **left untouched and re-executed against real Postgres to confirm**, not assumed compatible. Both passed: Postgres's native `ilike` behaved exactly as the SQLAlchemy code expected, no changes needed there.

## Verification results

**All 8 rewritten rows passed on the first attempt**, executed via `TestClient` against a real, freshly-created, isolated Postgres database per row (one shared embedded Postgres *server*, but a distinct `CREATE DATABASE` per row so no state leaked between tests) — check_specs reconstructed from each row's existing `verification_notes` plus its actual endpoints (the training-pairs schema doesn't persist a `check_spec` field, only free-text notes, so these were rebuilt to match, not invented from scratch).

```
[PASS] row 50: SQLAlchemy CRUD roundtrip (Users)
[PASS] row 51: list from DB (Products)
[PASS] row 52: DB delete 204 then 404 (Notes)
[PASS] row 53: DB update (Tasks)
[PASS] row 54: ilike filter (Cities)               <- ilike confirmed native on Postgres
[PASS] row 71: Tags, case-insensitive q= filter    <- ilike confirmed native on Postgres
[PASS] row 72: Employees CRUD
[PASS] row 73: Notes CRUD
```

No adjustments beyond the engine-layer rewrite were needed — the business logic was already correct; only the SQLite-specific connection scaffolding was wrong for the locked stack.

**Defensive re-check:** after writing the updated rows to disk, re-ran all 8 checks a second time reading directly from the persisted `fastapi-backend-pairs-v3.jsonl` file (not the in-memory rewrite) against a fresh Postgres instance — confirmed the file on disk is exactly what was verified, not just what was intended to be written.

## Dataset strategy: Option A (replace)

Went with **Option A** as the brief recommended by default: the 8 SQLite rows were replaced in place with their Postgres-verified equivalents — same `task`, `category`, `locked_spec`, `design_tokens`, `system_prompt`, `user_prompt`, `input_format` (all byte-identical to before); only `code`, `output`, and `verification_notes` changed. No reason found to prefer Option B — training the model on two different DB setup patterns for one locked stack would add confusion, not useful diversity, since `LockedSpec.stack.database` is always `"PostgreSQL"` for this project, never SQLite in production.

**Round-trip/schema-consistency confirmation** (same standard as prior rounds):
- All 93 rows (8 changed + 85 untouched) share identical key sets — asserted programmatically.
- Every changed row's `output` re-verified to round-trip through the real `extract_files` parser and match its new `code` field exactly.
- Total dataset size unchanged: **93 rows** (this was a replace, not an add).

## Flag (not fixed, per the brief's scope limit)

`BACKEND_SYSTEM` (in `orchestrator/orchestrator.py`) does **not** explicitly mention the database/stack at all — it says "Given a LockedSpec and DesignTokens, write the backend code," relying entirely on the model reading `LockedSpec.stack.database` out of the JSON payload itself rather than an explicit instruction to target it. This worked fine in this task's verification (the *reference* code was hand-written, not model-generated), but it's worth noting as a possible future weak point: nothing in the prompt explicitly says "use the database specified in `stack.database`" — a trained specialist could plausibly default to a familiar pattern (e.g. SQLite) if not reinforced by training examples using PostgreSQL specifically. Since this dataset's DB rows now use Postgres exclusively, this is a much smaller risk than before this task, but the prompt itself was left unmodified per the brief's explicit instruction to flag rather than fix.

## What NOT done (per scope)

- Non-DB rows untouched.
- No Round 3 augmentation or retraining — this was a standalone fix.
- `orchestrator/llm_client.py`/`CONTRACT.md` untouched.
- No permanent Postgres service left running — the embedded server was started fresh for each verification script run and cleaned up (`server.cleanup()`) afterward; nothing persists between sessions except the dataset file itself.

## Recommended next step

Retrain on the now-Postgres-verified 93-row dataset and rescore against `fastapi-eval-suite-v3.jsonl` (using the permanent `eval_runner_v3.py` from the prior task) — this closes a long-standing, multiply-flagged gap between what the dataset taught and what the locked production stack actually is. Worth watching in the next eval run specifically whether `database-sqlalchemy` category performance holds steady or improves now that the training examples match the real deployment target exactly.
