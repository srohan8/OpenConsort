"""Reshape the verified FastAPI training data to match the finalized
delimited-text code-bearing contract (orchestrator/CONTRACT.md).

Contract format for code output (what the Backend specialist must emit):

    ---FILE: <path>---
    <raw, unescaped code>
    ---END---

Verification is done with the REAL orchestrator parser (extract_files /
FILE_BLOCK_RE from orchestrator/llm_client.py), so "reshaped correctly" means
"the production parser reconstructs the original code byte-for-byte."

Reads:  fastapi-backend-pairs.jsonl  (71 verified pairs)
        fastapi-eval-suite.jsonl     (31 held-out tasks)
Writes: fastapi-backend-pairs-v2.jsonl
        fastapi-eval-suite-v2.jsonl
Originals are never modified.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ORCH = REPO / "orchestrator"

# Use the production parser as the source of truth for "did the reshape survive".
sys.path.insert(0, str(ORCH))
from llm_client import extract_files  # noqa: E402  (real orchestrator parser)

CONTRACT_TAG = "delimited-text-v1"
# Single-file FastAPI apps -> conventional entrypoint name. The schema's own
# example uses 'main.py'; BACKEND_SYSTEM lets the model choose its own path.
DEFAULT_PATH = "main.py"


def to_delimited(code: str, path: str = DEFAULT_PATH) -> str:
    """Wrap raw code in one ---FILE:---/---END--- block. Constructed so the
    production regex round-trips to the original `code` exactly (the optional
    \\n? before ---END--- absorbs the separator we add)."""
    return f"---FILE: {path}---\n{code}\n---END---\n"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_jsonl(rows: list[dict], path: Path) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def reshape_backend(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Add the contract-shaped `output` completion to each pair, preserving the
    original raw `code` for provenance/rollback. Returns (new_rows, failures)."""
    out, failures = [], []
    for i, r in enumerate(rows):
        code = r["code"]
        block = to_delimited(code, DEFAULT_PATH)

        # Verify with the REAL parser: must reconstruct exactly one file whose
        # content is byte-identical to the original code, at the chosen path.
        parsed = extract_files(block)
        if len(parsed) != 1:
            failures.append(f"line {i}: parser returned {len(parsed)} files, expected 1")
        elif parsed[0]["path"] != DEFAULT_PATH:
            failures.append(f"line {i}: path mismatch {parsed[0]['path']!r}")
        elif parsed[0]["content"] != code:
            failures.append(f"line {i}: content NOT byte-identical after round-trip")

        new = dict(r)  # preserve every original field (lossless)
        new["output"] = block            # contract-shaped completion (training target)
        new["file_path"] = DEFAULT_PATH
        new["contract_format"] = CONTRACT_TAG
        out.append(new)
    return out, failures


def reshape_eval(rows: list[dict]) -> list[dict]:
    """Eval tasks carry NO reference code payload (only a runtime check_spec),
    so there is nothing to re-delimit. Per the brief, check_spec is left fully
    intact; we only tag the output-format framing so the eval harness knows the
    model is expected to answer in delimited-text contract form."""
    out = []
    for r in rows:
        new = dict(r)
        new["contract_format"] = CONTRACT_TAG
        # keep task and check_spec byte-identical
        out.append(new)
    return out


def main():
    bp = HERE / "fastapi-backend-pairs.jsonl"
    ep = HERE / "fastapi-eval-suite.jsonl"
    backend = load_jsonl(bp)
    eval_rows = load_jsonl(ep)

    new_backend, failures = reshape_backend(backend)
    new_eval = reshape_eval(eval_rows)

    # Losslessness assertions (hard-fail, don't silently write a bad file).
    assert len(new_backend) == len(backend), "backend pair count changed!"
    assert len(new_eval) == len(eval_rows), "eval task count changed!"
    for orig, new in zip(backend, new_backend):
        assert new["code"] == orig["code"], "original code field mutated!"
        assert new["task"] == orig["task"], "task field mutated!"
    for orig, new in zip(eval_rows, new_eval):
        assert new["check_spec"] == orig["check_spec"], "check_spec mutated!"
        assert new["task"] == orig["task"], "eval task mutated!"

    if failures:
        print(f"[FAIL] {len(failures)} round-trip failures:")
        for f in failures[:20]:
            print("   ", f)
        raise SystemExit(1)

    dump_jsonl(new_backend, HERE / "fastapi-backend-pairs-v2.jsonl")
    dump_jsonl(new_eval, HERE / "fastapi-eval-suite-v2.jsonl")

    print(f"[OK] backend: {len(new_backend)} pairs reshaped, all round-trip byte-identical via real parser")
    print(f"[OK] eval:    {len(new_eval)} tasks tagged, check_spec + task left intact")
    print(f"[OK] wrote fastapi-backend-pairs-v2.jsonl and fastapi-eval-suite-v2.jsonl")
    print(f"[OK] originals untouched")


if __name__ == "__main__":
    main()
