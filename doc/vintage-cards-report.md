# Vintage Design Touches on Cards — Report

**Date:** 2026-07-23
**Scope:** Per `doc/kickoff-brief-vintage-cards.md`, follow-on to the Sunset Stripe palette work.

## What was applied

All five elements, applied consistently to **Project Scope module cards** and the **User Flow screen detail panel**:

1. **Stripe band** — a 5px `linear-gradient` band (terracotta → mustard → sage, equal thirds) via a shared `::before` on `.module-card, .detail-panel`, clipped to the card's rounded corners with `overflow: hidden`.
2. **Thick dark border, sharp corners** — `border: 2px solid #2a241c` (a warm near-black, `--vintage-border`), `border-radius: 4px` (`--vintage-radius`), replacing the previous thin hairline/soft-radius treatment.
3. **Serif title** — `.module-heading .plain-title` now uses `Georgia, "Times New Roman", serif`. Chose Georgia specifically because it's a system font available cross-browser/OS by default — no web font load needed, matching the brief's stated preference.
4. **Module-number badge** — `ModuleHeading.jsx` now parses the existing `technicalLabel` string ("Module 1 · Account & auth") into a terracotta pill (`MODULE 1`) plus the module name as separate muted text beside it, instead of one plain gray line. No caller (`ProjectScopeTab`, `UserFlowTab`'s detail panel) needed to change — they still just pass `technicalLabel`/`plainTitle` as before.
5. **Bold terracotta done/total numbers** — `.module-card-progress` (the "3/5 done" text) changed from `font-weight: 600` / neutral text color to `font-weight: 700` / `color: var(--stripe-terracotta)`.

## Development tab: lighter treatment (judgment call)

Applied **badge + module name only** (element #4), not the full five-element card treatment, to the Development tab's rows (`DevRow` and `DeltaThread` in `DevelopmentTab.jsx`).

**Reasoning:** these are dense, compact list rows (thin left-border color-coding, tight padding, an expand/collapse affordance for logs) — a fundamentally different pattern from the spacious module/screen cards, not a card representation at all. Applying a 2px dark border + sharp corners + top stripe band to every row in what's meant to read as a scannable activity log would visually compete with the expand/collapse interaction and make a list of many rows feel heavy rather than informative. The badge alone gives the same "MODULE N" visual anchor and terracotta accent color the vintage treatment introduces elsewhere, without fighting the row format's own density. No done/total numbers exist in this tab (element #5 doesn't apply here — these rows show status text, not a fraction), so that element was correctly left out rather than force-fit.

## Verification performed

Ran the actual app and visually confirmed (screenshots), not just read the code:
- Project Scope: all three module cards show the stripe band, thick border, terracotta badge, serif title, and bold terracotta "X/Y done" text.
- User Flow detail panel: clicking a screen node shows the identical treatment (stripe, border, badge, serif "Sign up" title) — visually consistent with the Project Scope cards, as required. (One screenshot caught the panel mid-fade-in from its existing `.appear` animation, looking washed out; a second screenshot immediately after confirmed the fully-rendered, correct state — not an actual rendering bug.)
- Development tab: confirmed the lighter badge-only treatment renders correctly across all three status rows, keeping the compact row format intact.

**Contrast confirmed via computed styles, not assumed:**
- Badge: background `rgb(196, 82, 46)` (terracotta) / text `rgb(250, 243, 228)` (cream) — strong, clearly legible contrast.
- Serif title: `rgb(42, 40, 35)` (near-black warm text) against the card's `rgb(251, 245, 232)` (near-white cream) background — strong contrast, no issue found.

No contrast problems were found with either the badge or the serif title against their backgrounds.

## Confirmation: module identity colors untouched

Grepped both `mockData.js` and `index.css` for the module color hex values (`#7c3aed`, `#2563eb`, `#059669`) — they exist **only** in `mockData.js`'s `moduleColors` object, with zero references anywhere in `index.css`. The stripe band is a fixed terracotta→mustard→sage sequence applied identically regardless of which module a card represents; module identity (the purple/teal/coral `--module-color` used for card-selection rings and screen-node borders) remains a fully separate system, exactly as instructed.

## Scope discipline

Per the brief's "what not to do": the sidebar, page headers, buttons, and inputs were not touched by any of the five elements — border-radius and border treatment changes were scoped strictly to `.module-card` and `.detail-panel`. No textures, gradients-as-background, or additional decorative elements were added beyond the five specified items.
