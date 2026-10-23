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
from openspec_bridge import requirements_text, write_change
from planning_format import PLANNING_SYSTEM, parse_plan
from retrieval import Retriever, examples_text

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

FRONTEND_SYSTEM = """You are the Frontend specialist in a fixed software-build pipeline.
Given a LockedSpec, DesignTokens, and UserFlow, write the frontend code for this app,
using the frontend stack specified in LockedSpec.stack.frontend (e.g. React + Vite).

Respond using this EXACT delimited plain-text format - NOT JSON, no escaping of any kind.
Write your code exactly as it should appear in each file, including real newlines and quotes:

---FILE: <the real path you choose, e.g. src/App.jsx>---
<the file's full content, written normally, no escaping>
---END---

You may include more than one file by repeating the block with a different real path
(e.g. one component per screen in UserFlow, plus an entry point / router file).

Concrete example (illustrative only - use your OWN real filename and implementation,
do not copy this example's filename or content):
---FILE: example_placeholder_component.jsx---
export default function Example() {{
  return <div>hi</div>;
}}
---END---

Output ONLY these ---FILE:---/---END--- blocks (one or more). Build the actual screens
and navigation described in UserFlow (one component per screen is a reasonable default
for a small app) - implement the real flow, not a placeholder/stub, and apply the colors/
typography/spacing from DesignTokens where relevant."""


def run_planning(run_id: str, llm: StageLLM, idea: str, max_repairs: int = 2) -> tuple:
    """Planning stage: idea in, (locked_spec, user_flow, scenarios) out.

    The model writes plain labelled lines (planning_format.py); code builds the schema-valid
    LockedSpec/UserFlow. On a parse failure the error is fed back for up to `max_repairs` retries."""
    user_prompt = f"Product idea: {idea}"
    prompt = user_prompt
    for attempt in range(max_repairs + 1):
        print(f"[planning] calling {llm.model} @ {llm.client.base_url} (attempt {attempt + 1}) ...")
        raw = llm.complete(PLANNING_SYSTEM, prompt)
        try:
            locked_spec, user_flow, scenarios = parse_plan(raw)
        except ValueError as e:
            log_stage(run_id, f"planning_try{attempt + 1}", PLANNING_SYSTEM, prompt, raw, {"__parse_error__": str(e)})
            if attempt == max_repairs:
                raise SystemExit(f"[planning] could not produce a valid plan after {attempt + 1} tries: {e}")
            prompt = (
                f"{user_prompt}\n\nYour previous answer was rejected: {e}\n"
                "Try again using ONLY the labelled lines."
            )
            continue
        log_stage(run_id, "planning", PLANNING_SYSTEM, prompt, raw, {"locked_spec": locked_spec, "user_flow": user_flow})
        validate(locked_spec, "locked_spec.schema.json", "planning.locked_spec")
        validate(user_flow, "user_flow.schema.json", "planning.user_flow")
        print("[planning] OK - plan parsed and schema-valid.")
        return locked_spec, user_flow, scenarios


def build_stage_llms(use_ollama_for_backend: bool, use_ollama_for_frontend: bool) -> dict:
    cloud = dict(
        base_url=os.getenv("CLOUD_BASE_URL", "http://localhost:20128/v1"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("CLOUD_MODEL", "My-combo"),
    )
    ollama = dict(base_url="http://localhost:11434/v1", api_key="ollama", model="qwen2.5-coder:1.5b")
    # PLANNING_MODEL (e.g. "gemma3:1b") routes Planning to local Ollama instead of the cloud proxy.
    planning_model = os.getenv("PLANNING_MODEL")
    if planning_model:
        planning = StageLLM("planning", **{**ollama, "model": planning_model})
    else:
        planning = StageLLM("planning", **cloud)
    stages = {
        "planning": planning,
        "design": StageLLM("design", **cloud),
    }
    stages["backend"] = StageLLM("backend", **(ollama if use_ollama_for_backend else cloud))
    stages["frontend"] = StageLLM("frontend", **(ollama if use_ollama_for_frontend else cloud))
    return stages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("idea", help="one-line product idea")
    parser.add_argument("--ollama-backend", action="store_true", help="route Backend stage to local Ollama")
    parser.add_argument("--ollama-frontend", action="store_true", help="route Frontend stage to local Ollama")
    parser.add_argument(
        "--openspec",
        action="store_true",
        help="write an OpenSpec change folder with the generated files and feed its requirements to Backend/Frontend",
    )
    parser.add_argument(
        "--retrieve",
        type=int,
        default=0,
        metavar="K",
        help="add the K most similar verified FastAPI examples to the Backend prompt (0 = off)",
    )
    args = parser.parse_args()

    suffix = "_ollama" if (args.ollama_backend or args.ollama_frontend) else "_cloud"
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + suffix
    stages = build_stage_llms(args.ollama_backend, args.ollama_frontend)

    design_tokens_schema = load_schema("design_tokens.schema.json")

    locked_spec, user_flow, scenarios = run_planning(run_id, stages["planning"], args.idea)

    spec_context = f"\n\n{requirements_text(locked_spec, user_flow, scenarios)}" if args.openspec else ""

    design_out = run_stage(
        run_id,
        "design",
        stages["design"],
        DESIGN_SYSTEM.format(design_tokens_schema=json.dumps(design_tokens_schema)),
        f"LockedSpec:\n{json.dumps(locked_spec)}\n\nUserFlow:\n{json.dumps(user_flow)}",
        "design_tokens.schema.json",
    )

    retrieved = ""
    if args.retrieve and "fastapi" in locked_spec["stack"]["backend"].lower():
        rows = Retriever.from_pairs().search(" ".join(locked_spec["features"]), args.retrieve)
        retrieved = f"\n\n{examples_text(rows)}" if rows else ""
        print(f"[backend] retrieval: added {len(rows)} example(s)")

    backend_out = run_code_stage(
        run_id,
        "backend",
        stages["backend"],
        BACKEND_SYSTEM,
        f"LockedSpec:\n{json.dumps(locked_spec)}\n\nDesignTokens:\n{json.dumps(design_out)}{spec_context}{retrieved}",
        spec_version=locked_spec["version"],
    )

    frontend_out = run_code_stage(
        run_id,
        "frontend",
        stages["frontend"],
        FRONTEND_SYSTEM,
        f"LockedSpec:\n{json.dumps(locked_spec)}\n\n"
        f"DesignTokens:\n{json.dumps(design_out)}\n\n"
        f"UserFlow:\n{json.dumps(user_flow)}{spec_context}",
        spec_version=locked_spec["version"],
    )

    print("\n=== Pipeline complete ===")
    out_dir = ROOT / "generated" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    for stage_name, stage_out in (("backend", backend_out), ("frontend", frontend_out)):
        print(f"{stage_name.capitalize()} produced {len(stage_out['files'])} file(s):")
        for f in stage_out["files"]:
            print(f"  - {f['path']} ({len(f['content'])} chars)")
            target = out_dir / f["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f["content"], encoding="utf-8")
    print(f"Files written to {out_dir}")
    if args.openspec:
        change = write_change(out_dir, args.idea, locked_spec, user_flow, scenarios=scenarios)
        print(f"OpenSpec change written to {change}")


if __name__ == "__main__":
    main()
