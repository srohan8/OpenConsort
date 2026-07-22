# Kickoff Brief for Claude Code — UI Refinements: Rename, Nav Help Text, Editable Canvas, Delta Chat

**Context:** Follow-on to the scaffolded UI shell (`doc/ui-shell-report.md`, `frontend/`). This came from the first real browser walkthrough of that shell — see `doc/architecture.md`'s "Platform UI Structure" section, "UI refinements from first real browser walkthrough" for the full decision record. Four changes, two small/mechanical and two substantial — all in this one brief since they touch the same area of the app.

## Part 1: Rename "UI" tab to "User Flow" (small, mechanical)

Rename the tab label from "UI" to "User Flow" throughout the app (nav item, any internal component/route naming that references it, page title). This is purely a naming clarity fix — the tab's content and behavior don't change. Check for any hardcoded "UI" strings in the codebase tied to this tab specifically (not the broader "UI" as in user interface terminology elsewhere in code comments, which shouldn't be touched).

## Part 2: One-line help text under each sidebar nav item (small, mechanical)

Add a short, plain-language description below each of the three nav labels in the sidebar itself (not just as a page subtitle after clicking in — visible at the point of navigation, before the user commits to clicking). Suggested copy, adjust for tone/length as needed to fit the sidebar width:
- **Project Scope**: "What you're building, grouped into modules"
- **User Flow**: "The screens your app will have, and how a person moves between them"
- **Development**: "What's being built right now, and how it's going"

Keep these short enough to fit comfortably under a nav label in a narrow sidebar — one line, not wrapping to two if avoidable.

## Part 3: Editable whiteboard-style canvas for User Flow (substantial)

The User Flow tab's screen/module diagram currently renders the locked `UserFlow` read-only. Change this to an **editable canvas**:
- Users can add a new screen/node directly on the canvas (e.g., a "+" affordance, or right-click/context-menu to add)
- Users can drag existing nodes to reposition them (visual only — doesn't need to persist a meaningful layout beyond the session unless that's easy to add)
- Users can edit an existing node's basic details (title, which module it belongs to)
- Users can draw/edit connections between nodes (representing navigation between screens)

This is a genuine interaction upgrade — the canvas becomes a place to *propose* changes, not just view the current locked state. Use a reasonable existing approach for a draggable/connectable node canvas in React (e.g., a library like `reactflow`/`@xyflow/react` is a common, well-supported choice for exactly this kind of node-and-edge canvas — evaluate and use it or a similarly appropriate library rather than building a custom drag-and-drop/connection system from scratch, since that's a lot of surface area to get right).

## Part 4: Canvas edits trigger a clarifying chat, which becomes a tracked delta (substantial — the most important part of this brief)

**No edit on the canvas is silent.** When a user adds a screen, edits a node, or changes a connection, this should trigger a **conversational prompt** (a chat interface, could be a slide-in panel or modal) that asks the clarifying questions needed to properly scope the change — e.g., if a user adds a new "Settings" screen node, the prompt might ask "What should this screen let a user do?" before the change is considered real.

This exchange is what actually produces a **delta** — matching the delta-interview concept already designed (see `architecture.md`'s two-tier requirements interview section). The output of this chat should structurally resemble a scoped change request, ready to eventually feed the same delta-processing path used elsewhere (see the open design question below — this brief doesn't need to fully resolve that path, just produce output in a compatible shape).

**This new chat thread lives alongside the existing Development-tab dev chat, not replacing it.** Each canvas-triggered chat should appear as its own thread/entry in the Development tab (e.g., "Change requested from User Flow: added Settings screen"), separate from — but visible alongside — any general dev-chat conversation. Tag each thread with which module/screen it relates to, consistent with the existing module-number cross-referencing pattern already used throughout the app.

**Open design question, flagged but not required to resolve in this task:** the relationship between "canvas edit → clarifying chat → delta" and "a message typed directly into dev chat → delta" should ideally converge on one shared underlying mechanism, not two separate implementations. Since the actual delta-processing pipeline (backend-side) doesn't exist yet (still deferred per `roadmap.md`), this task can build the *front-end* interaction and *UI representation* of both paths without needing to fully unify their backend handling yet — just don't design the two paths in a way that would make future unification hard (e.g., have both paths produce a similarly-shaped "delta request" object/event, even if nothing consumes it yet).

## Part 5: Motion & Micro-Interactions (apply throughout Parts 1-4, not a separate feature)

The platform should feel alive and responsive, not static — this isn't a separate task, it's a quality bar to apply while building the parts above. Concretely:

- **Hover/interaction feedback everywhere clickable:** module cards, screen nodes, sidebar nav items should have a subtle visual response on hover (slight lift/shadow change, color shift) — not just a plain cursor change.
- **Smooth transitions, not instant snaps:** switching tabs, expanding a detail panel, and the done/planned checkmark appearing should use a brief transition (150-250ms range is a reasonable default) rather than popping in/out instantly.
- **The canvas (Part 3) should feel tactile:** smooth dragging with no jank, connections that redraw fluidly as a node moves, a satisfying subtle animation when a new connection is made (e.g., a brief highlight pulse on the new edge) — this is the highest-value place to get motion right, since it's the most interactive surface in the app.
- **Progressive, not instant, chat responses (Part 4):** the clarifying chat prompt should feel conversational — e.g., a typing/thinking indicator before a prompt appears, messages appearing individually rather than the whole exchange rendering at once.
- **Module card progress should animate, not just update text:** if a done/total ratio changes (e.g., after a delta is applied), consider a subtle fill/progress-bar animation rather than the number just changing instantly.

**Scope guardrail:** this is about *polish and feel*, not new functionality — don't let this expand into building animation systems or a design-system library from scratch. Use straightforward CSS transitions/animations (or whatever lightweight approach the chosen canvas library already supports) rather than adding heavy new dependencies just for motion. If a micro-interaction is non-trivial to get right within reasonable effort, note it as a flag for a future polish pass rather than over-investing now.

## Part 6: General UI Color Palette (chrome only — do NOT replace module colors)

Apply this muted, professional palette to the app's general chrome — background, primary text, borders, and the main accent color:

- `#909EAE` — bluish-gray (secondary surfaces / muted elements)
- `#5C8DC5` — muted blue (primary accent — e.g., selected nav item, primary buttons, active states)
- `#AD9E90` — warm taupe (secondary accent / subtle highlights)
- `#736F60` — muted olive-brown (secondary text / borders / low-emphasis elements)

**Critical guardrail — do NOT apply this palette to module identity colors.** The app currently uses distinct, more saturated colors per module (purple, teal, coral, etc. — see the existing `frontend/` module color assignments) as a functional cross-referencing mechanism: the same module color appears in Project Scope, User Flow, and Development so a user can visually track "Module 2" across all three tabs at a glance. This is a working UX pattern, not just decoration — **do not overwrite it with this new palette.**

Keep module colors as their own separate, purpose-built color system, distinct from this general chrome palette. If the current module colors clash visually with this new palette, adjust the module colors' saturation/hue slightly to feel cohesive with the new chrome — but they must remain visually distinct from each other and from the general chrome palette, not blended into it.

## What NOT to do in this task

- Don't build the actual backend delta-processing logic — that's a separate, deferred, larger task. This is front-end interaction + mock/stubbed delta creation only (e.g., the "delta" can just be logged to console or added to a local mock array for now).
- Don't wire the User Flow tab to real orchestrator output — still mock data, per the original UI shell brief's scope.
- Don't attempt to fully resolve the canvas-chat vs. dev-chat unification question — flag it, don't solve it.
- Don't over-engineer the canvas library choice — pick a reasonable, well-supported one and move on; this isn't the place to build a custom canvas engine.

## Definition of done

- "UI" tab renamed to "User Flow" everywhere it appears
- One-line help text visible under each of the three sidebar nav items
- User Flow canvas is genuinely editable (add/edit/reposition nodes, edit connections) using an appropriate existing library
- Any canvas edit triggers a clarifying chat prompt before being treated as a real change
- The resulting change appears as its own thread in the Development tab, tagged to the relevant module, alongside (not replacing) the existing dev chat
- Hover states, transitions, and canvas interactions feel smooth/responsive rather than static or instant — per Part 5's guidance, using lightweight CSS-level polish, not heavy new dependencies
- General UI chrome (background/text/borders/primary accent) uses the new palette from Part 6; module identity colors remain distinct and separate, not overwritten by it
- A short report: what was built, which canvas library was used and why, any deviations from this brief, and a restated note on the still-open canvas-vs-dev-chat unification question for future reference
