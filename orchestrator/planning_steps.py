"""Two-step Planning: several narrow calls instead of one big one.

    1. modules  - which 2-4 areas does this idea need? (+ product TYPE)
    2. details  - one call per module: its FEATURE and SCREEN lines
    3. flow     - one call: FLOW lines connecting the screens from step 2

The result is assembled into the same labelled-line text parse_plan() reads, so everything
downstream is unchanged. Each call asks a small model one simple question.
"""
import re

MODULES_SYSTEM = """You are the Planning specialist in a software-build pipeline.
Decide which areas (modules) the product idea needs. Output ONLY these lines, no prose:

TYPE: one of web_app, portfolio, ecommerce, blog, internal_tool, mobile_app
MODULE: <module name> | <plain-English title for non-technical readers>

Write 2 to 4 MODULE lines. Every module must come directly from the idea; do not add generic
extras like Settings or Profile unless the idea asks for them.

Example for "a to-do app with a progress summary":
TYPE: web_app
MODULE: Task management | Add, view and complete your to-dos
MODULE: Progress | See how much you have done"""

DETAIL_SYSTEM = """You are the Planning specialist in a software-build pipeline.
Write the plan for ONE module of the product. Output ONLY these lines, no prose:

FEATURE: <short feature name> | WHEN <what the user does> | THEN <what the app does>
SCREEN: <short_id> | <Screen Name> | <what the screen is for>

Write 2 to 3 FEATURE lines and 1 to 2 SCREEN lines. Each feature must be different, and must
belong to this module and serve the product idea.

Example for module "Task management" of a to-do app:
FEATURE: Add a task | WHEN the user types a title and presses Add | THEN the task appears in the list
FEATURE: Complete a task | WHEN the user ticks a task | THEN it is shown as done
SCREEN: list | Task List | Shows all tasks
SCREEN: add | Add Task | Form to create a task"""

FLOW_SYSTEM = """You are the Planning specialist in a software-build pipeline.
Given the screens of an app, write how a user moves between them. Output ONLY FLOW lines:

FLOW: <from_id> -> <to_id> | <what the user does to move>

Use only the screen ids given. Write one FLOW line per move; every screen should be reachable.

Example screens: list, add, summary
FLOW: list -> add | click Add task
FLOW: add -> list | click Save
FLOW: list -> summary | click Progress"""

_KEEP = {
    "modules": re.compile(r"^\s*(?:[-*\d.)]+\s*)?\**(TYPE|MODULE)\**\s*:", re.IGNORECASE),
    "details": re.compile(r"^\s*(?:[-*\d.)]+\s*)?\**(FEATURE|SCREEN)\**\s*:", re.IGNORECASE),
    "flow": re.compile(r"^\s*(?:[-*\d.)]+\s*)?\**FLOW\**\s*:", re.IGNORECASE),
}
MODULE_RE = re.compile(r"^\s*(?:[-*\d.)]+\s*)?\**MODULE\**\s*:\s*(.+?)\s*$", re.IGNORECASE)


def _keep(text: str, kind: str) -> list:
    return [line.strip() for line in text.splitlines() if _KEEP[kind].match(line)]


def plan_in_steps(complete, idea: str, examples: str = "") -> str:
    """`complete(system, user) -> str`. Returns labelled-line plan text for parse_plan()."""
    intro = f"{examples}\n\n" if examples else ""
    module_lines = _keep(complete(MODULES_SYSTEM, f"{intro}Product idea: {idea}"), "modules")
    modules = [m for m in module_lines if MODULE_RE.match(m)]
    if len(modules) < 2:
        raise ValueError("Step 1 produced fewer than 2 MODULE lines")

    all_modules = "\n".join(modules)
    out = list(module_lines)
    # keep each module's FEATURE/SCREEN lines directly after its MODULE line
    out = [l for l in out if not MODULE_RE.match(l)]
    assembled, screens = out, []
    for module_line in modules[:4]:
        name = MODULE_RE.match(module_line).group(1).split("|")[0].strip()
        detail = _keep(
            complete(
                DETAIL_SYSTEM,
                f"Product idea: {idea}\nAll modules of this product:\n{all_modules}\n\nWrite the plan for this module only: {name}",
            ),
            "details",
        )
        assembled.append(module_line)
        assembled += detail
        screens += [l for l in detail if l.upper().lstrip("-*0123456789.) *").startswith("SCREEN")]

    if len(screens) > 1:
        flow = _keep(complete(FLOW_SYSTEM, f"Product idea: {idea}\nScreens:\n" + "\n".join(screens)), "flow")
        assembled += flow
    return "\n".join(assembled)
