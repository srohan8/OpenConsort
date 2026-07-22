# Kickoff Brief for Claude Code — Vintage Design Touches on Cards

**Context:** Follow-on to the Sunset Stripe color palette (`doc/kickoff-brief-ui-refinements.md` Part 6) and the sidebar color fix (dark sage, `#2E362E`). The palette alone read as flat/generic — this task adds specific vintage design touches (beyond color) to actually evoke the retro van-stripe reference, applied consistently to module cards (Project Scope tab) and screen node detail panels (User Flow tab).

## What to apply — five elements, all confirmed

Apply all five of these together, consistently, wherever a module or screen card/detail panel appears (Project Scope module cards, User Flow screen detail panel, and any other place a module/screen is represented as a card):

1. **A mini sunset-stripe band across the top of each card** — a thin horizontal strip (~4-5px) using the three sunset-stripe hues in sequence: terracotta `#C4522E` → mustard `#E0A83E` → sage `#6B7A6B`, each taking an equal third of the card's width. This sits at the very top edge of the card, inside the border.

2. **Thicker, dark border with sharper corners** — replace the current thin hairline border and soft border-radius with a heavier border (~2px) in a dark warm tone (e.g. `#2A241C`, a near-black with warm undertone matching the palette) and a smaller corner radius (~4px instead of the current ~12px) — reads more like retro signage/print than a modern soft SaaS card.

3. **A serif heading font for the plain-English title** — the module/screen's primary title (e.g. "Sign up and verify your account") should render in a serif typeface (e.g. `Georgia, serif` or a similar widely-available serif — pick something that renders well cross-browser without requiring a web font load if possible, or use a Google Font via the existing font-loading pattern if the project already has one). The small technical label above it (e.g. "Module 1 · Account & auth") stays in the existing sans-serif — only the primary plain-English title gets the serif treatment.

4. **A solid-color badge for the module number** — instead of the module number being part of the plain gray technical label text, give it its own small solid-color pill/badge (background = terracotta `#C4522E`, text = cream `#FAF3E4` or similar light color for contrast), e.g. a badge reading "MODULE 1" sitting above or beside the rest of the technical label.

5. **Bolder, accent-colored done/total numbers** — the "3/5 done" style text should be bold (font-weight 700, not the current regular weight) and colored with the terracotta accent (`#C4522E`) instead of flat black/dark text.

## Where to apply this

- Project Scope tab: all module cards
- User Flow tab: the screen detail panel (shown when a screen node is clicked) — apply the same card treatment (stripe band, border, badge, serif title, bold accent numbers) to keep it visually consistent with the Project Scope cards
- Any other card-style module/screen representation in the app (check Development tab's module-tagged rows too — if they use a similar card pattern, apply consistently; if they're a different, simpler row style, use judgment on whether the full treatment fits or just a lighter version, e.g. just the badge and accent color, would suit a denser list better — note the reasoning either way)

## What NOT to do

- Don't apply these five elements to the sidebar, page headers, or non-card UI elements — this is specifically for module/screen card representations.
- Don't touch the module identity colors (purple/teal/coral) — the stripe band uses the fixed sunset-stripe three-color sequence regardless of which module color the card is otherwise tagged with; don't conflate the two color systems.
- Don't add textures, gradients-as-background, or additional decorative elements beyond these five specified items — keep this a contained, specific set of changes, not an open-ended "make it more vintage" pass.
- Don't change corner radius or border treatment on non-card elements (buttons, inputs, nav items) — this task is scoped to cards specifically.

## Definition of done

- All five elements applied consistently to Project Scope module cards and the User Flow screen detail panel
- A short report on what was done for the Development tab's module rows (full treatment applied, or a judgment call to use a lighter version, with reasoning either way)
- Confirm readability/contrast: the badge text against terracotta, and the serif title against the cream background, both need to remain clearly legible — flag if any contrast issue is found
