# -*- coding: utf-8 -*-
"""Rewrite + verify the 8 database-sqlalchemy rows in fastapi-backend-pairs-v3.jsonl
against a REAL local PostgreSQL instance (via `pgserver`, embedded - no Docker/
system service needed), per doc/kickoff-brief-postgres-verification.md.

Each row's `code` is rewritten to use a Postgres connection string (read from
DATABASE_URL, falling back to a sensible default - matching the env-var
convention already used in orchestrator.py's _load_dotenv()), with the
SQLite-specific `connect_args={"check_same_thread": False}` / `StaticPool`
removed (meaningless for Postgres). Business logic, models, and routes are
left untouched. Each rewritten example is then actually executed via
TestClient against a real, freshly-created Postgres database (one per row,
for isolation) and checked against a reconstructed check_spec.
"""
import json
import re
import sys
import tempfile
import itertools
from pathlib import Path

import psycopg2
import pgserver

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_runner import run_eval  # reuse, don't reimplement

PAIRS_PATH = Path(__file__).resolve().parent / "fastapi-backend-pairs-v3.jsonl"
DB_ROW_INDICES = [50, 51, 52, 53, 54, 71, 72, 73]

# --- Reconstructed check_specs (the training pairs file doesn't store
#     check_spec, only free-text verification_notes - rebuilt here from the
#     notes + the actual endpoints in each row's code) ---
CHECK_SPECS = {
    50: {"steps": [
        {"method": "POST", "path": "/users", "json": {"name": "Alice"}, "save": {"uid": "$.id"},
         "expect": {"status": 201, "json_subset": {"name": "Alice"}}},
        {"method": "GET", "path": "/users/{uid}", "expect": {"status": 200, "json_subset": {"name": "Alice"}}},
        {"method": "GET", "path": "/users/99999", "expect": {"status": 404}},
    ]},
    51: {"steps": [
        {"method": "GET", "path": "/products", "expect": {"status": 200, "json_len": {"path": "$", "op": "==", "value": 2}}},
    ]},
    52: {"steps": [
        {"method": "DELETE", "path": "/notes/1", "expect": {"status": 204}},
        {"method": "DELETE", "path": "/notes/1", "expect": {"status": 404}},
    ]},
    53: {"steps": [
        {"method": "PUT", "path": "/tasks/1", "json": {"title": "new title"}, "expect": {"status": 200, "json_subset": {"id": 1, "title": "new title"}}},
        {"method": "PUT", "path": "/tasks/9999", "json": {"title": "x"}, "expect": {"status": 404}},
    ]},
    54: {"steps": [
        {"method": "GET", "path": "/cities", "params": {"q": "lon"}, "expect": {"status": 200, "json_equals": ["London"]}},
    ]},
    71: {"steps": [
        {"method": "POST", "path": "/tags", "json": {"name": "Python"}, "expect": {"status": 201, "json_subset": {"name": "Python"}}},
        {"method": "POST", "path": "/tags", "json": {"name": "Rust"}, "expect": {"status": 201}},
        {"method": "GET", "path": "/tags", "params": {"q": "pyth"}, "expect": {"status": 200, "json_len": {"path": "$", "op": "==", "value": 1}}},
    ]},
    72: {"steps": [
        {"method": "POST", "path": "/employees", "json": {"name": "Bob"}, "save": {"eid": "$.id"},
         "expect": {"status": 201, "json_subset": {"name": "Bob"}}},
        {"method": "GET", "path": "/employees/{eid}", "expect": {"status": 200, "json_subset": {"name": "Bob"}}},
        {"method": "GET", "path": "/employees/9999", "expect": {"status": 404}},
    ]},
    73: {"steps": [
        {"method": "POST", "path": "/notes", "json": {"text": "hi"}, "save": {"nid": "$.id"},
         "expect": {"status": 201, "json_subset": {"text": "hi"}}},
        {"method": "GET", "path": "/notes", "expect": {"status": 200}},
        {"method": "DELETE", "path": "/notes/{nid}", "expect": {"status": 204}},
    ]},
}

_SQLITE_MEMORY_ENGINE_RE = re.compile(
    r'engine = create_engine\("sqlite://", connect_args=\{"check_same_thread": False\}, poolclass=StaticPool\)'
)
_SQLITE_FILE_ENGINE_RE = re.compile(
    r'engine = create_engine\("sqlite:///\./test\.db", connect_args=\{"check_same_thread": False\}\)'
)
_STATICPOOL_IMPORT_RE = re.compile(r'from sqlalchemy\.pool import StaticPool\n')


def rewrite_for_postgres(code: str, db_url_placeholder: str) -> str:
    """Swap the SQLite engine line for a Postgres one (env-var driven, falls
    back to db_url_placeholder), drop the SQLite-only StaticPool import.
    Business logic/models/routes untouched."""
    new_engine_line = (
        f'engine = create_engine(os.getenv("DATABASE_URL", {db_url_placeholder!r}))'
    )
    out = _SQLITE_MEMORY_ENGINE_RE.sub(new_engine_line, code)
    out = _SQLITE_FILE_ENGINE_RE.sub(new_engine_line, out)
    out = _STATICPOOL_IMPORT_RE.sub('', out)
    if "import os" not in out:
        out = "import os\n" + out
    assert "sqlite" not in out.lower(), "rewrite left a sqlite reference behind"
    assert "check_same_thread" not in out, "rewrite left check_same_thread behind"
    assert "StaticPool" not in out, "rewrite left StaticPool behind"
    return out


def main():
    lines = [json.loads(l) for l in PAIRS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]

    pg_data_dir = tempfile.mkdtemp(prefix="pgverify_")
    print(f"Starting embedded Postgres in {pg_data_dir} ...")
    server = pgserver.get_server(pg_data_dir)
    base_uri = server.get_uri()  # postgresql://postgres:@127.0.0.1:PORT/postgres
    print(f"Postgres running: {base_uri}")

    admin_conn = psycopg2.connect(base_uri)
    admin_conn.autocommit = True
    admin_cur = admin_conn.cursor()

    results = {}
    rewritten_code = {}
    try:
        for idx in DB_ROW_INDICES:
            row = lines[idx]
            db_name = f"verifyrow{idx}"
            admin_cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
            admin_cur.execute(f"CREATE DATABASE {db_name}")
            row_db_url = base_uri.rsplit("/", 1)[0] + f"/{db_name}"

            new_code = rewrite_for_postgres(row["code"], row_db_url)
            rewritten_code[idx] = new_code

            import os as _os
            _os.environ["DATABASE_URL"] = row_db_url
            passed, detail = run_eval(new_code, {"check_type": "http_sequence", "check_spec": CHECK_SPECS[idx]})
            results[idx] = (passed, detail)
            print(f"[{'PASS' if passed else 'FAIL'}] row {idx}: {row['task'][:60]}...  -> {detail}")
    finally:
        server.cleanup()
        print("Postgres stopped, data dir will be cleaned up by OS temp policy.")

    all_passed = all(p for p, _ in results.values())
    print("\nALL PASSED" if all_passed else "\nSOME FAILED")

    if all_passed:
        out_path = Path(__file__).resolve().parent / "postgres_rewritten_code.json"
        out_path.write_text(json.dumps({str(k): v for k, v in rewritten_code.items()}, indent=2), encoding="utf-8")
        print(f"Rewritten code saved to {out_path} for the append step.")

    return all_passed


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
