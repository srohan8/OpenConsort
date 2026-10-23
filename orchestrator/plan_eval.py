"""Planning quality eval: does a plan actually serve the idea, not just parse?

    python plan_eval.py gemma3:1b:single gemma3:1b:two_step

Each argument is MODEL:MODE (MODE = single | two_step). Runs every idea in IDEAS through
run_planning on a local Ollama model and prints per-plan checks plus a summary per config.
No LLM judge: every check is a deterministic rule.

Checks (a plan PASSES when all hold):
  coverage   >= 0.6 of the idea's key words appear somewhere in the plan
  modules    2-4 modules
  balanced   every module has >= 2 features and >= 1 screen
  not_invented  no generic module (Settings, Profile, ...) the idea did not mention
"""
import datetime
import re
import sys
import time

from llm_client import StageLLM
from orchestrator import run_planning

IDEAS = [
    "A food tracker to log meals and see my weekly calories",
    "A recipe app where I can save recipes and build a weekly meal plan",
    "A website for my dog walking business with pricing and a booking form",
    "A simple library app to track books I lent to friends",
    "A study planner for students with deadlines and reminders",
    "A habit tracker with daily check-ins and streaks",
    "An online bakery shop where customers order cakes for pickup",
    "A gym class booking app where members reserve spots",
    "A tool for freelancers to create invoices and track who has paid",
    "A plant watering reminder app with a garden dashboard",
]

GENERIC_WORDS = {
    "app", "simple", "website", "where", "with", "want", "that", "this", "and", "for", "from", "their",
    "into", "about", "build", "make", "create", "using", "user", "users", "can", "see", "web", "page",
    "tool", "who", "has", "who", "customers", "members",
}
# Generic module names are fine only when the idea gives a reason for them (any trigger word below).
_ACCOUNT_WORDS = ("account", "sign up", "signup", "sign in", "login", "log in", "member", "user", "profile", "register")
GENERIC_MODULES = {
    "settings": ("setting", "prefer", "config", "personali"),
    "profile": _ACCOUNT_WORDS,
    "user profile": _ACCOUNT_WORDS,
    "account": _ACCOUNT_WORDS,
    "accounts": _ACCOUNT_WORDS,
    "admin": ("admin", "owner", "manage", "staff"),
    "general": (),
    "misc": (),
    "other": (),
}


def _stem(word: str) -> str:
    return word[:5]


def key_terms(idea: str) -> set:
    return {_stem(w) for w in re.findall(r"[a-z]+", idea.lower()) if len(w) >= 4 and w not in GENERIC_WORDS}


def plan_text(spec: dict, flow: dict, scenarios: dict) -> str:
    parts = []
    for m in spec["modules"]:
        parts += [m["name"], m.get("title", "")]
    for f in spec["features"]:
        parts += [f, scenarios.get(f, {}).get("when", ""), scenarios.get(f, {}).get("then", "")]
    for s in flow["screens"]:
        parts += [s["name"], s["purpose"]]
    return " ".join(parts).lower()


def score(idea: str, spec: dict, flow: dict, scenarios: dict) -> dict:
    terms = key_terms(idea)
    tokens = {_stem(w) for w in re.findall(r"[a-z]+", plan_text(spec, flow, scenarios))}
    coverage = len(terms & tokens) / len(terms) if terms else 1.0
    idea_lower = idea.lower()
    modules = spec["modules"]
    unbalanced = [m["name"] for m in modules if len(m["features"]) < 2 or not m["screens"]]
    invented = [
        m["name"]
        for m in modules
        if m["name"].strip().lower() in GENERIC_MODULES
        and not any(w in idea_lower for w in GENERIC_MODULES[m["name"].strip().lower()])
    ]
    checks = {
        "coverage": coverage >= 0.6,
        "modules": 2 <= len(modules) <= 4,
        "balanced": not unbalanced,
        "not_invented": not invented,
    }
    return {"coverage": coverage, "checks": checks, "pass": all(checks.values()), "unbalanced": unbalanced, "invented": invented}


def make_llm(model: str) -> StageLLM:
    return StageLLM("planning", base_url="http://localhost:11434/v1", api_key="ollama", model=model)


def main(configs: list):
    summary = {}
    for config in configs:
        model, _, mode = config.rpartition(":")
        llm = make_llm(model)
        rows = []
        print(f"\n=== {model} / {mode} ===")
        for i, idea in enumerate(IDEAS):
            run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + f"_eval{i}"
            t = time.time()
            try:
                spec, flow, scenarios = run_planning(run_id, llm, idea, mode=mode)
            except SystemExit as e:
                rows.append({"ok": False, "secs": time.time() - t})
                print(f"FAIL  {time.time() - t:4.0f}s  {idea[:48]} :: {str(e)[:90]}")
                continue
            r = score(idea, spec, flow, scenarios)
            r.update(ok=True, secs=time.time() - t, modules=len(spec["modules"]))
            rows.append(r)
            flags = "".join(k[0].upper() if v else k[0] for k, v in r["checks"].items())
            print(f"{'PASS' if r['pass'] else 'weak'}  {r['secs']:4.0f}s  cov={r['coverage']:.2f} mods={r['modules']} [{flags}]  {idea[:48]}")
            if r["unbalanced"] or r["invented"]:
                print(f"      unbalanced={r['unbalanced']} invented={r['invented']}")
        n = len(rows)
        ok = [r for r in rows if r["ok"]]
        summary[config] = {
            "valid": f"{len(ok)}/{n}",
            "quality_pass": f"{sum(r['pass'] for r in ok)}/{n}",
            "mean_coverage": round(sum(r["coverage"] for r in ok) / max(len(ok), 1), 2),
            "mean_secs": round(sum(r["secs"] for r in rows) / n),
        }
    print("\n=== SUMMARY (flags: Coverage Modules Balanced Not_invented; capital = ok) ===")
    for config, s in summary.items():
        print(f"{config:28s} {s}")


def rescore_logs(labels: list):
    """Replay the FIRST raw output of every logged eval run through parse_plan with cleanup off
    and on, on identical outputs (no model calls). Runs are grouped into len(labels) configs of
    len(IDEAS) runs each, in time order. First attempts only, so repairs don't blur the comparison."""
    import json
    from pathlib import Path

    from planning_format import parse_plan

    logs = Path(__file__).parent / "logs"
    runs = {}  # run_id -> first-attempt log
    for path in sorted(logs.glob("*_eval*_planning*.json")):
        run_id = path.name.split("_planning")[0]
        data = json.loads(path.read_text(encoding="utf-8"))
        if run_id not in runs or "_try1" in path.name:
            runs[run_id] = data
    ordered = sorted(runs)
    for c, label in enumerate(labels):
        group = ordered[c * len(IDEAS):(c + 1) * len(IDEAS)]
        print(f"\n=== {label}: first attempts, {len(group)} runs ===")
        for tidy in (False, True):
            valid = passed = 0
            for run_id in group:
                data = runs[run_id]
                idea = re.findall(r"Product idea: (.+)", data["user_prompt"])[-1].strip()
                try:
                    spec, flow, scenarios = parse_plan(data["raw_output"], tidy=tidy)
                except ValueError:
                    continue
                valid += 1
                passed += score(idea, spec, flow, scenarios)["pass"]
            print(f"  cleanup={'on ' if tidy else 'off'}  valid {valid}/{len(group)}  quality-pass {passed}/{len(group)}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--rescore"]:
        rescore_logs(sys.argv[2:] or ["gemma3:1b single", "gemma3:1b two_step"])
    else:
        main(sys.argv[1:] or ["gemma3:1b:single", "gemma3:1b:two_step"])
