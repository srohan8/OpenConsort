"""Plain-content Planning format: the model writes simple labelled lines, code builds the
LockedSpec / UserFlow (and OpenSpec scenarios) from them.

A 1B model never has to produce JSON or OpenSpec headings. Modules group what follows them:
FEATURE and SCREEN lines belong to the most recent MODULE line.

    TYPE: web_app
    MODULE: Task management | Add, view and complete your to-dos
    FEATURE: Add a task | WHEN the user submits the add form | THEN the task appears in the list
    SCREEN: list | Task List | Shows all tasks
    FLOW: list -> add | click Add task
    STACK_BACKEND: FastAPI        (optional; defaults below)
"""
import re

PRODUCT_TYPES = ["web_app", "portfolio", "ecommerce", "blog", "internal_tool", "mobile_app"]
DEFAULT_STACK = {
    "backend": "FastAPI",
    "frontend": "React + Vite",
    "database": "SQLite",
    "auth": "none",
    "payments": None,
}
MIN_MODULES = 2
MIN_FEATURES = 3

PLANNING_SYSTEM = """You are the Planning specialist in a fixed software-build pipeline.
Turn the product idea into a plan using ONLY these labelled lines. No JSON, no markdown, no extra prose.

TYPE: one of web_app, portfolio, ecommerce, blog, internal_tool, mobile_app
MODULE: <module name> | <plain-English title for non-technical readers>
FEATURE: <short feature name> | WHEN <what the user does> | THEN <what the app does>
SCREEN: <short_id> | <Screen Name> | <what the screen is for>
FLOW: <from_id> -> <to_id> | <what the user does to move>

Rules:
- Write 2 to 4 MODULE lines. A module is one area of the app (for example accounts, the main task, reporting).
- Under each MODULE line write its 1 to 3 FEATURE lines, then the SCREEN lines for that module.
- 2 to 5 SCREEN lines in total. FLOW ids must be SCREEN ids you wrote. One line per item.
- Describe THIS idea. Do not copy the example."""

_LABEL = re.compile(
    r"^\s*(?:[-*\d.)]+\s*)?\**(TYPE|MODULE|FEATURE|SCREEN|FLOW|STACK_\w+)\**\s*:\s*(.+?)\s*$", re.IGNORECASE
)


def _clean_id(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.strip().lower()).strip("_")


def _clause(text: str, word: str) -> str:
    return re.sub(rf"^\s*{word}\s*[:\-]?\s*", "", text.strip(), flags=re.IGNORECASE)


MAX_MODULES = 4


def _merge_into(target: dict, source: dict):
    target["features"] += [f for f in source["features"] if f not in target["features"]]
    target["screens"] += [s for s in source["screens"] if s not in target["screens"]]


def _is_weak(module: dict) -> bool:
    return len(module["features"]) < 2 or not module["screens"]


def tidy_modules(modules: list) -> list:
    """Deterministic cleanup of the model's module split (small models split badly):
    1. merge modules that share a name,
    2. fold weak modules (< 2 features or no screen) into a neighbour,
    3. cap the count at MAX_MODULES by folding the smallest module into a neighbour.
    Never drops below MIN_MODULES. Features/screens are moved, never deleted."""
    merged = {}
    for m in modules:
        key = re.sub(r"\s+", " ", m["name"].strip().lower())
        if key in merged:
            _merge_into(merged[key], m)
        else:
            merged[key] = {**m, "features": list(m["features"]), "screens": list(m["screens"])}
    mods = list(merged.values())

    def fold(index: int):
        # into the previous module, or the next one when it is first
        target = mods[index - 1] if index > 0 else mods[1]
        _merge_into(target, mods[index])
        del mods[index]

    while len(mods) > MIN_MODULES:
        weak = [i for i, m in enumerate(mods) if _is_weak(m)]
        if not weak:
            break
        fold(min(weak, key=lambda i: len(mods[i]["features"]) + len(mods[i]["screens"])))
    while len(mods) > MAX_MODULES:
        fold(min(range(len(mods)), key=lambda i: len(mods[i]["features"]) + len(mods[i]["screens"])))
    return mods


def parse_plan(text: str, tidy: bool = True) -> tuple:
    """Return (locked_spec, user_flow, scenarios). locked_spec carries `features` (flat, for the
    existing schema) and `modules` [{name, title, features, screens}]. Raises ValueError with a
    message that is safe to feed back to the model as a repair instruction."""
    product_type = "web_app"
    modules, scenarios, screens, flows, stack = [], {}, [], [], dict(DEFAULT_STACK)
    current = None

    def module():
        nonlocal current
        if current is None:
            current = {"name": "General", "title": "General", "features": [], "screens": []}
            modules.append(current)
        return current

    for line in text.splitlines():
        m = _LABEL.match(line)
        if not m:
            continue
        label, body = m.group(1).upper(), m.group(2)
        parts = [p.strip() for p in body.split("|")]
        if label == "TYPE":
            value = _clean_id(body)
            product_type = value if value in PRODUCT_TYPES else "web_app"
        elif label == "MODULE":
            if not parts[0]:
                continue
            current = {"name": parts[0], "title": parts[1] if len(parts) > 1 and parts[1] else parts[0], "features": [], "screens": []}
            modules.append(current)
        elif label == "FEATURE":
            name = parts[0]
            if not name or name in scenarios:
                continue
            when = _clause(parts[1], "WHEN") if len(parts) > 1 else ""
            then = _clause(parts[2], "THEN") if len(parts) > 2 else ""
            module()["features"].append(name)
            scenarios[name] = {"when": when, "then": then}
        elif label == "SCREEN":
            if len(parts) < 2 or not _clean_id(parts[0]):
                continue
            sid = _clean_id(parts[0])
            if any(s["id"] == sid for s in screens):
                continue
            screens.append({"id": sid, "name": parts[1], "purpose": parts[2] if len(parts) > 2 else parts[1]})
            module()["screens"].append(sid)
        elif label == "FLOW":
            arrow = re.match(r"\s*([\w\- ]+?)\s*(?:->|→|=>)\s*([\w\- ]+?)\s*$", parts[0])
            if arrow:
                flows.append((_clean_id(arrow.group(1)), _clean_id(arrow.group(2)), parts[1] if len(parts) > 1 else "navigate"))
        elif label.startswith("STACK_"):
            key = label[len("STACK_"):].lower()
            if key in stack:
                stack[key] = None if body.strip().lower() in ("none", "null", "") and key == "payments" else body.strip()

    modules = [m for m in modules if m["features"] or m["screens"]]
    if tidy:
        modules = tidy_modules(modules)
    features = [f for m in modules for f in m["features"]]
    if len(features) < MIN_FEATURES:
        raise ValueError(
            f"Only {len(features)} FEATURE line(s). Write at least {MIN_FEATURES}, each like: "
            "FEATURE: <name> | WHEN <user action> | THEN <app result>"
        )
    if len(modules) < MIN_MODULES:
        raise ValueError(
            f"Only {len(modules)} MODULE line(s). Write at least {MIN_MODULES}, each like: "
            "MODULE: <module name> | <plain-English title>, followed by its FEATURE and SCREEN lines"
        )
    if not screens:
        raise ValueError("No SCREEN lines found. Write at least 2 lines like: SCREEN: <short_id> | <Screen Name> | <purpose>")

    def resolve(ref: str):
        """Screen id for a FLOW endpoint: exact id, then screen name, then a unique partial match."""
        if any(s["id"] == ref for s in screens):
            return ref
        by_name = [s["id"] for s in screens if _clean_id(s["name"]) == ref]
        if by_name:
            return by_name[0]
        partial = [s["id"] for s in screens if ref and (ref in s["id"] or s["id"] in ref or ref in _clean_id(s["name"]))]
        return partial[0] if len(partial) == 1 else None

    transitions = []
    for a, b, trigger in flows:
        src, dst = resolve(a), resolve(b)
        if src and dst and src != dst:
            transitions.append({"from": src, "to": dst, "trigger": trigger})
    if not transitions and len(screens) > 1 and tidy:
        # No usable FLOW lines: chain the screens in the order written. A placeholder the user can edit.
        transitions = [
            {"from": a["id"], "to": b["id"], "trigger": f"go to {b['name']}"} for a, b in zip(screens, screens[1:])
        ]
    if not transitions and len(screens) > 1:
        raise ValueError(
            "No valid FLOW lines. Each FLOW must use SCREEN ids you wrote, like: FLOW: "
            f"{screens[0]['id']} -> {screens[1]['id']} | click the button"
        )

    locked_spec = {"version": 1, "product_type": product_type, "stack": stack, "features": features, "modules": modules}
    user_flow = {"version": 1, "spec_version": 1, "screens": screens, "transitions": transitions}
    return locked_spec, user_flow, scenarios
