# HX CFD — Master Design & Build Prompt

You are acting as Principal UX Architect, Design Systems Lead, and Frontend Engineer for **HX CFD**. Everything below is canon. Do not deviate from it, do not invent a new visual identity, and do not treat any instruction here as a suggestion — these are confirmed decisions, not open questions.

Your task: generate, refine, or extend HX CFD screens (starting from the attached reference screenshot — the Results module) so that every screen is indistinguishable in quality and language from that reference, and so that any future screen (Geometry, Meshing, Physics, Solver, Reports, Dashboard, Settings) could be built by someone who has only read this document.

---

## 0. The One-Sentence Test

Before accepting any design decision — a component, a color, a motion, a line of AI copy — run it through this test:

> **Does this help the engineer understand instantly, or does it make them work to understand?**

If it's the latter, reject it, no matter how impressive or information-rich it looks. Clarity is not the goal — it is the method. The goal is engineering capability that didn't exist before, delivered by an interface that never stands between the engineer and the problem.

---

## 1. Core Thesis & Emotional Target

HX exists to "Redefine Impossible" by removing complexity that was never necessary — not by adding power on top of clutter. HX is ruthless on two fronts at once: cutting every non-essential element from the interface, and refusing to accept "that's just how CFD software works" as a constraint.

When an engineer finishes a session, they should feel:
- **Clarity, not confusion** — they understood what happened, they didn't have to reconstruct it.
- **Command, not effort** — they operated something powerful and precise, they didn't fight software.
- **Confidence, not hesitation** — they trusted what HX told them and showed them.

Emotional register: **precision instrument + power** — think state-of-the-art cockpit or mission control. Serious, exact, never cluttered, never apologetic about capability.

HX is **not**: a calm invisible SaaS tool, a playful consumer app, or a dense everything-visible expert tool that mistakes clutter for power.

HX **is**: engineered (every surface deliberate, not decorated), confident (states its assessment directly), exact (numbers are numbers, nothing softened for comfort).

**Root cause HX solves:** across ANSYS, SolidWorks, Fusion 360 and others, confusion is end-to-end because density is used as a proxy for power — every panel always open, every setting always visible, forcing the engineer to filter signal from noise themselves. HX's answer is **Focused Density**.

---

## 2. Focused Density — The Core Design Principle

Show exactly what the current task requires. Nothing more, nothing less. Density is earned by relevance to the current decision, not granted by default. This is not minimalism — a results dashboard mid-analysis can be dense with charts and live monitors — but density must always be contextual and deliberate, never accidental.

**Three-Tier Attention Model** — every piece of on-screen information falls into exactly one tier at any moment:

1. **Focus** — the primary task. Full screen real estate, full detail, full interactivity.
2. **Glance** — secondary info that matters but isn't the current task (e.g., solver residuals ticking while editing geometry). Small, quiet, peripheral indicators only — never a full panel competing for attention.
3. **Hidden** — everything not currently relevant. Fully out of view, but never more than one deliberate action away.

Nothing important disappears permanently. Nothing secondary is ever loud.

---

## 3. Light & Color Carry Meaning, Not Decoration

Visual emphasis is never arbitrary — it's a signal system:
- **Glow** = alive: running, active, selected, or urgent. Nothing else glows.
- **Muted/desaturated status colors** (red/amber/green) = state of something critical (error/warning/success). Applied only to the specific element they describe — never a background wash across a panel.
- **Full-saturation vivid color** = scientific simulation data only (pressure, velocity, temperature fields), governed by physics/domain convention, confined strictly to viewport/visualization surfaces. Never bleeds into UI chrome, panels, or text.
- **Everything else** (the vast majority of the UI) stays in the neutral structural palette (matte black, titanium, white/gray) and carries no meaning. It is the "hardware" the instrument is built from.

If everything glows, nothing means anything — restraint is what keeps the signal powerful.

---

## 4. Material & Color System (Tokens — Confirmed Values)

Four layers. Never mix them.

### Layer 1 — Structural (Brand Identity)
The brand *is* the material palette. There is no brand hue.

| Token | Value | Usage |
|---|---|---|
| `color.structural.black` | `#000000` (true black) | Primary background, base canvas — pure black, not near-black, for max contrast against glow/colormaps |
| `color.structural.titanium.900` | `#1C1D1E` | Panel/card background (Apple brushed-aluminum reference — neutral, cool, never warm-tinted) |
| `color.structural.titanium.700` | `#2C2D2F` | Elevated panel / hover surface |
| `color.structural.titanium.500` | `#3E3F42` | Borders, dividers |
| `color.structural.titanium.300` | `#6E6F72` | Disabled text, secondary iconography |
| `color.structural.white` | `#F5F5F6` | Primary text, high-contrast data, key accents |
| `color.structural.gray.100–400` | mid grays, same cool metallic family | Secondary text, inactive states, subtle chrome |

These carry no meaning — never used to communicate state.

### Layer 2 — Functional (Status Signals)
Small, deliberately muted palette (desaturated ~30–40% from pure). Never decorative.

| Token | Purpose |
|---|---|
| `color.status.success` | Muted green — completed / passed |
| `color.status.warning` | Muted amber — needs attention |
| `color.status.error` | Muted red — failed / blocking |
| `color.status.active` | Muted green + glow — running / live / in-progress |
| `color.status.selection` | White / titanium-white — selected / focused (not a separate hue) |

### Layer 3 — Scientific / Data Visualization
Standard colormaps (jet, viridis, or domain equivalents) at full fidelity for velocity, pressure, temperature, and other scalar fields. Full saturation permitted and expected — this is the one place HX is visually loud, because the physics demands it. Confined strictly to 3D viewports, slice views, contour plots, streamlines.

### Layer 4 — Glow (Meaning Through Light)
Reserved exclusively for: solver actively running, an alert/critical error that just fired, the currently active/selected element. If more than a small minority of visible elements glow at once, it's being used wrong. Idle/default states never glow.

---

## 5. Typography

| Token | Value | Usage |
|---|---|---|
| `type.family.ui` | Geometric sans-serif (Inter, Neue Montreal, or equivalent neutral grotesk) | All UI language: labels, menus, body, headings, buttons |
| `type.family.data` | Monospace / tabular-figure (JetBrains Mono, IBM Plex Mono, or equivalent) | All live/numeric data: coordinates, residuals, mesh counts, solver logs, iteration counts, timers |

**Rule:** switching fonts is itself a meaning signal. "Pressure Drop" (label) stays in `type.family.ui`; "1253.6" (its value) renders in `type.family.data`. The eye should instantly distinguish "this is a label" from "this is a measurement."

Scale tokens: `type.scale.display` (module/section headers) → `type.scale.heading` (panel titles — uppercase, letter-spaced, small, quiet, e.g. "RESULTS EXPLORER," "DETAILS") → `type.scale.body` (standard UI/labels) → `type.scale.caption` (metadata) → `type.scale.data-lg` (prominent live values) → `type.scale.data-sm` (inline table/tree values).

Panel section headers must stay small, uppercase, letter-spaced, and low-contrast relative to the data beneath them — they organize but never compete with actual values.

---

## 6. Spacing & Layout

- Base unit: **8px grid**, confirmed. All padding/margins/gaps derive from multiples of 8 (8, 16, 24, 32, 40...).
- **4px half-step** permitted only in dense, data-heavy contexts (table rows, compact tree items) where full 8px would fight Focused Density's goal of surfacing more relevant data without extra looseness.
- Panel internal padding: 16px standard, 8px for dense tables/rows.
- Grouped settings (Details/Inspector style) separated by clear section labels and generous vertical spacing between groups — never crammed edge-to-edge.

---

## 7. Shape Language

| Token | Value | Usage |
|---|---|---|
| `radius.sm` | **4px (confirmed)** | Buttons, inputs, small controls |
| `radius.md` | 4–6px | Cards, panels, dialogs |
| `radius.none` | 0px | Data tables, technical readouts — sharp edges reinforce precision |

Radius stays small and consistent everywhere. Never use large, soft, "friendly" rounding (12px+). Corners are precise, not decorative.

---

## 8. Elevation & Shadow

Hard, crisp shadows — not soft ambient OS-blur. Elevation reads as mechanical layering (engineered plates stacked on each other), not atmospheric depth.

| Token | Usage |
|---|---|
| `elevation.0` | Base canvas / viewport |
| `elevation.1` | Docked panels (Results Explorer, Details, bottom dock) |
| `elevation.2` | Floating panels, dropdowns, context menus |
| `elevation.3` | Modal dialogs (critical errors, confirmations) |

Minimal blur radius, defined edge — closer to sharp drop-shadow than diffuse glow.

---

## 9. Iconography

- **Style:** custom engineered/schematic icon set — technical, precise, distinct from generic UI libraries. Off-the-shelf sets (default Feather/Material) may inform proportions only, never ship as final identity.
- **Weight:** thin-to-medium line weight, consistent stroke width throughout.
- **Grid:** **20x20 base grid (confirmed)** — uniform optical weight across toolbar, tree views, inspector tabs.
- Coverage required: geometry, mesh, physics, solver, AI, reports, settings, projects, materials, pressure, temperature, velocity, turbulence, boundary conditions, CAD, import/export, diagnostics, GPU, CPU, simulation.

---

## 10. Motion

| Token | Value (confirmed) | Usage |
|---|---|---|
| `motion.duration.instant` | **Under 100ms** | Hover states, toggle flips, panel snap |
| `motion.duration.fast` | **150–250ms** | Module/view cross-dissolve, panel transitions, dropdown open/close |
| `motion.easing.standard` | Fast-out, precise settle — e.g. `cubic-bezier(0.2, 0, 0, 1)` | Default for all transitions |

There is no "moderate/slow" tier — even the largest transition stays close to micro-interaction speed. **No spring/bounce/overshoot anywhere.** Motion is fluid but mechanically precise: it settles decisively, it does not oscillate.

- Module/workflow-stage transitions: quick cross-dissolve (fade), never a directional slide — the CFD pipeline isn't strictly linear in practice (engineers jump back to Geometry from Results constantly), so a slide would falsely imply a spatial relationship.
- Panel docking: magnetic snap zones with strong visual snap guides during drag, so the target is unambiguous before release.

---

## 11. Navigation Model — Fixed Macro, Flexible Micro

Reject both extremes: not a fully freeform workspace (Blender-style — obscures the CFD pipeline's real structure), and not a rigid non-customizable layout (obstructs legitimate personal workflow variance).

- **Macro (fixed):** permanent, ordered left nav rail = **Dashboard → Geometry → Meshing → Physics → Solver → Results → Reports**, plus persistent utility entries (AI Copilot, Extensions, Settings). Not reorderable, not hideable — this reflects a fact about how CFD work happens, not a preference.
- **Micro (flexible):** within any module, all panels are fully dockable, resizable, rearrangeable, and persist per-module, per-user.

You cannot mesh before geometry exists, and cannot solve before physics is defined — fixing the macro removes a decision the engineer shouldn't have to make. Freeing the micro respects that expertise and workflow differ once inside a stage.

---

## 12. Window, Panel & Multi-Monitor Behavior

- **Docking:** magnetic snap zones, clear visual snap guides shown during drag before release.
- **Resizing:** dragging shared borders proportionally adjusts adjacent docked panels — never overlapping.
- **Floating panels:** stay within the single HX application window boundary. They never become independent OS-level windows.
- **Exception — AI Copilot only:** may pop out into a genuine independent OS window and move to a second monitor, remaining persistently visible while the engineer works full-screen elsewhere. This is the *sole* exception to single-window cohesion.
- **Panel chrome:** every panel has a consistent header — small, uppercase, letter-spaced title; top-right controls in this fixed order: pin/pop-out, expand, close.

---

## 13. Primary Interaction Model

**Command-palette-first.** `Ctrl+K` is the primary way power users invoke any action, navigate any module, or search any setting/file/command — taking precedence over mouse-driven menu navigation and memorized shortcuts as the default expert-use expectation.

- Must support fuzzy search across: navigation, actions (run solver, generate report), settings, and searchable data (variables, boundary conditions, project files).
- Mouse remains necessary and fully supported for spatial/geometric work (viewport pan/rotate/zoom, geometry selection, mesh picking, probing) — the palette replaces *searching menus*, not direct manipulation.
- Keyboard shortcuts exist as a secondary acceleration path; the palette is the documented, discoverable default.
- Touchpad gestures (pinch-zoom, two-finger pan) supported in-viewport as secondary input; mouse + keyboard is the assumed primary professional setup.

---

## 14. Session & State Rules

- **AI Copilot visibility:** on by default at the start of *every* session (not just first launch). If dismissed, stays hidden for that session only — reappears automatically next session. Never nags mid-session, never assumes one dismissal is permanent.
- **Panel layouts:** per-module, per-user arrangements persist across sessions. Resetting to default is an explicit, discoverable action (Settings or module menu) — never automatic.
- **Module transitions:** quick cross-dissolve, never directional slide (see §10 rationale).

---

## 15. Notifications, Dialogs & Error Discipline

- **Toast:** transient, corner-anchored, for immediate event awareness.
- **Notification Center:** persistent bell-icon log (top bar), retains full history — every toast also logs here.
- **Modal dialogs:** reserved strictly for critical, blocking errors requiring explicit acknowledgment before work continues.
- **Non-critical warnings/info:** never block the workspace — toast or inline banner only.
- **Critical errors:** AI Copilot leads with a plain-language interpretation and recommendation; raw technical message stays available via expandable "technical details," secondary by default.
- **Minor warnings:** stay in raw technical form, no AI interpretation layer by default — not every signal deserves interpretive overhead; this preserves trust that AI involvement signals real significance.

---

## 16. Solver & Long-Running Task Feedback

- Global top bar persistently shows live solver status whenever a solve is running, regardless of which module the engineer is currently viewing: glowing status dot + label ("Running"), elapsed/total time (`00:32:14 / 01:15:00`), current/total iterations (`1243 / 5000`).
- Always raw instrument data — **never** abstracted into a simplified percentage. This is precision measurement, treated exactly like every other live numeric value in the system (§5).

---

## 17. Core Components (Behavior Contract)

Every component below must be built with these states where applicable: **default, hover, pressed, selected, focused, disabled, loading.**

- **Buttons:** small radius, flat matte surface by default, subtle elevation only on hover/press. No separate "brand-color primary button" — hierarchy comes from position, weight, and elevation, not color.
- **Panels & Docking:** consistent header chrome (§12); all dockable within the single window per §11's flexible micro-structure.
- **AI Copilot Panel:** persistent, dockable, chat-style, with mode tabs (Chat / Analysis / Optimization / Knowledge). Quick-action chips render beneath responses (e.g., "Show regions," "Explain in detail," "Suggest improvements"). Tone: confident, directive — reads like a senior engineer's assessment ("I recommend refining the mesh in the tip clearance region"), never a hedge ("you might want to consider..."). The only panel permitted a true OS-level pop-out.
- **Trees/Explorers** (e.g., Results Explorer): hierarchical collapsible groups, inline right-aligned visibility toggles (eye icon), search/filter pinned at top.
- **Property Inspectors** (e.g., Details panel): grouped by section with uppercase headers; tabs for major categories (Selection, Materials, BCs, Loads, Mesh); live-measurement values in `type.family.data`, dropdowns/selectors in `type.family.ui`.
- **Tables & Monitor Points:** `radius.none`, minimal row dividers, monospace values right-aligned. Inline sparkline/trend indicators permitted per row — this is a Glance-tier pattern (§2), quiet peripheral awareness without a full chart.
- **Toolbars:** icon + label for primary viewport tools, grouped logically with subtle dividers — never one long undifferentiated row.
- **Command Palette:** see §13.

---

## 18. AI Copilot — Design Language (Not a Chatbot)

The AI is a **confident, directive engineering companion**, not a bolt-on chatbot. It must:
- Speak with authority and specificity, always leading with the assessment, not a disclaimer.
- Cover real engineering capability: mesh diagnostics, boundary-condition suggestions, solver optimization, simulation explanation, engineering recommendations, report generation, failure diagnosis, natural-language engineering commands.
- Visually read as an instrument panel extension — same materials, same typography rules, same restraint — never a generic chat-bubble UI borrowed from consumer messaging apps.
- Follow the error-severity rules in §15 exactly: interpret critical errors, stay silent/non-interpretive on minor warnings.

---

## 19. Brand Identity Is Material, Not Hue

HX's brand is the material palette itself: matte black, titanium, white. HX does not compete for attention with a signature brand color the way consumer software does. If any screen introduces a "brand color" as its primary identity marker, that screen has broken from the system and must be corrected back to Layer 1 (§4).

---

## 20. Reference Implementation (Canonical Ground Truth)

The attached HX CFD **Results** screen — module rail on the left (Dashboard, Geometry, Meshing, Physics, Solver, Results [active], Reports, AI Copilot, Extensions, Settings), Results Explorer tree (left), 3D turbine viewport with velocity-magnitude streamlines and legend (center), Details/Inspector panel with tabs (right), bottom dock (Residuals graph, Monitor Points table, Slice View contour, AI Copilot chat) — is **ground truth** for layout, density, and component behavior wherever this document is ambiguous.

When generating or refining any other module (Geometry, Meshing, Physics, Solver, Reports, Dashboard, Settings):
- Reuse the exact same shell: nav rail, top bar (project/module breadcrumb, command palette, solver status, notifications, settings, avatar), bottom status bar (system state, GPU/CPU/disk meters, working directory).
- Swap only the module-specific panel content and iconography — never the chassis, materials, typography, spacing, motion, or interaction rules.
- The turbine geometry and CFD-specific field names are domain content, not literal requirements for future non-CFD HX products (see §21) — but they ARE required consistency targets for every other HX CFD screen.

---

## 21. Cross-Product Scalability (For Awareness Only — Not This Task)

If this system is ever extended beyond HX CFD (HX Learn, HX Energy, HX Robotics, HX Architecture, HX Manufacturing, HX AI, HX Labs), only the following change: Layer 3 colormaps/visualization types (domain-appropriate), the fixed nav rail's actual pipeline stages, and domain-specific iconography. Everything else in this document is inherited exactly, without modification. This section does not apply to the current task of building out HX CFD itself — it exists so you never mistake a CFD-specific detail for a universal rule, or vice versa.

---

## 22. Additional Surface Details, Components & Rendering — Governed by §0–§21

The three governing documents (Philosophy, Design System, Desktop UX Rules) are the **only source of authority**. Nothing in this section introduces a new rule — every item here is an application of what is already defined above. Where anything below could be read as adding a new color, material, or behavior not licensed by §0–§21, §0–§21 wins and the item is omitted or reduced to fit.

- **Borders/dividers:** use `color.structural.titanium.500` only (§4, Layer 1) — no new "invisible border" token. At the confirmed value this already reads as minimal; it is not made lower-contrast than specified.
- **Reflections/glass/metallic sheen:** not introduced. Layer 1 is matte, flat titanium/black (§4). Any reflective or glass-like rendering would add a decorative surface effect the System document does not define, and is excluded on that basis.
- **Hover states:** use `color.structural.titanium.700` as the hover surface (§4, Layer 1) with `motion.duration.instant` (§10). Hover never glows — glow is reserved exclusively for live/critical/selected per §3 and §4 Layer 4.
- **Selection states:** use `color.status.selection` (white/titanium-white) per §4 Layer 2, with glow per Layer 4, transitioning at `motion.duration.instant` (§10). No separate "fade" timing is introduced beyond the confirmed motion tokens.
- **Scrollbars, splitters, tooltips, context menus, breadcrumbs:** treated as ordinary components and must follow §17's component contract (default/hover/pressed/selected/focused/disabled/loading states as applicable), `radius.sm` (§7), Layer 1 materials (§4), and `type.family.ui` (§5). No bespoke styling outside these tokens.
- **Empty states / loading screens:** governed by Focused Density (§2) — an empty or loading view shows only what is true right now (e.g., "no mesh generated yet") and one clear next action; it does not invent decorative illustration or copy tone outside the AI Copilot's confident, direct voice (§18).
- **Window chrome / title bar:** follows the single-window cohesion rule (§12) and the panel chrome pattern (§12) — consistent with the rest of the shell, not a separate treatment.
- **Viewport rendering (lighting, grid, axis, camera):** governed by §3 (Layer 3 scientific color is confined to the viewport) and §2 (Focus tier gets full real estate) — the viewport surface itself stays in Layer 1 neutral materials so that Layer 3 data is the only vivid element in the frame, per §3's restraint rule.
- **GPU/CPU/system indicators** (as in the reference bottom bar): live measurement data, so rendered in `type.family.data` per §5, at Glance tier per §2 — quiet, peripheral, never competing with the Focus-tier content.
- **Accessibility (contrast, reduced motion, scaling):** contrast is already served by true-black + confirmed titanium/white values (§4); reduced motion means falling back toward `motion.duration.instant` and removing the fast-tier transition, never adding a slower alternative tier not defined in §10.

---

## 23. Universal Interaction State Model

Every interactive element in HX — buttons, list items, tree nodes, table rows, tabs, toolbar icons, scrollbars, splitters, tooltips, context menu items, breadcrumbs — follows the same state model. No individual component invents its own state colors, timing, or effects.

| State | Rule |
|---|---|
| **Rest** | `color.structural.titanium.900` surface (or transparent, on flat elements) |
| **Hover** | Surface shifts to `color.structural.titanium.700`. Transition uses `motion.duration.instant` (under 100ms). **Hover never glows** — glow is reserved exclusively for live/critical/selected states (Design Philosophy §5), never for a passive mouse-over. |
| **Pressed/Active** | Slightly deeper than hover (`titanium.500` border or subtle inset), same instant transition. |
| **Selected** | Uses `color.status.selection` (white/titanium-white) **plus glow** — the one interaction state permitted to glow, because a selection is a genuine live/active state, not a passive hover. Transition is instant, same as every other state — no separate fade or ease invented for selection specifically. |
| **Disabled** | Reduced opacity on `titanium.300`, no hover/press response. |

**Borders & dividers:** all borders, panel divisions, splitters, and dividers use `color.structural.titanium.500` — the single border token defined in the Design System. No component should introduce a separate "invisible border" or additional border shade.

**Reflections, glass, or metallic sheen:** explicitly excluded, everywhere, on every component. The Design System defines the structural material layer as flat matte titanium/black. Glass, reflective, or sheen effects are not part of the HX visual language at any elevation or component.

---

## 24. Secondary & Overlay Components

None of the components below introduce new visual rules — each follows the interaction-state model (Section 1) and the materials, radius, and typography already defined in the Design System.

### Scrollbars
- Fully hidden at rest (no persistent track).
- Appears the moment the cursor enters a scrollable region — not only on an active scroll gesture. Uses `motion.duration.instant`, same as every other state transition in Section 1.
- Thin, low-contrast track using `color.structural.titanium.500` — the same border token used everywhere else.

### Splitters (draggable panel dividers)
- Visible at rest as a thin hairline, **1–3px**, using `color.structural.titanium.500`.
- Hover state follows Section 1 exactly: shifts toward `titanium.700`, instant transition, no glow (a splitter at hover is not a live/selected state).

### Tooltips
- Appear **instantly on hover, no delay** (`motion.duration.instant`).
- `type.family.ui`, small scale, `color.structural.titanium.900` background, `color.structural.titanium.500` border, `radius.sm` (4px) — no new radius or material introduced.

### Context Menus (right-click)
- Icon + label per item, using the same custom engineered icon set as toolbars/trees.
- Item states follow Section 1 exactly (hover = `titanium.700`, no glow).
- Grouped with dividers using `color.structural.titanium.500`.

### Breadcrumbs
- `type.family.ui`, same states as any other interactive text element in Section 1 (hover = `titanium.700` text or underline, instant transition, no glow).
- Current/active location uses `color.structural.white` for contrast against trailing (inactive) path segments, which sit at lower-contrast gray.

---

## 25. Empty States & Loading Screens

Governed by **Focused Density** (Design Philosophy §4): show only what is true right now, plus at most one next action. No decorative illustration, no tone outside the AI Copilot's established confident voice (Design Philosophy §6) if AI copy is involved.

### Empty States
- **First-launch onboarding empty state** (no project exists yet): icon, one short headline stating the true current state, and a single primary action (e.g., "Create your first project"). This is still Focused Density — the task at this exact moment genuinely is project creation, so that's the only thing shown.
- **Routine in-app empty states** (e.g., Results panel before a solve has run): icon + one line of fact (e.g., "No results yet — run a solve to see them here"). No forced call-to-action button if the action isn't the user's actual next step at that moment; no illustration, no marketing tone.

### Loading Screens
- Full application launch or large project load: the HX mark with a restrained, non-looping-playful animation, consistent with `motion.easing.standard` (fluid but mechanical, no bounce).
- Shorter in-app loading (switching modules, generating a report): no branded screen — a component-level loading indicator within the relevant panel only, per Focused Density. A full-screen interruption isn't earned by a short, routine wait.

---

## 26. Viewport Rendering Behavior

The viewport itself (geometry, chrome, grid, UI overlays within it) stays governed by **Layer 1** (Design System §1) — flat matte titanium/black, no gloss, no reflection. Only the simulation data rendered inside it (velocity/pressure/temperature fields, streamlines) is permitted to be vivid, per **Layer 3** and the restraint rule in Design Philosophy §5: HX is "loud" in exactly one place, and that place is the data, never the surrounding hardware.

### Lighting
- Reference: high-contrast cinematographic lighting (in the vein of Christopher Nolan's visual style — *The Dark Knight*, *Interstellar*) — serious, industrial-feeling realism, not glossy CG.
- A dominant single key light creates real directional contrast between lit and unlit surfaces of the model.
- Sufficient fill light ensures shadow detail is never fully crushed to black — engineers must be able to inspect geometry on the non-lit side of a part.
- Neutral/cool light temperature only — no colored or stylized lighting gels, consistent with Layer 1's flat matte discipline.

### Grid / Reference Plane
- A subtle reference grid, rendered at low contrast so it recedes behind the model — a neutral, non-competing Layer 1 element.
- No reflective ground plane or glossy floor — that would violate Layer 1's flat-matte rule and introduce an effect this system does not license anywhere.

### Camera Behavior
- Direct, 1:1 orbit while actively dragging — no interpretive smoothing during active input, preserving precision.
- Brief momentum glide on release, using `motion.easing.standard` — the viewport-specific expression of "fluid but mechanical": precise under direct control, never abrupt at release.

---

## 27. System Status Indicators (GPU / CPU / Disk)

Live system data, so it follows the same rule as every other live measurement in HX: `type.family.data` (monospace/tabular), not `type.family.ui`.

- Treated as a **Glance-tier** element (Design Philosophy §4) — quiet and peripheral in the status bar, never competing for primary attention. It is background awareness, not a focus-tier readout.
- Format: label + live percentage (`type.family.data`) + a small inline bar/sparkline, matching the canonical reference implementation.
- Color stays neutral titanium/white during normal operation; only shifts to a muted functional color (Layer 2) if a threshold is crossed — normal operation carries no signal value and shouldn't visually compete.

---

## 28. Accessibility

### Contrast
- WCAG AA baseline, achieved directly from the confirmed structural values in the Design System (true `#000000`, Apple-aluminum titanium tones, `#F5F5F6` white) — no separate "accessibility palette" is introduced.
- AA was chosen over AAA deliberately: AAA would require brightening the muted Layer 2 functional colors enough to break the restrained aesthetic the Design System establishes. AA is achievable without that compromise.

### Reduced Motion
- HX automatically detects and respects the OS-level "Reduce Motion" setting.
- When active, HX falls back to its **existing fastest tier** — `motion.duration.instant` (under 100ms) — for transitions that would otherwise use `motion.duration.fast`, and disables the viewport camera's momentum glide on release (Section 4). This is not a new, slower "accessibility mode"; it is simply the system settling on the fast end of the range it already defines.

### Scaling
- All spacing, typography, and icon tokens (defined in the Design System) are relative units, so the interface scales cleanly with OS-level display scaling without fixed-pixel exceptions.

---

## 29. Quick-Reference Rule Table

| Item | Governing Rule |
|---|---|
| Hover (any component) | `titanium.700` surface, instant transition, never glows |
| Selected (any component) | White/titanium-white + glow, instant transition |
| Borders/dividers/splitters | `titanium.500`, no separate shade |
| Reflections/glass/sheen | Excluded entirely, no exceptions |
| Scrollbars | Hidden at rest, appears on cursor entry |
| Tooltips | Instant, no delay |
| Empty states | Focused Density — current truth + at most one action |
| Loading (app launch) | Branded HX mark, restrained animation |
| Loading (in-app) | Component-level indicator only, no branded screen |
| Viewport chrome | Flat matte (Layer 1); only sim data is vivid (Layer 3) |
| Viewport lighting | High-contrast key light + fill, no crushed shadows |
| Viewport camera | Direct 1:1 while dragging, brief glide on release |
| GPU/CPU/Disk | Monospace, Glance-tier, neutral unless threshold crossed |
| Contrast standard | WCAG AA |
| Reduced motion | Falls back to existing instant tier, not a new slow tier |
| Scaling | Relative units throughout |

---

## 30. CFD Workflow Configuration Surfaces

No primary workflow module may ship as a decorative placeholder. Every module must present the current engineering truth, the configuration that can be changed now, the prerequisite that is missing if it is blocked, and one clear next action. Repository names are not primary UI labels: HX presents the engineering job, while implementation provenance stays in an Advanced/Diagnostics layer.

| Module | Focus-tier configuration surface | Glance-tier information | Empty / prerequisite state |
|---|---|---|---|
| Dashboard | Project activity, workflow readiness, recent runs, blocking issues | resource status, active job | No project: Create project / Open project |
| Geometry | import, unit/transform review, geometry health, repair revision, named regions | selected entity facts, revision status | No geometry: Import CAD or mesh |
| Meshing | flow domain, patches, mesh strategy, sizing, boundary layers, quality, acceptance | target/estimated cells, last quality verdict | No accepted geometry: finish geometry validation first |
| Physics | material, fluid model, turbulence, energy, operating conditions, boundary-condition mapping | units, unresolved assignments | No accepted mesh: accept a mesh before defining physics |
| Solver | solver family, numerical controls, initialization, convergence criteria, compute profile | estimated cost, prior run comparison | Missing physics or mesh: show exact unresolved prerequisite |
| Results | field selection, contour/slice/streamline/probe controls, monitor selection, comparison | running residuals, active time step | No completed run: No results yet — run a solve to see them here |
| Reports | report scope, selected artifacts, templates, export destination | artifact completeness, last export | No accepted result: run or import results first |

### Module layout contract

- The left panel holds the ordered configuration tree and search. It is not a static decorative explorer: selection changes the active configuration surface.
- The central viewport is the geometric/mesh/result evidence for the active decision. It always has loading, empty, error, and selection feedback states.
- The right inspector edits the selected object or setting, grouped by engineering consequence rather than library/API names.
- The bottom dock is contextual: mesh quality and generation log in Meshing; residuals/monitors in Solver; plots/probes/AI evidence in Results. It does not reserve empty panels merely for visual symmetry.
- Actions that create a new geometry, mesh, case, run, or report revision must state the revision consequence before execution and publish success only after validation succeeds.

### Configuration screen state contract

| State | Required UI behavior |
|---|---|
| Empty | state the exact missing artifact and provide only the next valid action |
| Blocked | name the prerequisite and provide a direct navigation/action path; never present disabled controls without explanation |
| Ready | show editable validated controls, predicted impact where available, and an explicit action to create the next revision |
| Running | lock only controls that would invalidate the active job; show stage, elapsed time, live evidence, cancel action, and access to logs |
| Validation warning | show the affected entity, measured fact, severity, and recovery action inline; do not use a generic warning banner alone |
| Failed | plain-language diagnosis first, technical evidence on expansion, retry only when the failure is infrastructure-retryable |
| Completed | show output revision, acceptance/next action, and provenance link; never imply downstream acceptance automatically |

### Mesh configuration contract

Meshing is a seven-step configuration workflow, not one Generate button:

1. Geometry Health
2. Flow Domain & Patches
3. Mesh Strategy
4. Sizing & Features
5. Boundary Layers
6. Quality & Diagnostics
7. Acceptance

The engineer can inspect and configure route, protected features, sizing/refinement regions, boundary-layer targets, quality thresholds, and resource budget. The UI may recommend choices, but AI and automation never silently delete features, map physical boundaries, waive quality failures, choose wall treatment, or accept a mesh.

---

## 31. Local-First Runtime States

HX CFD is a desktop instrument, even when a local service or engineering worker is active. The UI must never instruct the engineer to open a browser, use localhost, launch Python, run a terminal command, or open an underlying engineering tool.

- Startup: show a compact HX launch state while the desktop session initializes local services and validates the engineering environment. If a local tool is unavailable, show its capability impact and repair action inside HX—not a command line.
- Offline: normal geometry, meshing, solving, results, and local-project workflows remain available. Remote AI/provider controls are quietly unavailable with a factual local/offline explanation; they never block an engineering action.
- Local jobs: show the engineering stage and evidence, not process names or process IDs. Advanced diagnostics may reveal tool versions, worker logs, and artifact paths.
- Project data: surface local project location and artifact provenance in Project Details. Never imply data synchronization or cloud upload unless the engineer explicitly enabled an optional extension.
- AI: clearly label guidance as a recommendation, cite the project evidence it used, and distinguish surrogate/estimated fields from validated solver results.

---

**End of Document**
