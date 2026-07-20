"""Step-4 re-verification: take a sample of RESHAPED pairs, parse their `output`
with the real orchestrator parser, reconstruct the file, and actually execute it
under FastAPI TestClient to confirm the delimited reshape didn't corrupt/truncate
anything. Runs in the data-prep venv (has fastapi); vendors only the tiny regex so
we don't need openai here — but the full-dataset byte-identity proof already ran
against the genuine extract_files in reshape_to_contract.py."""
import importlib.util
import json
import re
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

HERE = Path(__file__).resolve().parent

# Same regex as orchestrator/llm_client.py FILE_BLOCK_RE (kept in sync).
FILE_BLOCK_RE = re.compile(
    r"---\s*FILE:\s*(?P<path>[^\n\r-]+?)\s*---\r?\n(?P<content>.*?)\r?\n?---\s*END\s*---",
    re.DOTALL,
)


def parse_files(text):
    return [{"path": m.group("path").strip(), "content": m.group("content")} for m in FILE_BLOCK_RE.finditer(text)]


def load_module_from_code(code, name):
    mod = types.ModuleType(name)
    mod.__dict__["__name__"] = name
    sys.modules[name] = mod
    exec(compile(code, f"<{name}>", "exec"), mod.__dict__)
    return mod


def main():
    rows = [json.loads(l) for l in (HERE / "fastapi-backend-pairs-v2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    # Sample across categories: first of each category, capped at 8.
    seen, sample = set(), []
    for i, r in enumerate(rows):
        if r["category"] not in seen:
            seen.add(r["category"])
            sample.append((i, r))
        if len(sample) >= 8:
            break

    ok = 0
    for idx, r in sample:
        files = parse_files(r["output"])
        assert len(files) == 1, f"line {idx}: expected 1 file, got {len(files)}"
        # Corruption checks: parsed content must equal preserved original code.
        assert files[0]["content"] == r["code"], f"line {idx}: parsed != original code"
        assert "---FILE:" not in files[0]["content"], f"line {idx}: delimiter leaked into content"
        assert "---END---" not in files[0]["content"], f"line {idx}: END leaked into content"

        # Execute the reconstructed app.
        mod = load_module_from_code(files[0]["content"], f"reshaped_{idx}")
        app = getattr(mod, "app", None)
        assert app is not None, f"line {idx}: reconstructed module has no `app`"
        client = TestClient(app)
        # Smoke: the app instantiates and the router is mounted (openapi always 200).
        resp = client.get("/openapi.json")
        assert resp.status_code == 200, f"line {idx}: openapi not served ({resp.status_code})"
        n_routes = len(app.routes)
        print(f"  [OK] line {idx:>2} [{r['category']:<20}] {len(files)} file, {n_routes} routes, executes clean")
        ok += 1

    print(f"\n[PASS] {ok}/{len(sample)} sampled reshaped pairs parse (real delimiters), reconstruct byte-identical, and execute.")


if __name__ == "__main__":
    main()
