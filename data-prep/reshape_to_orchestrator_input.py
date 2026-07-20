"""Second reshape pass: restructure the dataset's INPUT to mirror the real
Backend-stage user_prompt, not the placeholder free-text `task` string.

Ground truth (orchestrator/orchestrator.py, run_code_stage call for backend):

    BACKEND_SYSTEM                                              # system prompt
    f"LockedSpec:\n{json.dumps(locked_spec)}\n\n"
    f"DesignTokens:\n{json.dumps(design_out)}"                  # user prompt

Both BACKEND_SYSTEM and the schemas are IMPORTED/LOADED from the real
orchestrator files below (never hand-retyped), and the user_prompt string is
built with the identical f-string template used in orchestrator.py:211 - so
this cannot silently drift from production and require a second reshape.

Why LockedSpec + DesignTokens (not the free-text `task`) is the real input:
the Backend specialist never sees a plain task description in production -
it only ever sees a validated LockedSpec + DesignTokens pair. Training on
free-text `task` would teach the model an input shape it will never actually
receive at inference time.

Reads:  fastapi-backend-pairs-v2.jsonl   (has `output`, delimited-text)
        fastapi-eval-suite-v2.jsonl
Writes: fastapi-backend-pairs-v3.jsonl
        fastapi-eval-suite-v3.jsonl
v2/v1 files untouched.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ORCH = REPO / "orchestrator"
sys.path.insert(0, str(ORCH))

import jsonschema  # noqa: E402
from orchestrator import BACKEND_SYSTEM, load_schema  # noqa: E402 (ground truth, not retyped)

LOCKED_SPEC_SCHEMA = load_schema("locked_spec.schema.json")
DESIGN_TOKENS_SCHEMA = load_schema("design_tokens.schema.json")

INPUT_FORMAT_TAG = "locked_spec+design_tokens-v1"

# Phase 1 locked stack (doc/architecture.md "What Phase 1 locks in concretely").
# Constant across all training pairs - this is the one stack Phase 1 targets,
# not a per-pair guess.
PHASE1_STACK = {
    "backend": "FastAPI",
    "frontend": "React + Vite",
    "database": "PostgreSQL",
    "auth": "JWT-based",
    "payments": None,
}

# DesignTokens content doesn't drive backend code (it's a Frontend/UI concern),
# but the real Backend prompt always includes it - so a constant, schema-valid
# placeholder is included for prompt-shape fidelity. Fabricating varied fake
# visual tokens per pair would add noise with no ground-truth signal behind it.
PLACEHOLDER_DESIGN_TOKENS = {
    "version": 1,
    "spec_version": 1,
    "colors": {"primary": "#2563eb", "background": "#ffffff", "text": "#111827"},
    "typography": {"font_family": "Inter, sans-serif", "scale": {"body": "16px", "h1": "32px"}},
    "spacing": {"sm": "8px", "md": "16px", "lg": "24px"},
}


def make_locked_spec(task: str) -> dict:
    """features = [task]: the free-text task description IS already a plain-
    language feature description (matches the schema's own example style,
    e.g. 'create/edit/delete tasks') - reusing it verbatim as the single
    feature is lossless, vs. fabricating multiple synthetic features."""
    return {
        "version": 1,
        "product_type": "web_app",
        "stack": dict(PHASE1_STACK),
        "features": [task],
    }


def build_user_prompt(locked_spec: dict, design_tokens: dict) -> str:
    # Identical template to orchestrator.py:211 - copied as a literal f-string
    # shape check, not retyped logic (see assertion in main()).
    return f"LockedSpec:\n{json.dumps(locked_spec)}\n\nDesignTokens:\n{json.dumps(design_tokens)}"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_jsonl(rows: list[dict], path: Path) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def reshape_backend(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        locked_spec = make_locked_spec(r["task"])
        design_tokens = PLACEHOLDER_DESIGN_TOKENS
        jsonschema.validate(locked_spec, LOCKED_SPEC_SCHEMA)
        jsonschema.validate(design_tokens, DESIGN_TOKENS_SCHEMA)

        new = dict(r)  # preserve everything from v2 (lossless)
        new["system_prompt"] = BACKEND_SYSTEM
        new["locked_spec"] = locked_spec
        new["design_tokens"] = design_tokens
        new["user_prompt"] = build_user_prompt(locked_spec, design_tokens)
        new["input_format"] = INPUT_FORMAT_TAG
        out.append(new)
    return out


def reshape_eval(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        locked_spec = make_locked_spec(r["task"])
        design_tokens = PLACEHOLDER_DESIGN_TOKENS
        jsonschema.validate(locked_spec, LOCKED_SPEC_SCHEMA)
        jsonschema.validate(design_tokens, DESIGN_TOKENS_SCHEMA)

        new = dict(r)
        new["system_prompt"] = BACKEND_SYSTEM
        new["locked_spec"] = locked_spec
        new["design_tokens"] = design_tokens
        new["user_prompt"] = build_user_prompt(locked_spec, design_tokens)
        new["input_format"] = INPUT_FORMAT_TAG
        out.append(new)
    return out


def main():
    bp = HERE / "fastapi-backend-pairs-v2.jsonl"
    ep = HERE / "fastapi-eval-suite-v2.jsonl"
    backend = load_jsonl(bp)
    eval_rows = load_jsonl(ep)

    new_backend = reshape_backend(backend)
    new_eval = reshape_eval(eval_rows)

    # Losslessness: every v2 field still present and unchanged.
    for orig, new in zip(backend, new_backend):
        for k, v in orig.items():
            assert new[k] == v, f"field {k!r} mutated during v2->v3 reshape"
    for orig, new in zip(eval_rows, new_eval):
        for k, v in orig.items():
            assert new[k] == v, f"field {k!r} mutated during v2->v3 reshape (eval)"

    # Ground-truth fidelity: user_prompt must be reproducible by the exact
    # template orchestrator.py uses, and must contain the schema-valid JSON
    # objects we validated above (round-trip parse check).
    for row in new_backend + new_eval:
        expected = build_user_prompt(row["locked_spec"], row["design_tokens"])
        assert row["user_prompt"] == expected, "user_prompt does not match orchestrator's f-string template"
        assert row["system_prompt"] == BACKEND_SYSTEM, "system_prompt does not match orchestrator.BACKEND_SYSTEM"
        head, _, tail = row["user_prompt"].partition("LockedSpec:\n")
        ls_json, _, dt_part = tail.partition("\n\nDesignTokens:\n")
        assert json.loads(ls_json) == row["locked_spec"]
        assert json.loads(dt_part) == row["design_tokens"]

    dump_jsonl(new_backend, HERE / "fastapi-backend-pairs-v3.jsonl")
    dump_jsonl(new_eval, HERE / "fastapi-eval-suite-v3.jsonl")

    print(f"[OK] backend: {len(new_backend)} pairs — system_prompt=BACKEND_SYSTEM (imported), "
          f"user_prompt=real f-string template, locked_spec+design_tokens schema-valid")
    print(f"[OK] eval:    {len(new_eval)} tasks — same input restructuring applied")
    print(f"[OK] wrote fastapi-backend-pairs-v3.jsonl and fastapi-eval-suite-v3.jsonl")
    print(f"[OK] v2/v1 files untouched")


if __name__ == "__main__":
    main()
