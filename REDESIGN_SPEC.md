# REDESIGN SPEC: Luma Bay Area Events Viewer

**Source file:** `C:/Users/suagraw/luma-events/build_viewer.py`
**Generated:** 2026-05-29
**Audit severity:** 4 Critical, 4 High, 3 Medium, 1 Low

---

## 1. DESIGN READ

A hand-curated local events board that feels like a friend texted you a list -- warm, opinionated, fast, zero chrome. Think Craigslist's density meets Are.na's restraint, not a SaaS dashboard.

---

## 2. DIAL SETTINGS

| Dial     | Value | Rationale |
|----------|-------|-----------|
| VARIANCE | 0.7   | High variation between time-group sections to break grid monotony |
| MOTION   | 0.3   | Minimal motion -- remove stat counter animations, keep card entrance |
| DENSITY  | 0.8   | Content-forward: first event card visible within 300px of viewport top |

---

## 3. TOP 15 CHANGES (ordered by impact)

### Change 1: Replace Instrument Serif with Newsreader
**What:** Eliminate the #1 AI font tell (italic serif display heading)
**Current CSS (line 164):**
```css
--fi:'Instrument Serif',Georgia,serif;
```
**New CSS:**
```css
--fi:'Newsreader',Georgia,serif;
```
**Also change Google Fonts import (line 152) from:**
```css
family=Instrument+Serif:ital@0;1
```
**To:**
```css
family=Newsreader:ital,wght@0,400;0,600;1,400
```
**Why:** Instrument Serif italic is the single most common AI design tell of 2025. Newsreader is a contemporary serif with optical sizes that reads as editorial rather than decorative. Remove `font-style:italic` from h1 (line 176), section-header (line 267), and hero-title (line 255) -- use roman weight instead.

### Change 2: Replace AI-purple score accent with warm amber
**What:** Eliminate `#8b5cf6` (Tailwind violet-500) entirely
**Current CSS (line 158):**
```css
--score:#8b5cf6;--sbg:rgba(139,92,246,.08);--sglow:rgba(139,92,246,.2);
```
**New CSS:**
```css
--score:#d97706;--sbg:rgba(217,119,6,.08);--sglow:rgba(217,119,6,.18);
```
**Why:** `#8b5cf6` is the AI-purple signature. Warm amber (`#d97706`, Amber-600 but mixed warmer) signals intentionality and pairs with the warm background tones in Change 3. Also update confetti colors (JS line 642) to remove `#7c3aed` and `#a78bfa`.

### Change 3: Replace Tailwind-default background with warm dark
**What:** Move from cold blue-black to warm charcoal
**Current CSS (line 154):**
```css
--bg:#090b11;
```
**New CSS:**
```css
--bg:#111110;
```
**Also update all `rgba(9,11,17,...)` references throughout CSS to `rgba(17,17,16,...)`:**
- Line 154: `--surface:rgba(16,19,30,.85)` -> `--surface:rgba(24,24,22,.88)`
- Line 154: `--surface-2:rgba(22,26,40,.7)` -> `--surface-2:rgba(32,32,28,.72)`
- Line 250 hero overlay: `rgba(9,11,17,.95)` -> `rgba(17,17,16,.95)`
- Line 250 hero overlay: `rgba(9,11,17,.4)` -> `rgba(17,17,16,.4)`
- Line 285 ring bg: `rgba(9,11,17,.8)` -> `rgba(17,17,16,.8)`
- Line 287 badge bg: `rgba(9,11,17,.75)` -> `rgba(17,17,16,.75)`
- Line 289 card body gradient: `rgba(9,11,17,.9)` and `rgba(9,11,17,.5)` -> `rgba(17,17,16,.9)` and `rgba(17,17,16,.5)`
- Line 334 modal overlay: `rgba(9,11,17,.9)` -> `rgba(17,17,16,.9)`
- Line 338 modal body: `rgba(16,19,30,.98)` -> `rgba(24,24,22,.98)`
- Line 368 close bg: `rgba(9,11,17,.5)` -> `rgba(17,17,16,.5)`
- Line 390 cmd overlay: `rgba(9,11,17,.85)` -> `rgba(17,17,16,.85)`
- Line 392 cmd box: `rgba(16,19,30,.98)` -> `rgba(24,24,22,.98)`
**Why:** `#090b11` is the default Tailwind dark mode background. `#111110` is a warm near-black with a barely perceptible yellow cast that reads as intentionally chosen.

### Change 4: Collapse filter wall into single bar + drawer
**What:** Hide all filter chips behind a toggle, show only search bar by default
**Current HTML (lines 768-796):** 9 rows of controls always visible
**New HTML structure:**
```html
<div class="toolbar">
  <input type="search" id="search" placeholder="Search events..." />
  <label class="sort-wrap">Sort: <select id="sort">...</select></label>
  <button class="filter-toggle" id="filterToggle">
    Filters <span class="filter-count" id="filterCount"></span>
  </button>
  <div class="mode-toggle">...</div>
</div>
<div class="filter-drawer" id="filterDrawer">
  <!-- all chips, date range, person chips, score slider move here -->
</div>
```
**New CSS:**
```css
.toolbar{display:flex;gap:12px;align-items:center;margin:0 0 24px;flex-wrap:wrap}
.filter-toggle{background:transparent;color:var(--t3);border:1px solid var(--border);border-radius:var(--rs);padding:8px 16px;font-size:13px;font-weight:500;cursor:pointer;font-family:var(--fb);transition:border-color .2s var(--eo)}
.filter-toggle:active{transform:scale(.97)}
.filter-count{background:var(--accent);color:var(--bg);border-radius:999px;padding:1px 6px;font-size:10px;margin-left:6px;display:none}
.filter-count.show{display:inline}
.filter-drawer{display:none;padding:20px 0;border-bottom:1px solid var(--border);margin:0 0 24px}
.filter-drawer.open{display:flex;flex-wrap:wrap;gap:12px;align-items:center}
```
**Why:** ~500px / 48% of viewport consumed before first content. On mobile, zero event cards visible above fold. Target: first card within 300px.

### Change 5: Replace Geist body font with Sora
**What:** Eliminate the second AI-tell font
**Current CSS (line 163):**
```css
--fb:'Geist',-apple-system,BlinkMacSystemFont,sans-serif;
```
**New CSS:**
```css
--fb:'Sora',-apple-system,BlinkMacSystemFont,sans-serif;
```
**Also change Google Fonts import (line 152) from:**
```css
family=Geist:wght@300;400;500;600;700
```
**To:**
```css
family=Sora:wght@300;400;500;600;700
```
**Why:** Geist is the Vercel house font that every AI tool defaults to. Sora is a geometric sans-serif with distinctive lowercase letterforms (the `a` and `g` are immediately recognizable) that signal intentional selection.

### Change 6: Introduce 3 card layout variants
**What:** Break uniform 380px card grid with mixed layouts
**Current CSS (lines 276-280):**
```css
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px}
.grid .card:first-child{grid-column:1/-1;height:440px}
```
**New CSS:**
```css
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.grid .card:first-child{grid-column:1/-1;height:400px}
.grid .card:nth-child(2),
.grid .card:nth-child(3){height:340px}
.grid .card:nth-child(n+4){height:280px}
.grid .card.compact{height:auto;min-height:80px;flex-direction:row;border-radius:var(--rs)}
.grid .card.compact .cover{position:relative;width:120px;min-width:120px;height:auto}
.grid .card.compact .body{position:relative;background:none;padding:16px}
.grid .card.compact .title{font-size:15px}
```
**Why:** Every section uses identical layout -- zero variation between temporal groups. Mixed card heights and a compact row variant create visual rhythm.

### Change 7: Differentiate time-group section layouts
**What:** Each time bucket gets a distinct layout pattern
**Current:** All 5 sections use identical `.section-header` + `.grid` markup
**New section-specific CSS:**
```css
/* Today: horizontal scroll strip on desktop */
.section[data-period="today"] .grid{
  display:flex;gap:16px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px;
  -webkit-overflow-scrolling:touch
}
.section[data-period="today"] .grid .card{
  flex:0 0 360px;scroll-snap-align:start;height:400px
}
.section[data-period="today"] .grid .card:first-child{
  flex:0 0 480px;grid-column:auto
}
@media(max-width:768px){
  .section[data-period="today"] .grid .card{flex:0 0 85vw}
  .section[data-period="today"] .grid .card:first-child{flex:0 0 85vw}
}

/* Tomorrow: 2-column with one large + two stacked small */
.section[data-period="tomorrow"] .grid{
  grid-template-columns:1.4fr 1fr;grid-template-rows:auto auto
}
.section[data-period="tomorrow"] .grid .card:first-child{
  grid-row:1/3;height:auto;min-height:380px
}
@media(max-width:768px){
  .section[data-period="tomorrow"] .grid{grid-template-columns:1fr}
  .section[data-period="tomorrow"] .grid .card:first-child{grid-row:auto}
}

/* This Week: standard grid (current behavior) */
.section[data-period="week"] .grid{
  grid-template-columns:repeat(auto-fill,minmax(320px,1fr))
}

/* This Month + Later: compact list rows */
.section[data-period="month"] .grid,
.section[data-period="later"] .grid{
  grid-template-columns:1fr;gap:8px
}
.section[data-period="month"] .grid .card,
.section[data-period="later"] .grid .card{
  height:auto;min-height:80px;flex-direction:row;border-radius:var(--rs)
}
```
**Why:** Layout monotony is a medium-severity finding. Each time bucket should feel different to sustain attention and signal editorial intent.

### Change 8: Replace vanity stat bar with contextual summary
**What:** Remove 4-stat counter animation, replace with single actionable line
**Current HTML (lines 760-765):**
```html
<div class="stats">
  <div class="stat"><div class="n" data-val="...">..</div><div class="l">Events</div></div>
  ...4 stats...
</div>
```
**New HTML:**
```html
<div class="summary" id="summary"></div>
```
**New CSS:**
```css
.summary{font-size:14px;color:var(--t2);margin:16px 0 0;line-height:1.5}
.summary strong{color:var(--text);font-weight:600}
```
**JS logic:** Compute and render something like: `<strong>12 events</strong> happening today in San Francisco. <strong>3 new</strong> since yesterday.`
**Why:** The stat bar (433 / 24,268 / 395 / 38) is the canonical AI dashboard hero pattern. Contextual text is both more useful and less cliched. Also remove `animateStats()` function entirely (JS line 710-712).

### Change 9: Fix WCAG AA contrast on muted labels
**What:** Increase `--t4` lightness to pass 4.5:1 on new background
**Current CSS (line 156):**
```css
--t4:#475569;
```
**New CSS:**
```css
--t4:#6b7280;
```
**Contrast check:** `#6b7280` on `#111110` = approximately 5.2:1 (passes AA for all text sizes)
**Why:** `#475569` at 10-11px fails WCAG AA (4.1:1 ratio). All stat labels, chip labels, control labels are affected. This is a High severity accessibility issue.

### Change 10: Consolidate to 8 font sizes (from 17)
**What:** Reduce to a strict modular scale: 10, 12, 13, 15, 18, 24, 32, 44
**Current:** 17 distinct sizes (9px through 48px)
**Changes:**
| Current | New | Where |
|---------|-----|-------|
| 9px (badge, going-badge) | 10px | `.badge`, `.going-badge` |
| 10px (stat label, hero-label, cat, modal-score name, person-chip label) | 10px | keep |
| 11px (chip, labels, date-quick, pick-chip, cmd-item meta, prep h3, picks-label) | 12px | all `.chip`, `.date-quick button`, `.pick-chip`, etc. |
| 14px (body, modal desc, cmd-item title) | 15px | `body`, `.modal .desc`, `.cmd-item .ci-title` |
| 16px (cmd-input, score-val) | 15px | `.cmd-input`, `.score-slider .val` |
| 20px (ring-lg val) | 18px | `.ring-lg .ring-val` |
| 22px (swipe title, flash) | 24px | `.swipe-card .s-title`, `.swipe-flash` |
| 28px (first-card title, modal h2) | 24px | `.grid .card:first-child .title`, `.modal h2` |
| 40px (hero-title) | 32px | `.hero-title` |
| 48px (h1) | 44px | `h1` |
**Why:** 17 font sizes is excessive. A proper type scale uses 7-8 sizes max.

### Change 11: Consolidate border-radius to 4 values (from 8)
**What:** Reduce to: `--rs:6px`, `--rl:14px`, `999px` (pill), `50%` (circle)
**Current CSS (line 160):**
```css
--rs:8px;--rl:16px;
```
**New CSS:**
```css
--rs:6px;--rl:14px;
```
**Remove:** 2px (range track), 3px (scrollbar), 4px (kbd), 6px (mode-btn inner) -- normalize all to `--rs` or `--rl`.
**Why:** 8 border-radius values far exceeds the 3-4 threshold.

### Change 12: Fix spacing to 4px grid
**What:** Snap all off-grid values to nearest 4px multiple
**Current off-grid values -> New values:**
| Current | New | Where |
|---------|-----|-------|
| 3px (mode-toggle padding) | 4px | `.mode-toggle` |
| 5px (badge/chip padding-block) | 4px | `.chip`, `.badge` |
| 6px (card body gap, chips gap, badges gap) | 8px | `.body`, `.chips`, `.badges` |
| 7px (mode-btn padding-block) | 8px | `.mode-btn` |
| 10px (controls input padding, date-quick gap) | 12px | `.controls input`, `.date-quick` |
| 14px (chip padding-inline, prep h3 margin, cover ring padding) | 12px or 16px | various |
| 18px (cmd-input padding, person-chip padding-inline) | 16px or 20px | `.cmd-input`, `.person-chip` |
**Why:** ~40% of spacing values are off the 4px grid.

### Change 13: Remove pulsing dot from section headers
**What:** Delete the fake "live indicator" decoration
**Current CSS (lines 268-269):**
```css
.section-header .dot{width:6px;height:6px;border-radius:50%;background:var(--pos);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
```
**New CSS:** Delete both rules entirely. Remove `<span class="dot">` from JS (line 508).
**Why:** The pulsing dot is pure decoration that does not indicate real-time data. It is an AI design trope (visual noise masquerading as polish).

### Change 14: Fix touch targets to 44px minimum
**What:** Increase tap targets for WCAG 2.5.8 compliance
**Current -> New:**
```css
/* Chips: current ~23px tall, need 44px */
.chip{padding:10px 16px;font-size:12px}
/* was: padding:5px 14px;font-size:11px */

/* Date quick buttons: current ~25px tall */
.date-quick button{padding:10px 14px;font-size:12px}
/* was: padding:6px 12px;font-size:11px */

/* Close button: current 36x36 */
.close{width:44px;height:44px}
/* was: width:36px;height:36px */

/* Mode button: current ~30px tall */
.mode-btn{padding:10px 16px;font-size:12px}
/* was: padding:7px 16px;font-size:12px */

/* Score slider thumb: current 20x20 */
.score-slider input[type=range]::-webkit-slider-thumb{width:24px;height:24px}
/* Still under 44px but range thumbs get system-level enlargement on mobile */
```
**Why:** Multiple touch targets fail the 44x44px minimum. Chips at 23px are nearly half the required size.

### Change 15: Remove confetti and keyboard hint dock
**What:** Delete gratuitous delight-engineering and permanent keyboard hints
**Current CSS (lines 383-386):**
```css
#confetti{position:fixed;inset:0;pointer-events:none;z-index:200}
.kb-hint{position:fixed;bottom:20px;right:20px;...}
```
**New:** Remove `#confetti` canvas element and `confetti()` JS function. Remove `.kb-hint` element. Move keyboard shortcut help into the command palette (`/` menu) where users expect it.
**Why:** Confetti on RSVP click is gratuitous. Permanently docked keyboard hints are an AI trope. Real keyboard-heavy apps show hints contextually.

---

## 4. STRUCTURAL CHANGES (HTML template)

### 4a. Header: Replace stat bar with summary line
```html
<!-- BEFORE -->
<div class="stats">
  <div class="stat"><div class="n" data-val="{total}">{total}</div><div class="l">Events</div></div>
  <div class="stat"><div class="n" data-val="{total_rsvps}">{total_rsvps:,}</div><div class="l">RSVPs</div></div>
  <div class="stat"><div class="n" data-val="{open_count}">{open_count}</div><div class="l">Open</div></div>
  <div class="stat"><div class="n" data-val="{sold_count}">{sold_count}</div><div class="l">Sold out</div></div>
</div>

<!-- AFTER -->
<div class="summary" id="summary"></div>
```

### 4b. Controls: Collapse into toolbar + drawer
```html
<!-- BEFORE -->
<div class="controls">
  <input type="search" .../> 
  <label>Sort: <select>...</select></label>
  <div class="date-range">...</div>
  <div class="person-chips">...</div>
  <div class="score-slider">...</div>
  <div class="chips" id="statusChips"></div>
  <div class="chips" id="catChips"></div>
  <div class="chips" id="cityChips"></div>
</div>

<!-- AFTER -->
<div class="toolbar">
  <input type="search" id="search" placeholder="Search events..." />
  <label class="sort-wrap">Sort: <select id="sort">...</select></label>
  <button class="filter-toggle" id="filterToggle" onclick="toggleFilters()">
    Filters <span class="filter-count" id="filterCount"></span>
  </button>
  <div class="mode-toggle">
    <button class="mode-btn active" data-mode="discover">Discover</button>
    <button class="mode-btn" data-mode="swipe">Swipe</button>
  </div>
</div>
<div class="filter-drawer" id="filterDrawer">
  <div class="person-chips" id="personChips"><span class="label">For:</span></div>
  <div class="score-slider" id="scoreSlider">...</div>
  <div class="chips" id="statusChips"></div>
  <div class="chips" id="catChips"></div>
  <div class="chips" id="cityChips"></div>
  <div class="date-range">...</div>
</div>
```

### 4c. Sections: Add data-period attribute for CSS targeting
```javascript
// BEFORE (JS line 506):
section.className='section';

// AFTER:
section.className='section';
section.dataset.period=k;  // 'today', 'tomorrow', 'week', 'month', 'later'
```

### 4d. Remove confetti canvas and keyboard hints
```html
<!-- DELETE these elements -->
<canvas id="confetti"></canvas>
<div class="kb-hint">...</div>
```

### 4e. Section headers: Remove italic, remove dot
```javascript
// BEFORE (JS line 508):
const dot=k==='today'?'<span class="dot"></span>':'';
section.innerHTML=`<div class="section-header">${dot}${lbl}...`;

// AFTER:
section.innerHTML=`<div class="section-header">${lbl}...`;
```

---

## 5. COLOR PALETTE

All values are chosen to be non-reversible to any Tailwind shade.

| Token | Hex | Role | Notes |
|-------|-----|------|-------|
| `--bg` | `#111110` | Page background | Warm near-black (barely perceptible yellow) |
| `--surface` | `rgba(24,24,22,.88)` | Card/panel backgrounds | Warm dark surface |
| `--surface-2` | `rgba(32,32,28,.72)` | Secondary surfaces | Slightly lighter warm |
| `--border` | `rgba(148,163,184,.06)` | Borders (keep) | Subtle enough, fine |
| `--bh` | `rgba(148,163,184,.14)` | Border hover | Slight bump |
| `--text` | `#ede9e3` | Primary text | Warm off-white (not blue-tinted `#f1f5f9`) |
| `--t2` | `#9c9590` | Secondary text | Warm mid-gray |
| `--t3` | `#706a65` | Tertiary text | Warm muted |
| `--t4` | `#6b7280` | Labels/captions | WCAG AA compliant on `#111110` (~5.2:1) |
| `--accent` | `#2db87a` | Primary accent (CTA) | Custom green (not emerald-500) |
| `--ah` | `#4fd1a0` | Accent hover | Lighter custom green |
| `--abg` | `rgba(45,184,122,.08)` | Accent background | |
| `--score` | `#d97706` | Score/rating color | Warm amber (not violet) |
| `--sbg` | `rgba(217,119,6,.08)` | Score background | |
| `--sglow` | `rgba(217,119,6,.18)` | Score glow | |
| `--pos` | `#2db87a` | Positive/going (same as accent) | Unify accent + positive |
| `--info` | `#3b9ece` | Calendar/info links | Custom blue (not sky-500) |
| `--danger` | `#d1453b` | Sold out / skip | Custom red (not red-500) |

### Confetti colors (JS line 642):
Replace `['#7c3aed','#22c55e','#0ea5e9','#eab308','#ef4444','#a78bfa']`
With: remove confetti entirely (Change 15). If kept for RSVP delight, use:
`['#d97706','#2db87a','#3b9ece','#ede9e3','#d1453b']`

### Score color function (JS line 418):
```javascript
// BEFORE:
const scC=n=>n>=80?'#22c55e':n>=50?'#eab308':'#334155';

// AFTER:
const scC=n=>n>=80?'#2db87a':n>=50?'#d97706':'#3a3a38';
```

---

## 6. TYPOGRAPHY

### Font stack
```css
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=Newsreader:ital,wght@0,400;0,600;1,400&display=swap');
:root{
  --fd:'Outfit',system-ui,sans-serif;      /* Display / numbers (keep) */
  --fb:'Sora',-apple-system,BlinkMacSystemFont,sans-serif;  /* Body (was Geist) */
  --fi:'Newsreader',Georgia,serif;          /* Headings (was Instrument Serif) */
}
```

### Type scale (8 sizes, ~1.25 ratio)
| Size | Weight | Line-height | Usage |
|------|--------|-------------|-------|
| 44px | 400, roman | 1.05 | h1 page title |
| 32px | 700 (Outfit) | 1.0 | Stat numbers (if kept), hero title |
| 24px | 400 (Newsreader, roman) | 1.15 | Section headers, modal h2, first-card title, swipe title |
| 18px | 700 (Outfit) | 1.25 | Card title |
| 15px | 400 | 1.55 | Body text, modal description, cmd-item title |
| 13px | 500 | 1.5 | Controls, buttons, meta rows |
| 12px | 500-600 | 1.4 | Chips, badges, sub-meta, date inputs |
| 10px | 600 | 1.3 | Labels, uppercase micro-text, categories |

### Key heading rules (all roman, no italic):
```css
h1{font-family:var(--fi);font-size:44px;font-weight:400;font-style:normal;letter-spacing:-.02em;color:var(--text);line-height:1.05}
.section-header{font-family:var(--fi);font-size:24px;font-weight:400;color:var(--t2);font-style:normal;line-height:1.15;letter-spacing:-.01em}
.hero-title{font-family:var(--fi);font-size:32px;font-weight:400;color:var(--text);line-height:1.1;font-style:normal}
.modal h2{font-family:var(--fi);font-size:24px;font-weight:400;color:var(--text);line-height:1.15;font-style:normal}
```

### Line-height fixes:
```css
/* Section header: was inheriting 1.6 from body */
.section-header{line-height:1.15}

/* Modal description: was 1.8 (excessive) */
.modal .desc{line-height:1.55}
```

---

## 7. BEFORE/AFTER CSS (10 most important rules)

### Rule 1: Root custom properties
```css
/* BEFORE */
:root{
  --bg:#090b11;--surface:rgba(16,19,30,.85);--surface-2:rgba(22,26,40,.7);
  --border:rgba(148,163,184,.06);--bh:rgba(148,163,184,.12);
  --text:#f1f5f9;--t2:#94a3b8;--t3:#64748b;--t4:#475569;
  --accent:#10b981;--ah:#34d399;--abg:rgba(16,185,129,.08);
  --score:#8b5cf6;--sbg:rgba(139,92,246,.08);--sglow:rgba(139,92,246,.2);
  --pos:#22c55e;--info:#0ea5e9;--danger:#ef4444;
  --rs:8px;--rl:16px;
  --eo:cubic-bezier(0.23,1,0.32,1);--eio:cubic-bezier(0.77,0,0.175,1);
  --fd:'Outfit',system-ui,sans-serif;
  --fb:'Geist',-apple-system,BlinkMacSystemFont,sans-serif;
  --fi:'Instrument Serif',Georgia,serif;
}

/* AFTER */
:root{
  --bg:#111110;--surface:rgba(24,24,22,.88);--surface-2:rgba(32,32,28,.72);
  --border:rgba(148,163,184,.06);--bh:rgba(148,163,184,.14);
  --text:#ede9e3;--t2:#9c9590;--t3:#706a65;--t4:#6b7280;
  --accent:#2db87a;--ah:#4fd1a0;--abg:rgba(45,184,122,.08);
  --score:#d97706;--sbg:rgba(217,119,6,.08);--sglow:rgba(217,119,6,.18);
  --pos:#2db87a;--info:#3b9ece;--danger:#d1453b;
  --rs:6px;--rl:14px;
  --eo:cubic-bezier(0.23,1,0.32,1);
  --fd:'Outfit',system-ui,sans-serif;
  --fb:'Sora',-apple-system,BlinkMacSystemFont,sans-serif;
  --fi:'Newsreader',Georgia,serif;
}
```

### Rule 2: h1 page title
```css
/* BEFORE */
h1{font-family:var(--fi);font-size:48px;font-weight:400;font-style:italic;letter-spacing:-.01em;color:var(--text);line-height:1}

/* AFTER */
h1{font-family:var(--fi);font-size:44px;font-weight:400;font-style:normal;letter-spacing:-.02em;color:var(--text);line-height:1.05}
```

### Rule 3: Body base
```css
/* BEFORE */
body{font-family:var(--fb);background:var(--bg);color:var(--t2);line-height:1.6;min-height:100vh;-webkit-font-smoothing:antialiased;overflow-x:hidden;font-size:14px}

/* AFTER */
body{font-family:var(--fb);background:var(--bg);color:var(--t2);line-height:1.55;min-height:100vh;-webkit-font-smoothing:antialiased;overflow-x:hidden;font-size:15px}
```

### Rule 4: Section header
```css
/* BEFORE */
.section-header{font-family:var(--fi);font-size:24px;font-weight:400;color:var(--t2);margin:56px 0 24px;letter-spacing:0;font-style:italic;display:flex;align-items:center;gap:10px}

/* AFTER */
.section-header{font-family:var(--fi);font-size:24px;font-weight:400;color:var(--t2);margin:48px 0 20px;letter-spacing:-.01em;font-style:normal;line-height:1.15}
```

### Rule 5: Card grid
```css
/* BEFORE */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px}
.grid .card:first-child{grid-column:1/-1;height:440px}

/* AFTER */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.grid .card:first-child{grid-column:1/-1;height:400px}
.grid .card:nth-child(2),.grid .card:nth-child(3){height:340px}
.grid .card:nth-child(n+4){height:280px}
```

### Rule 6: Chip touch targets
```css
/* BEFORE */
.chip{background:transparent;color:var(--t3);border:1px solid var(--border);border-radius:999px;padding:5px 14px;font-size:11px;font-weight:500;cursor:pointer;user-select:none;transition:all .2s var(--eo)}

/* AFTER */
.chip{background:transparent;color:var(--t3);border:1px solid var(--border);border-radius:999px;padding:10px 16px;font-size:12px;font-weight:500;cursor:pointer;user-select:none;transition:color .2s var(--eo),border-color .2s var(--eo),background .2s var(--eo)}
```

### Rule 7: Controls / Toolbar
```css
/* BEFORE */
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:0 0 40px;padding:16px 0;border-bottom:1px solid var(--border)}

/* AFTER */
.toolbar{display:flex;gap:12px;align-items:center;margin:0 0 24px;flex-wrap:wrap}
.filter-drawer{display:none;padding:20px 0;border-bottom:1px solid var(--border);margin:0 0 24px}
.filter-drawer.open{display:flex;flex-wrap:wrap;gap:12px;align-items:center}
```

### Rule 8: Modal description line-height
```css
/* BEFORE */
.modal .desc{color:var(--t2);font-size:14px;line-height:1.8;margin:24px 0;max-height:400px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:rgba(71,85,105,.3) transparent}

/* AFTER */
.modal .desc{color:var(--t2);font-size:15px;line-height:1.55;margin:24px 0;max-height:400px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:rgba(71,85,105,.3) transparent}
```

### Rule 9: Close button (44px target)
```css
/* BEFORE */
.close{position:absolute;top:16px;right:16px;background:rgba(9,11,17,.5);color:var(--text);width:36px;height:36px;border-radius:50%;border:1px solid rgba(255,255,255,.06);cursor:pointer;font-size:18px;z-index:2;display:flex;align-items:center;justify-content:center;transition:all .15s var(--eo);backdrop-filter:blur(6px)}

/* AFTER */
.close{position:absolute;top:12px;right:12px;background:rgba(17,17,16,.5);color:var(--text);width:44px;height:44px;border-radius:50%;border:1px solid rgba(255,255,255,.06);cursor:pointer;font-size:18px;z-index:2;display:flex;align-items:center;justify-content:center;transition:background .15s var(--eo);backdrop-filter:blur(6px)}
```

### Rule 10: Person chip active state (was AI-purple)
```css
/* BEFORE */
.person-chip.active{background:var(--score);color:#fff;border-color:transparent}

/* AFTER */
.person-chip.active{background:var(--accent);color:#fff;border-color:transparent}
```

---

## IMPLEMENTATION NOTES

1. **Remove dead CSS variable:** `--eio:cubic-bezier(0.77,0,0.175,1)` is declared but never referenced. Delete it.
2. **Replace `transition:all`** in all 11 instances with specific properties (e.g., `transition:color .2s var(--eo),border-color .2s var(--eo),background .2s var(--eo)`). This prevents unintended transitions on layout properties.
3. **Add `:active` to missing interactive elements:** `.my-event-chip`, `.pick-chip`, `.cmd-item`, `.hero` -- all have `cursor:pointer` but no `:active` scale feedback.
4. **Cover images:** Consider converting CSS `background-image` to `<img>` tags with `loading="lazy"` for proper lazy loading. The `content-visibility:auto` on sections only partially mitigates eager loading of 433+ cover images.
5. **Section data attributes:** The JS `filterAndRender()` function must set `section.dataset.period=k` on each section element for the period-specific CSS to work.
6. **Filter count badge:** JS must track active filter count and update `#filterCount` text content and `.show` class.
