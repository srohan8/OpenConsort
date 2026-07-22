"""Reshape the verified Round 2 examples (round2_examples.py) into the exact
fastapi-backend-pairs-v3.jsonl row schema and append them.

Reuses the same ground-truth helpers as reshape_to_orchestrator_input.py
(make_locked_spec, build_user_prompt, PLACEHOLDER_DESIGN_TOKENS, imported
BACKEND_SYSTEM + schemas) so the new rows cannot drift from the existing
71/82 rows' shape.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ORCH = REPO / "orchestrator"
sys.path.insert(0, str(ORCH))
sys.path.insert(0, str(HERE))

import jsonschema  # noqa: E402
from orchestrator import BACKEND_SYSTEM, load_schema  # noqa: E402
from llm_client import extract_files  # noqa: E402
from reshape_to_orchestrator_input import (  # noqa: E402
    make_locked_spec,
    build_user_prompt,
    PLACEHOLDER_DESIGN_TOKENS,
    INPUT_FORMAT_TAG,
)
from round2_examples import EXAMPLES  # noqa: E402
from eval_runner import run_eval  # noqa: E402

LOCKED_SPEC_SCHEMA = load_schema("locked_spec.schema.json")
DESIGN_TOKENS_SCHEMA = load_schema("design_tokens.schema.json")

PAIRS_PATH = HERE / "fastapi-backend-pairs-v3.jsonl"


def make_output(code: str, file_path: str = "main.py") -> str:
    return f"---FILE: {file_path}---\n{code}\n---END---\n"


def build_row(example: dict) -> dict:
    task = example["task"]
    code = example["code"]
    file_path = "main.py"
    output = make_output(code, file_path)

    # Round-trip through the REAL production parser before anything else -
    # if this doesn't match, the row would train the model on a shape that
    # doesn't actually round-trip in production.
    files = extract_files(output)
    assert len(files) == 1, f"expected 1 file, got {len(files)}"
    assert files[0]["path"] == file_path
    assert files[0]["content"] == code, (
        f"round-trip mismatch for task {task[:50]!r}:\n"
        f"expected: {code!r}\ngot:      {files[0]['content']!r}"
    )

    # Re-verify against check_spec one more time here (belt and suspenders -
    # already verified in the previous step, but this script is the one that
    # actually commits to the dataset, so it re-asserts independently).
    passed, detail = run_eval(code, {"check_type": "http_sequence", "check_spec": example["check_spec"]})
    assert passed, f"verification failed at append time for task {task[:50]!r}: {detail}"

    locked_spec = make_locked_spec(task)
    design_tokens = PLACEHOLDER_DESIGN_TOKENS
    jsonschema.validate(locked_spec, LOCKED_SPEC_SCHEMA)
    jsonschema.validate(design_tokens, DESIGN_TOKENS_SCHEMA)
    user_prompt = build_user_prompt(locked_spec, design_tokens)

    return {
        "task": task,
        "code": code,
        "category": example["category"],
        "verified": True,
        "verification_notes": f"round2: {detail}",
        "output": output,
        "file_path": file_path,
        "contract_format": "delimited-text-v1",
        "system_prompt": BACKEND_SYSTEM,
        "locked_spec": locked_spec,
        "design_tokens": design_tokens,
        "user_prompt": user_prompt,
        "input_format": INPUT_FORMAT_TAG,
    }


def main():
    existing = [json.loads(l) for l in PAIRS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    existing_keys = set(existing[0].keys())

    new_rows = [build_row(ex) for ex in EXAMPLES]

    for row in new_rows:
        assert set(row.keys()) == existing_keys, (
            f"key mismatch: new={set(row.keys()) ^ existing_keys}"
        )

    all_rows = existing + new_rows
    PAIRS_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_rows) + "\n",
        encoding="utf-8",
    )

    by_category = {}
    for r in new_rows:
        by_category.setdefault(r["category"], 0)
        by_category[r["category"]] += 1

    print(f"[OK] {len(existing)} existing + {len(new_rows)} new = {len(all_rows)} total rows")
    print(f"[OK] all new rows: schema-consistent with existing rows (identical key sets)")
    print(f"[OK] all new rows: output round-trips through extract_files exactly matching code")
    print(f"[OK] all new rows: re-verified via TestClient against check_spec at append time")
    print("\nNew rows by category:")
    for cat, count in sorted(by_category.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
