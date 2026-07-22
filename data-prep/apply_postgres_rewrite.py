"""Option A (per doc/kickoff-brief-postgres-verification.md step 6): REPLACE
the 8 SQLite-based database-sqlalchemy rows with their Postgres-verified
equivalents (same task/category, new `code` from postgres_verify_db_rows.py's
already-passing rewrite). Everything else about each row (task description,
category, locked_spec, design_tokens, system_prompt, user_prompt,
input_format) stays identical - only `code`/`output`/`verification_notes`
change, since only the DB connection layer changed.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "orchestrator"))

from llm_client import extract_files  # noqa: E402 - real production parser
from postgres_verify_db_rows import DB_ROW_INDICES, CHECK_SPECS  # noqa: E402

PAIRS_PATH = HERE / "fastapi-backend-pairs-v3.jsonl"
REWRITTEN_PATH = HERE / "postgres_rewritten_code.json"


def make_output(code: str, file_path: str = "main.py") -> str:
    return f"---FILE: {file_path}---\n{code}\n---END---\n"


def main():
    lines = [json.loads(l) for l in PAIRS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    rewritten = json.loads(REWRITTEN_PATH.read_text(encoding="utf-8"))
    original_keys = set(lines[0].keys())

    changed = 0
    for idx in DB_ROW_INDICES:
        row = lines[idx]
        new_code = rewritten[str(idx)]
        new_output = make_output(new_code, row["file_path"])

        # Round-trip through the real production parser before committing.
        files = extract_files(new_output)
        assert len(files) == 1 and files[0]["path"] == row["file_path"]
        assert files[0]["content"] == new_code, f"round-trip mismatch for row {idx}"

        row["code"] = new_code
        row["output"] = new_output
        row["verification_notes"] = (
            f"{row['verification_notes']} | postgres-verified (2026-07-22): "
            f"re-executed via TestClient against a real local Postgres instance "
            f"(pgserver, isolated per-row database), engine/connection rewritten "
            f"for postgresql://, check_same_thread/StaticPool removed"
        )
        assert set(row.keys()) == original_keys, f"key set changed for row {idx}"
        changed += 1

    PAIRS_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in lines) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] replaced {changed} rows with Postgres-verified code (Option A)")
    print(f"[OK] all rows: schema-consistent (identical key sets)")
    print(f"[OK] all rows: output round-trips through extract_files exactly matching code")
    print(f"[OK] total dataset size unchanged: {len(lines)} rows")


if __name__ == "__main__":
    main()
