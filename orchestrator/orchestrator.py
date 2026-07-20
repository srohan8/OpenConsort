"""Minimal fixed-pipeline orchestrator: Planning -> Design -> Backend (-> Frontend).

Each stage: one direct input, one direct output, validated against a JSON schema.
No tool-calling loop, no ReAct protocol, no shared "team" LLM config - deliberately
the opposite shape of MetaGPT's RoleZero architecture (see doc/phase1-patch-report.md
for why that mattered).
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

import jsonschema


def _load_dotenv():
    """Minimal .env loader (no dependency): reads KEY=VALUE lines from the
    repo-root .env into os.environ if not already set."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


_load_dotenv()

from llm_client import StageLLM, extract_files, extract_json

ROOT = Path(__file__).parent
SCHEMAS = ROOT / "schemas"
LOGS = ROOT / "logs"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


def validate(data: dict, schema_name: str, stage: str):
    schema = load_schema(schema_name)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise SystemExit(
            f"[{stage}] output failed schema validation ({schema_name}): {e.message}\n"
            f"Path: {list(e.path)}\nOffending output:\n{json.dumps(data, indent=2)[:2000]}"
        )


def log_stage(run_id: str, stage: str, system_prompt: str, user_prompt: str, raw_output: str, parsed: dict):
    LOGS.mkdir(exist_ok=True)
    path = LOGS / f"{run_id}_{stage}.json"
    path.write_text(
        json.dumps(
            {
                "stage": stage,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "raw_output": raw_output,
                "parsed_output": parsed,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  -> logged to {path}")


def run_stage(run_id: str, stage: str, llm: StageLLM, system_prompt: str, user_prompt: str, schema_name: str) -> dict:
    print(f"[{stage}] calling {llm.model} @ {llm.client.base_url} ...")
    raw = llm.complete(system_prompt, user_prompt)
    try:
        parsed = extract_json(raw)
    except ValueError as e:
        log_stage(run_id, stage, system_prompt, user_prompt, raw, {"__parse_error__": str(e)})
        raise SystemExit(f"[{stage}] failed to extract JSON from model output: {e}")
    log_stage(run_id, stage, system_prompt, user_prompt, raw, parsed)
    if schema_name:
        validate(parsed, schema_name, stage)
    print(f"[{stage}] OK - schema-valid output produced.")
    return parsed


def run_code_stage(run_id: str, stage: str, llm: StageLLM, system_prompt: str, user_prompt: str, spec_version: int) -> dict:
    """Like run_stage, but for code-bearing stages: parses the delimited-text
    ---FILE:.../---END--- format instead of a JSON string field. See CONTRACT.md.
    stage/spec_version are supplied by the orchestrator, not the model."""
    print(f"[{stage}] calling {llm.model} @ {llm.client.base_url} ...")
    raw = llm.complete(system_prompt, user_prompt)
    try:
        files = extract_files(raw)
    except ValueError as e:
        log_stage(run_id, stage, system_prompt, user_prompt, raw, {"__parse_error__": str(e)})
        raise SystemExit(f"[{stage}] failed to extract file blocks from model output: {e}")
    parsed = {"stage": stage, "spec_version": spec_version, "files": files}
    log_stage(run_id, stage, system_prompt, user_prompt, raw, parsed)
    validate(parsed, "code_output.schema.json", stage)
    print(f"[{stage}] OK - {len(files)} file(s) parsed and schema-valid.")
    return parsed


PLANNING_SYSTEM = """You are the Planning specialist in a fixed software-build pipeline.
Given a one-line product idea, produce a LockedSpec and a UserFlow.
Respond with a single JSON object with exactly two top-level keys: "locked_spec" and "user_flow".
"locked_spec" must match this schema:
{locked_spec_schema}
"user_flow" must match this schema:
{user_flow_schema}
Both must use spec_version/version = 1. Output ONLY the JSON object, no other prose, no markdown fences."""

DESIGN_SYSTEM = """You are the Design specialist in a fixed software-build pipeline.
Given a LockedSpec and UserFlow, produce DesignTokens matching this schema:
{design_tokens_schema}
Output ONLY a single JSON object matching that schema, no other prose, no markdown fences."""

BACKEND_SYSTEM = """You are the Backend specialist in a fixed software-build pipeline.
Given a LockedSpec and DesignTokens, write the backend code for this app.

Respond using this EXACT delimited plain-text format - NOT JSON, no escaping of any kind.
Write your code exactly as it should appear in the file, including real newlines and quotes:

---FILE: <the real path you choose, e.g. app.py>---
<the file's full content, written normally, no escaping>
---END---

You may include more than one file by repeating the block with a different real path.

Concrete example (illustrative only - use your OWN real filename and implementation,
do not copy this example's filename or content):
---FILE: example_placeholder_name.py---
def hello():
    print("hi")

hello()
---END---

Output ONLY these ---FILE:---/---END--- blocks (one or more). Keep the implementation
simple and correct - a single main file is fine for a small app. Implement the features
listed in the LockedSpec, not just a placeholder/stub."""


def build_stage_llms(use_ollama_for_backend: bool) -> dict:
    cloud = dict(
        base_url=os.getenv("CLOUD_BASE_URL", "http://localhost:20128/v1"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("CLOUD_MODEL", "My-combo"),
    )
    stages = {
        "planning": StageLLM("planning", **cloud),
        "design": StageLLM("design", **cloud),
    }
    if use_ollama_for_backend:
        stages["backend"] = StageLLM(
            "backend", base_url="http://localhost:11434/v1", api_key="ollama", model="qwen2.5-coder:1.5b"
        )
    else:
        stages["backend"] = StageLLM("backend", **cloud)
    return stages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("idea", help="one-line product idea")
    parser.add_argument("--ollama-backend", action="store_true", help="route Backend stage to local Ollama")
    args = parser.parse_args()

    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ("_ollama" if args.ollama_backend else "_cloud")
    stages = build_stage_llms(args.ollama_backend)

    locked_spec_schema = load_schema("locked_spec.schema.json")
    user_flow_schema = load_schema("user_flow.schema.json")
    design_tokens_schema = load_schema("design_tokens.schema.json")

    planning_out = run_stage(
        run_id,
        "planning",
        stages["planning"],
        PLANNING_SYSTEM.format(
            locked_spec_schema=json.dumps(locked_spec_schema),
            user_flow_schema=json.dumps(user_flow_schema),
        ),
        f"Product idea: {args.idea}",
        None,
    )
    # planning_out is {"locked_spec": ..., "user_flow": ...} - validate each half separately
    validate(planning_out["locked_spec"], "locked_spec.schema.json", "planning.locked_spec")
    validate(planning_out["user_flow"], "user_flow.schema.json", "planning.user_flow")
    locked_spec = planning_out["locked_spec"]
    user_flow = planning_out["user_flow"]

    design_out = run_stage(
        run_id,
        "design",
        stages["design"],
        DESIGN_SYSTEM.format(design_tokens_schema=json.dumps(design_tokens_schema)),
        f"LockedSpec:\n{json.dumps(locked_spec)}\n\nUserFlow:\n{json.dumps(user_flow)}",
        "design_tokens.schema.json",
    )

    backend_out = run_code_stage(
        run_id,
        "backend",
        stages["backend"],
        BACKEND_SYSTEM,
        f"LockedSpec:\n{json.dumps(locked_spec)}\n\nDesignTokens:\n{json.dumps(design_out)}",
        spec_version=locked_spec["version"],
    )

    print("\n=== Pipeline complete ===")
    print(f"Backend produced {len(backend_out['files'])} file(s):")
    for f in backend_out["files"]:
        print(f"  - {f['path']} ({len(f['content'])} chars)")

    out_dir = ROOT / "generated" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in backend_out["files"]:
        target = out_dir / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"], encoding="utf-8")
    print(f"Files written to {out_dir}")


if __name__ == "__main__":
    main()
