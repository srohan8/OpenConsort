"""Render a LockedSpec + UserFlow as an OpenSpec change folder (no LLM involved).

Layout written under <out_dir>/openspec/changes/<change_name>/:
    proposal.md, design.md, tasks.md, specs/<module>/spec.md, specs/user-flow/spec.md

Each plan module becomes one OpenSpec capability. The pipeline contracts stay JSON; this is a
deterministic projection of them into OpenSpec's artifact format so a generated project can be
developed with /opsx:* later.
"""
import re
from pathlib import Path


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"


def _modules(locked_spec: dict) -> list:
    """Plan modules, or one module holding every feature for plans without modules."""
    modules = locked_spec.get("modules")
    if modules:
        return modules
    return [{"name": "Features", "title": "Features", "features": locked_spec["features"], "screens": []}]


def _module_slugs(modules: list) -> list:
    slugs, seen = [], set()
    for m in modules:
        slug = base = _slug(m["name"])
        n = 2
        while slug in seen or slug == "user-flow":
            slug, n = f"{base}-{n}", n + 1
        seen.add(slug)
        slugs.append(slug)
    return slugs


def render_module_spec(module: dict, product_type: str, scenarios: dict | None = None) -> str:
    lines = ["## ADDED Requirements", ""]
    for feature in module["features"]:
        when = (scenarios or {}).get(feature, {}).get("when", "")
        then = (scenarios or {}).get(feature, {}).get("then", "")
        lines += [
            f"### Requirement: {feature}",
            f"The system SHALL provide: {feature}.",
            "",
            f"#### Scenario: {feature}",
            f"- **WHEN** {when or 'a user exercises this feature in the ' + product_type}",
            f"- **THEN** {then or 'it behaves as described and the result is visible to the user'}",
            "",
        ]
    return "\n".join(lines)


def render_flow_spec(user_flow: dict) -> str:
    names = {s["id"]: s["name"] for s in user_flow["screens"]}
    lines = ["## ADDED Requirements", ""]
    for screen in user_flow["screens"]:
        lines += [
            f"### Requirement: {screen['name']} screen",
            f"The system SHALL provide a {screen['name']} screen: {screen['purpose']}.",
            "",
        ]
        outgoing = [t for t in user_flow["transitions"] if t["from"] == screen["id"]]
        if not outgoing:
            lines += [
                f"#### Scenario: {screen['name']} is reachable",
                f"- **WHEN** a user navigates to {screen['name']}",
                "- **THEN** the screen is shown",
                "",
            ]
        for t in outgoing:
            to = names.get(t["to"], t["to"])
            lines += [
                f"#### Scenario: {t['trigger']}",
                f"- **WHEN** a user does \"{t['trigger']}\" on {screen['name']}",
                f"- **THEN** the app navigates to {to}",
                "",
            ]
    return "\n".join(lines)


def write_change(
    out_dir: Path, idea: str, locked_spec: dict, user_flow: dict, change_name: str = "initial-build", scenarios: dict | None = None
) -> Path:
    change = Path(out_dir) / "openspec" / "changes" / change_name
    stack = locked_spec["stack"]
    constraints = locked_spec.get("constraints") or []
    modules = _modules(locked_spec)
    slugs = _module_slugs(modules)
    screen_name = {s["id"]: s["name"] for s in user_flow["screens"]}

    files = {
        "proposal.md": "\n".join(
            [
                "## Why",
                idea,
                "",
                "## What Changes",
                *[f"- {f}" for f in locked_spec["features"]],
                "",
                "## Capabilities",
                "### New Capabilities",
                *[f"- `{slug}`: {m.get('title') or m['name']}" for slug, m in zip(slugs, modules)],
                "- `user-flow`: screens and transitions from the UserFlow",
                "",
                "## Impact",
                f"New {locked_spec['product_type']} (LockedSpec v{locked_spec['version']}).",
                "",
            ]
        ),
        "design.md": "\n".join(
            [
                "## Context",
                f"Generated from LockedSpec v{locked_spec['version']} and UserFlow v{user_flow['version']}.",
                "",
                "## Decisions",
                *[f"- {k}: {v}" for k, v in stack.items() if v],
                "",
                "## Constraints",
                *([f"- {c}" for c in constraints] or ["- none"]),
                "",
            ]
        ),
        "specs/user-flow/spec.md": render_flow_spec(user_flow),
    }
    for slug, m in zip(slugs, modules):
        if m["features"]:
            files[f"specs/{slug}/spec.md"] = render_module_spec(m, locked_spec["product_type"], scenarios)

    tasks = []
    for i, m in enumerate(modules, 1):
        tasks += [f"## {i}. {m['name']}", ""]
        items = [f"Implement: {f}" for f in m["features"]] + [
            f"Build screen: {screen_name.get(sid, sid)}" for sid in m.get("screens", [])
        ]
        tasks += [f"- [ ] {i}.{j} {item}" for j, item in enumerate(items, 1)]
        tasks.append("")
    files["tasks.md"] = "\n".join(tasks)

    for rel, content in files.items():
        target = change / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (change / ".openspec.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    return change


def requirements_text(locked_spec: dict, user_flow: dict, scenarios: dict | None = None) -> str:
    """The spec text appended to Backend/Frontend prompts when --openspec is set."""
    parts = [
        f"Module: {m['name']}\n{render_module_spec(m, locked_spec['product_type'], scenarios)}"
        for m in _modules(locked_spec)
        if m["features"]
    ]
    return "Requirements:\n" + "\n".join(parts) + "\n" + render_flow_spec(user_flow)
