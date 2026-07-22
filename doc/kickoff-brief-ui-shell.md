# Kickoff Brief for Claude Code — Scaffold Real UI Shell (Three-Tab Platform Layout)

**Context:** This chat prototyped and validated the platform's main UI structure via throwaway interactive mockups (SVG/HTML widgets, not real code) — see `doc/architecture.md`'s "Platform UI Structure: Three Tabs, Threaded by Module Number" section for the full decision record. This task turns that validated concept into a real, running React/Vite project in the repo — not another mockup.

## Goal of this task

Scaffold a real React + Vite frontend (matching the Phase 1 combo already locked: FastAPI + React/Vite) implementing the three-tab shell — Project Scope, UI, Development — using **hardcoded mock data first**, not connected to the real orchestrator yet. Get the shell itself feeling right before wiring it to anything real.

## What to build (matches the validated prototype exactly — don't redesign)

**Layout:** left-side vertical sidebar with three tab buttons (Project scope, UI, Development), content area fills the remaining width to the right. Not top horizontal tabs.

**Module title hierarchy (apply consistently everywhere a module appears):** a small technical label above a larger plain-English title. E.g.:
```
Module 2 · Task management        <- small label
Add, view, and complete your to-dos  <- larger, primary heading
```
The plain-English phrasing is the primary thing a user reads; the technical label is a lightweight cross-reference anchor.

**Tab 1 — Project Scope:** modules shown as visual cards (not a flat list), each showing its module number + technical label, plain-English title, and a done/total count (e.g. "3/3 done"). Clicking a module should visually select/highlight it (persists across tab switches — see below).

**Tab 2 — UI:** the interactive User Flow map — screens as nodes connected by navigation-path lines, each screen tagged with its module number/color. Clicking a screen node shows a detail panel below with: the screen's plain-English purpose, "reached from" context, and its actions listed as a bulleted list — each action marked done (checkmark, dark text) or planned (dot icon, muted text), not a paragraph description.

**Tab 3 — Development:** a list of module-tagged status rows, each showing: module label, a done (checkmark)/in-progress (dot) icon, and a plain-language status line (e.g. "Auth endpoints built and tested", "Building progress stats endpoint..."). Default to plain language — a non-technical user should be able to read this tab and understand what's happening. Include an expand/collapse affordance per row for viewing raw logs/code (can be a stub/placeholder for now — the real log wiring is a later task, not this one).

**Cross-tab module highlighting:** selecting a module in the Project Scope tab should keep that same module highlighted when the user switches to the UI or Development tabs (shared selection state across tabs, via the module number as the key).

## Mock data to use

Use a mock "to-do app" spec as placeholder data (matches what was prototyped in this chat):
- 3 modules: "Account & auth" (Module 1), "Task management" (Module 2), "Progress tracking" (Module 3)
- Module 1 screens: Sign up, Verify email
- Module 2 screens: Add task, Task list, Complete task
- Module 3 screens: Progress summary
- Mix of done/planned actions per screen (don't make everything done — the point is to show the done/planned distinction working)

Structure this mock data as if it roughly matches the real `LockedSpec`/`UserFlow` shape (see `orchestrator/schemas/locked_spec.schema.json` and `user_flow.schema.json` for the real schemas) — close enough that swapping in real orchestrator output later is a data-shape change, not a full rewrite. Note: `locked_spec.schema.json`'s `features` field is flagged in `architecture.md` as needing to change to a module-grouped structure — if that schema update hasn't happened yet, use a reasonable module-grouped mock shape now and flag the schema itself as still needing to catch up, rather than blocking this UI task on that schema change.

## Technical approach

- React + Vite (per the locked Phase 1 frontend stack)
- Keep it simple — this is a shell/prototype, not the final polished product. Plain CSS or a lightweight utility approach is fine; don't over-engineer state management for 3 tabs and one selected-module value (React's built-in `useState` is sufficient, no need for Redux/Zustand etc. at this stage)
- Structure components so swapping mock data for real orchestrator output later is straightforward (e.g., a single `mockData.js`/`mockData.json` file that the components read from, not data scattered inline across components)

## What NOT to do in this task

- Don't connect to the real orchestrator or backend yet — mock data only.
- Don't implement the actual delta-interview or requirements-interview flow — this task is the shell/navigation structure, not the interview logic.
- Don't build real log-streaming for the Development tab — a static/stubbed placeholder for "expand for raw logs" is fine for now.
- Don't touch `orchestrator/` or `data-prep/` — this is a new, separate frontend project within the repo.
- Don't attempt to make this pixel-perfect/production-styled — the Design specialist's eventual output (design tokens) will define the real visual polish later; this task is about structure and interaction working correctly.

## Definition of done

- A running React + Vite app (`npm run dev` works) showing the three-tab sidebar layout
- All three tabs populated with the mock to-do app data, matching the structure/hierarchy described above
- Module selection persists across tab switches
- Screens in the UI tab are clickable and show the action list with done/planned states
- A short report: what was built, any deviations from this brief (and why), and what the natural next step would be (e.g., wiring to real orchestrator output)
