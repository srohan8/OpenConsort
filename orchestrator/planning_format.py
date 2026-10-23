"""Plain-content Planning format: the model writes simple labelled lines, code builds the
LockedSpec / UserFlow (and OpenSpec scenarios) from them.

A 1B model never has to produce JSON or OpenSpec headings. Format:

    TYPE: web_app
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

PLANNING_SYSTEM = """You are the Planning specialist in a fixed software-build pipeline.
Turn the product idea into a plan using ONLY these labelled lines. No JSON, no markdown, no extra prose.

TYPE: one of web_app, portfolio, ecommerce, blog, internal_tool, mobile_app
FEATURE: <short feature name> | WHEN <what the user does> | THEN <what the app does>
SCREEN: <short_id> | <Screen Name> | <what the screen is for>
FLOW: <from_id> -> <to_id> | <what the user does to move>

Rules: 3 to 6 FEATURE lines, 2 to 5 SCREEN lines, one FLOW line per move between screens.
FLOW ids must be SCREEN ids you wrote. Use one line per item.

Example for "a to-do app":
TYPE: web_app
FEATURE: Add a task | WHEN the user types a title and presses Add | THEN the task appears in the list
FEATURE: Complete a task | WHEN the user ticks a task | THEN it is shown as done
SCREEN: list | Task List | Shows all tasks
SCREEN: add | Add Task | Form to create a task
FLOW: list -> add | click Add task
FLOW: add -> list | click Save"""

_LABEL = re.compile(r"^\s*(?:[-*\d.)]+\s*)?\**(TYPE|FEATURE|SCREEN|FLOW|STACK_\w+)\**\s*:\s*(.+?)\s*$", re.IGNORECASE)


def _clean_id(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.strip().lower()).strip("_")


def _clause(text: str, word: str) -> str:
    return re.sub(rf"^\s*{word}\s*[:\-]?\s*", "", text.strip(), flags=re.IGNORECASE)


def parse_plan(text: str) -> tuple:
    """Return (locked_spec, user_flow, scenarios). Raises ValueError with a message that is
    safe to feed back to the model as a repair instruction."""
    product_type = "web_app"
    features, scenarios, screens, flows, stack = [], {}, [], [], dict(DEFAULT_STACK)

    for line in text.splitlines():
        m = _LABEL.match(line)
        if not m:
            continue
        label, body = m.group(1).upper(), m.group(2)
        parts = [p.strip() for p in body.split("|")]
        if label == "TYPE":
            value = _clean_id(body)
            product_type = value if value in PRODUCT_TYPES else "web_app"
        elif label == "FEATURE":
            name = parts[0]
            if not name:
                continue
            when = _clause(parts[1], "WHEN") if len(parts) > 1 else ""
            then = _clause(parts[2], "THEN") if len(parts) > 2 else ""
            features.append(name)
            scenarios[name] = {"when": when, "then": then}
        elif label == "SCREEN":
            if len(parts) < 2 or not _clean_id(parts[0]):
                continue
            sid = _clean_id(parts[0])
            screens.append({"id": sid, "name": parts[1], "purpose": parts[2] if len(parts) > 2 else parts[1]})
        elif label == "FLOW":
            arrow = re.match(r"\s*([\w\- ]+?)\s*(?:->|→|=>)\s*([\w\- ]+?)\s*$", parts[0])
            if arrow:
                flows.append((_clean_id(arrow.group(1)), _clean_id(arrow.group(2)), parts[1] if len(parts) > 1 else "navigate"))
        elif label.startswith("STACK_"):
            key = label[len("STACK_"):].lower()
            if key in stack:
                stack[key] = None if body.strip().lower() in ("none", "null", "") and key == "payments" else body.strip()

    if not features:
        raise ValueError("No FEATURE lines found. Write at least 3 lines like: FEATURE: <name> | WHEN <user action> | THEN <app result>")
    if not screens:
        raise ValueError("No SCREEN lines found. Write at least 2 lines like: SCREEN: <short_id> | <Screen Name> | <purpose>")

    ids = {s["id"] for s in screens}
    transitions = [{"from": a, "to": b, "trigger": t} for a, b, t in flows if a in ids and b in ids]
    if not transitions and len(screens) > 1:
        raise ValueError(
            "No valid FLOW lines. Each FLOW must use SCREEN ids you wrote, like: FLOW: "
            f"{screens[0]['id']} -> {screens[1]['id']} | click the button"
        )

    locked_spec = {"version": 1, "product_type": product_type, "stack": stack, "features": features}
    user_flow = {"version": 1, "spec_version": 1, "screens": screens, "transitions": transitions}
    return locked_spec, user_flow, scenarios
