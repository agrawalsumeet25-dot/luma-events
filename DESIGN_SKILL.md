# Design Engineering Skill — Combined Reference

> Synthesized from Emil Kowalski's design engineering philosophy, Taste Skill's anti-slop rules, and Impeccable's token-based system. Every rule below exists to prevent the specific patterns that make AI-generated UI look AI-generated.

---

## 0. Read the Room First

Before touching any code, answer:
1. **What kind of page?** Dashboard, landing, app, viewer, tool
2. **Who uses it?** Technical users, consumers, mixed
3. **What's the vibe?** Minimal, playful, premium, utilitarian
4. **What already exists?** Don't redesign what works

**Output a one-line "Design Read" before generating.** Example: *"Dark dashboard for technical users browsing events — utilitarian with moments of delight, not a marketing site."*

---

## 1. Design Tokens (Mandatory)

**NEVER hardcode colors, fonts, radii, or easing values.** Use CSS custom properties as the single source of truth.

```css
:root {
  /* Surfaces */
  --bg: #0c0f1a;
  --surface: rgba(19, 24, 39, 0.7);
  --border: rgba(148, 163, 184, 0.08);
  --border-hover: rgba(148, 163, 184, 0.15);

  /* Text hierarchy */
  --text: #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted: #475569;
  --text-faint: #334155;

  /* Accent (ONE per project — color-lock rule) */
  --accent: #10b981;          /* emerald — primary actions */
  --accent-hover: #34d399;
  --accent-bg: rgba(16, 185, 129, 0.1);

  /* Secondary semantic colors */
  --info: #0ea5e9;             /* links, calendar, info */
  --positive: #22c55e;         /* success, going, confirmed */
  --warning: #f59e0b;          /* caution */
  --danger: #ef4444;           /* error, destructive */

  /* Radii: TWO sizes only */
  --r-sm: 8px;                 /* chips, inputs, badges */
  --r-lg: 12px;                /* cards, modals, containers */

  /* Easing (Emil Kowalski curves) */
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);

  /* Type */
  --font-display: 'Outfit', system-ui, sans-serif;
  --font-body: 'Geist', -apple-system, BlinkMacSystemFont, sans-serif;
}
```

**Rules:**
- Change a value in ONE place → propagates everywhere
- If you need a new color, add it to tokens. Don't inline `rgba(...)`.
- Two radii. Not three. Not five. TWO.

---

## 2. Color Rules

### The Lila Rule (from Taste Skill)
**AI purple/blue glow is BANNED as the default accent.** "No automatic purple button glows, no random neon gradients." This is the #1 tell that a page was AI-generated.

**Use neutral bases (Zinc/Slate) with ONE high-contrast singular accent:**
- Emerald, Electric Blue, Deep Rose, Burnt Orange, Teal

**Override:** Purple is acceptable ONLY when it has specific semantic meaning (e.g., "scoring" in our viewer) — not as the primary brand color.

### Color Consistency Lock
Once an accent is chosen, it's used on the WHOLE page. A teal site doesn't get a purple CTA in section 7. One accent, everywhere.

### Color with Purpose (from Impeccable)
Every color has a JOB:
- **Accent** = primary actions, CTAs, active states
- **Info** = informational, links, calendar
- **Positive** = success, confirmation, "going"
- **Warning** = caution states
- **Danger** = errors, destructive actions

Don't use colors decoratively. If something is green, it means "yes/success/go."

---

## 3. Typography

### Font Selection
- **Discouraged as default:** Inter (too generic, every AI tool uses it)
- **Preferred:** Geist, Outfit, Satoshi, Cabinet Grotesk
- **Serif is VERY DISCOURAGED.** Only use when the brief explicitly calls for editorial/luxury.
- **One family per project.** Don't mix Outfit with Inter with Roboto.

### Scale
- Display/Headlines: `font-family: var(--font-display)` — Outfit, 700-800 weight
- Body: `font-family: var(--font-body)` — Geist, 400-500 weight
- Mono/Code: system monospace stack

### Hierarchy
- Headlines: 24-28px, weight 700-800, tight letter-spacing
- Body: 13-14px, weight 400-500, relaxed line-height (1.6-1.7)
- Meta/captions: 11-12px, weight 500-600, uppercase tracking
- Max line length: 65ch for body text

---

## 4. Animation Decision Framework (from Emil Kowalski)

### Should this animate at all?

| Frequency | Decision |
|---|---|
| 100+ times/day (filter chips, search) | **No animation. Ever.** |
| Tens of times/day (hover, card nav) | Remove or drastically reduce |
| Occasional (modals, drawers) | Standard animation |
| Rare/first-time (onboarding, celebrations) | Can add delight |

**Never animate keyboard-initiated actions.** They're repeated hundreds of times.

### Easing Rules
- **Always custom curves.** Browser defaults (`ease`, `ease-in-out`) are too weak.
- **Enter/exit = ease-out:** `cubic-bezier(0.23, 1, 0.32, 1)` — starts fast, feels responsive
- **On-screen movement = ease-in-out:** `cubic-bezier(0.77, 0, 0.175, 1)`
- **NEVER ease-in for UI.** It starts slow, making the interface feel sluggish.

### Duration Guide

| Element | Duration |
|---|---|
| Button press feedback | 100-160ms |
| Tooltips, popovers | 125-200ms |
| Dropdowns, selects | 150-250ms |
| Modals, drawers | 200-500ms |
| **Rule: UI animations < 300ms** | |

### Stagger
When multiple items enter together, stagger 50ms per item. Cap at 400ms total delay.

---

## 5. Interaction Rules

### Button Press Feedback (Mandatory)
Every clickable element needs `:active` feedback:
```css
button:active, .card:active { transform: scale(0.97); }
```
Buttons MUST feel responsive to press.

### Touch Device Hover Gating (Mandatory)
Touch devices trigger hover on tap, causing false positives. Gate ALL hover effects:
```css
@media (hover: hover) and (pointer: fine) {
  .card:hover { transform: translateY(-4px); }
}
```

### Performance
- **Only animate `transform` and `opacity`.** Never `width`, `height`, `padding`, `margin`.
- **`will-change: transform` ONLY on hover**, not permanently on all elements.
- **CSS animations beat JS under load.** Use CSS for predetermined animations; JS for dynamic/interruptible ones.

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  *, html {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```
Keep opacity/color transitions (they aid comprehension). Remove movement animations.

---

## 6. Layout Rules (from Taste Skill)

### Shape Consistency
Pick ONE corner-radius scale and stick to it. Our system: 8px (small) and 12px (large). No 14px, no 16px, no 18px.

### Section Layout Repetition Ban
Once you use a layout family for a section, that family appears at most ONCE on the page. Don't make all time-groups look identical.

### Eyebrow Restraint
Max 1 eyebrow-style label per 3 sections. Every-section eyebrows = AI scaffolding.

### Mobile
- Touch targets: minimum 44x44px
- Full-width cards on mobile
- Bottom-sheet modals (not centered overlays)
- No 3D tilt effects on touch devices
- `env(safe-area-inset-*)` for notched phones

---

## 7. Component Principles

### Cards
- Use cards ONLY when elevation communicates hierarchy
- Otherwise group with `border-top`, `divide-y`, or negative space
- No pure-black drop shadows. Tint shadows to background hue.

### Icons
- NEVER use emojis as UI icons. Use SVG icon libraries.
- One icon family per project. Don't mix.
- Standardize `strokeWidth` globally.

### Scrollbar
Custom dark scrollbar for dark themes:
```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
```

---

## 8. Pre-Delivery Checklist

### Visual
- [ ] No purple/blue as default accent (Lila Rule)
- [ ] All colors use CSS custom properties (no hardcoded rgba)
- [ ] TWO radii only (8px, 12px)
- [ ] ONE accent color used consistently across the page
- [ ] Font: Geist or Outfit, NOT Inter as default
- [ ] No emojis as icons

### Interaction
- [ ] `:active { transform: scale(0.97) }` on all clickable elements
- [ ] Hover effects gated behind `@media (hover: hover) and (pointer: fine)`
- [ ] Custom easing curves, not browser defaults
- [ ] Animations under 300ms for UI interactions
- [ ] `prefers-reduced-motion` respected

### Accessibility
- [ ] Text contrast 4.5:1 minimum (WCAG AA)
- [ ] Focus states visible for keyboard navigation
- [ ] Touch targets 44x44px minimum on mobile
- [ ] No horizontal scroll on mobile
- [ ] All images have alt text

### Performance
- [ ] Only animate `transform` + `opacity`
- [ ] `will-change` only on hover, not permanently
- [ ] Lazy rendering for long lists (IntersectionObserver)
- [ ] Debounced search/filter inputs

---

## 9. Applying to Luma Events Viewer

**Design Read:** Dark dashboard for technical users discovering Bay Area events. Utilitarian core with moments of delight (swipe mode, confetti, score rings). Not a marketing site — it's a tool.

**Specific tokens for this project:**
- Accent: Emerald `#10b981` (primary actions, RSVP, active states)
- Score: Violet `#8b5cf6` (ONLY for person scoring — not primary accent)
- Info: Sky `#0ea5e9` (calendar links, date pickers)
- Positive: Green `#22c55e` (going, confirmed, success)
- Font display: Outfit (headings, scores, section labels)
- Font body: Geist (body text, meta, descriptions)
- Background: `#0c0f1a` (deep blue-black, not purple-black)
- Radii: 8px (chips, inputs, badges) and 12px (cards, modals)
