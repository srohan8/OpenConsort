"""Render a LockedSpec + UserFlow as an OpenSpec change folder (no LLM involved).

Layout written under <out_dir>/openspec/changes/<change_name>/:
    proposal.md, design.md, tasks.md, specs/<capability>/spec.md

The pipeline contracts stay JSON; this is a deterministic projection of them into
OpenSpec's artifact format so a generated project can be developed with /opsx:* later.
"""
import re
from pathlib import Path


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"


def _screen_names(user_flow: dict) -> dict:
    return {s["id"]: s["name"] for s in user_flow["screens"]}


def render_features_spec(locked_spec: dict, scenarios: dict | None = None) -> str:
    lines = ["## ADDED Requirements", ""]
    for feature in locked_spec["features"]:
        when = (scenarios or {}).get(feature, {}).get("when", "")
        then = (scenarios or {}).get(feature, {}).get("then", "")
        lines += [
            f"### Requirement: {feature}",
            f"The system SHALL provide: {feature}.",
            "",
            f"#### Scenario: {feature}",
            f"- **WHEN** {when or 'a user exercises this feature in the ' + locked_spec['product_type']}",
            f"- **THEN** {then or 'it behaves as described and the result is visible to the user'}",
            "",
        ]
    return "\n".join(lines)


def render_flow_spec(user_flow: dict) -> str:
    names = _screen_names(user_flow)
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
                f"- **THEN** the screen is shown",
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
                "- `features`: product features from the LockedSpec",
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
        "specs/features/spec.md": render_features_spec(locked_spec, scenarios),
        "specs/user-flow/spec.md": render_flow_spec(user_flow),
    }

    tasks = ["## 1. Backend", ""]
    tasks += [f"- [ ] 1.{i} Implement: {f}" for i, f in enumerate(locked_spec["features"], 1)]
    tasks += ["", "## 2. Frontend", ""]
    tasks += [f"- [ ] 2.{i} Build screen: {s['name']}" for i, s in enumerate(user_flow["screens"], 1)]
    files["tasks.md"] = "\n".join(tasks) + "\n"

    for rel, content in files.items():
        target = change / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (change / ".openspec.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    return change


def requirements_text(locked_spec: dict, user_flow: dict, scenarios: dict | None = None) -> str:
    """The spec text appended to Backend/Frontend prompts when --openspec is set."""
    return f"Requirements:\n{render_features_spec(locked_spec, scenarios)}\n{render_flow_spec(user_flow)}"
