# UI Shell Scaffold — Report

**Date:** 2026-07-22
**Scope:** Per `doc/kickoff-brief-ui-shell.md`. New project: `frontend/` (React + Vite, separate from `orchestrator/`/`data-prep/`).

## What was built

A real, running React + Vite app (`frontend/`) implementing the validated three-tab prototype:

- **`frontend/src/mockData.js`** — mock data shaped to match the module-grouped `LockedSpec`/`UserFlow` structure decided in `doc/architecture.md`'s "Platform UI Structure" section (not the current flat-array `locked_spec.schema.json`, which that same section flags as needing to change *to* this shape — used the target shape directly here rather than blocking on the schema update, per the brief's explicit instruction).
- **`Sidebar.jsx`** — left vertical sidebar, three tab buttons (Project Scope / UI / Development), not top tabs.
- **`ModuleHeading.jsx`** — the shared small-technical-label-above-large-plain-title convention, reused identically across all three tabs (Project Scope cards, UI detail panel, Development rows all render through this one component, so the hierarchy can't drift between tabs).
- **`ProjectScopeTab.jsx`** — module cards (not a flat list), each showing module number/technical label, plain-English title, a computed `done/total` count, and its feature list. Clicking a card selects/highlights it.
- **`UITab.jsx`** — the User Flow map: screens as nodes positioned by flow order (x-axis) and module lane (y-axis, color-coded per module), connected by SVG lines with arrowheads for transitions. Clicking a screen opens a detail panel below with its plain-English purpose, "reached from" context, and an action list where each item is marked done (✓, dark) or planned (○, muted) — not paragraph prose.
- **`DevelopmentTab.jsx`** — module-tagged status rows, each with a done (✓)/in-progress (●) icon and a plain-language status line, plus a per-row expand/collapse toggle showing a stubbed raw-log block (static text, not real log streaming — deferred per the brief).
- **Cross-tab module highlighting** — a single `selectedModule` state in `App.jsx`, passed down to all three tabs and keyed by `module_number`: selecting Module 1 in Project Scope keeps it visually highlighted (dimming other screens in the UI tab, outlining the matching row in Development) when switching tabs.

## Verification performed

Ran the actual app in a browser (not just read the code) via `npm run dev`, and drove it through the real interaction described in the brief:
1. Loaded the app — Project Scope tab renders 3 module cards with correct done/total counts (3/5, 5/7, 0/2 — computed from the mock action lists, not hardcoded).
2. Clicked Module 1's card — selected/highlighted correctly (colored border).
3. Switched to the UI tab — Module 1's two screens (Sign up, Verify email) stayed at full opacity; the rest of the flow map dimmed — confirming cross-tab persistence genuinely works, not just in the code.
4. Clicked the "Sign up" screen node — detail panel appeared below with the purpose text, "reached from" context, and the action list showing 2 done items (✓, dark) and 1 planned item (○, muted).
5. Switched to the Development tab — Module 1's row appeared with a colored outline (the same cross-tab highlight persisting a third tab over), correct ✓/● status icons, and clicking "Show logs" expanded a stubbed log block, collapsing back on a second click.

No console/server errors at any point (`preview_logs` came back clean).

## Deviations from the brief (and why)

- **None structurally.** The layout, tab contents, module hierarchy convention, and cross-tab highlighting all match the brief's description exactly, since it explicitly said not to redesign.
- **Minor addition beyond the brief's letter:** the flow map's screen positions are computed (index-based x, module-lane-based y) rather than hand-placed per screen, so adding/removing a screen in `mockData.js` doesn't require touching `UITab.jsx`'s layout logic — a small robustness choice within the "keep it simple" spirit, not scope creep (still plain `useMemo`, no layout library).
- **Styling is plain CSS** (`index.css`), per the brief's explicit instruction not to over-engineer or aim for pixel-perfect polish at this stage.

## Natural next step

Wire the mock data source to real orchestrator output: since `mockData.js` is the single point components read from, the natural swap is replacing its static exports with the real `LockedSpec`/`UserFlow`/`DesignTokens` returned by `orchestrator.py`'s pipeline (once `locked_spec.schema.json` itself is updated to the module-grouped shape `architecture.md` flags as still pending) — components themselves shouldn't need to change, only the data source. The Development tab's log stub is the next-most-concrete gap: replacing the static `logStub` strings with real per-stage orchestrator log output once that pipeline is wired to run against real user input rather than a hardcoded mock idea.
