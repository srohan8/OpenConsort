# Kickoff Brief for Claude Code — PostgreSQL Verification Lane

**Context:** Long-standing known gap, flagged since the original data-prep phase and reaffirmed multiple times in `doc/architecture.md`'s Testing Log and Open Risks: the training dataset's DB-related examples use in-memory/file-based SQLite, but the locked Phase 1 stack (`LockedSpec.stack.database`) is **PostgreSQL**. This task closes that gap.

## Goal of this task

Verify (and where needed, fix) all database-related examples in `fastapi-backend-pairs-v3.jsonl` against a **real PostgreSQL instance**, not SQLite — confirming the generated code actually works against the locked production database, not just a compatible substitute.

## Why this matters concretely

SQLite and PostgreSQL have real behavioral differences that could make "verified against SQLite" code silently wrong against Postgres:
- Connection string / driver differences (`sqlite:///` vs `postgresql://` or `postgresql+psycopg2://`/`postgresql+asyncpg://`)
- `ilike` case-insensitive matching (works natively in Postgres, SQLite needs `func.lower()` workarounds or has different case-sensitivity defaults depending on configuration)
- Autoincrement/serial behavior differences for primary keys
- Type strictness differences (SQLite is famously loose about column types; Postgres enforces them)
- Connection pooling / `check_same_thread` (SQLite-specific, meaningless/wrong for Postgres — currently present in the SQLAlchemy examples added in Round 1, needs removing/replacing for a Postgres version)

## Steps

1. **Set up a local PostgreSQL instance for testing.** Docker is the simplest, most reproducible approach:
   ```
   docker run --name openconsort-test-pg -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=testdb -p 5432:5432 -d postgres:16
   ```
   Confirm it's running and reachable before proceeding.

2. **Install the Postgres driver** needed for SQLAlchemy (`psycopg2-binary` for sync, or `asyncpg` if the project moves to async — check what's already used elsewhere in the codebase/orchestrator and stay consistent; default to sync/`psycopg2-binary` unless there's a clear reason not to).

3. **Identify every DB-related row** in `fastapi-backend-pairs-v3.jsonl` (category `database-sqlalchemy`, currently ~6 rows: the original SQLite-based ones from data-prep plus the 3 added in Round 1).

4. **For each one, rewrite the connection/engine setup for Postgres** (keep the model classes, routes, and business logic identical — only the engine/connection layer should change):
   - Replace `create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})` with `create_engine("postgresql://postgres:testpass@localhost:5432/testdb")` (or read from an env var, better practice — check if the project already has a `.env` pattern from `orchestrator.py`'s `_load_dotenv()` and follow that convention)
   - Remove the SQLite-specific `connect_args={"check_same_thread": False}` — not needed/meaningful for Postgres
   - Check `ilike` usage specifically (the tags-filtering example) — should work natively in Postgres, confirm it actually does rather than assuming
   - Watch for any other SQLite-specific quirks that might have silently worked before but need adjustment for Postgres

5. **Actually execute-verify each rewritten example against the real Postgres instance** — same non-negotiable standard used throughout this project: run each app via `TestClient`, hit it against the real running Postgres container, confirm the check_spec still passes. Do not assume "it's basically the same as SQLite" without running it.

6. **Decide on dataset strategy**, and flag your reasoning rather than assuming:
   - **Option A:** Replace the SQLite-based rows with Postgres-verified equivalents (same task, same check_spec, different `code`) — cleaner, matches the locked stack exactly
   - **Option B:** Add Postgres-verified versions as new rows alongside the existing SQLite ones (both stay in the dataset) — preserves more training diversity but trains the model on two different DB setup patterns for the same stack, which may be confusing rather than helpful
   - Recommend Option A unless you find a good reason for B; note this decision either way

7. **Update the connection-string pattern going forward** — since all future DB-related training examples (and the orchestrator's own generated code, eventually) should target Postgres by default, not SQLite, given it's the locked stack.

## What NOT to do in this task

- Don't touch non-DB-related rows in the dataset.
- Don't start Round 3 augmentation or retraining — this is a standalone fix, orthogonal to the Round 1/2 augmentation work.
- Don't modify `orchestrator/llm_client.py`, `CONTRACT.md`, or the orchestrator's own prompts as part of this task — if you find the `BACKEND_SYSTEM` prompt should mention Postgres more explicitly (it references `LockedSpec.stack.database` already, so it should already be conveying this), note it as a flag rather than modifying it here.
- Don't require Docker Compose or a permanent Postgres service running 24/7 — a throwaway container for verification purposes is sufficient; document how to spin it up/down for reproducibility.

## Definition of done

- A working local Postgres instance used for verification (documented setup steps, e.g. the Docker command)
- All DB-related dataset rows re-verified (or rewritten and verified) against real Postgres, not SQLite
- Updated `fastapi-backend-pairs-v3.jsonl` reflecting the Postgres-verified versions (per the Option A/B decision above)
- A short report: how many rows were affected, what specifically had to change (connection strings, `ilike` behavior, anything else), whether everything passed cleanly or needed adjustment, and confirmation of the round-trip/schema-consistency checks (same standard as prior rounds — all rows share identical keys, `output` parses correctly via `extract_files` and matches `code`)
