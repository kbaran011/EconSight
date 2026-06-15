# EconSight UI Redesign — Design Spec

**Date:** 2026-06-15  
**Status:** Approved  

---

## Overview

Replace the current Inter-font IBM-blue consulting aesthetic with a distinctive Editorial design system: warm parchment backgrounds, Source Serif 4 display typography, a jade green primary palette, and CSS entrance animations. The goal is a portfolio-quality UI that reads as intentionally designed — not AI-generated boilerplate.

---

## Design Tokens

### Colour

```css
--bg:           #faf7f2;   /* warm parchment page background */
--surface-2:    #f5f0e8;   /* secondary surfaces, chart backgrounds */
--card:         #ffffff;   /* card backgrounds */
--border:       #e0d8cc;   /* card/section borders */
--border-strong: #ccc4b4;  /* dividers, table rows */

--primary:      #1a7a55;   /* jade — nav bg, score numbers, positive accents */
--primary-dark: #145e42;   /* hover states on nav links */
--accent:       #c9483a;   /* brick red — logo chip, negative indicators */
--positive:     #1a6a3a;   /* positive delta text */
--negative:     #c9483a;   /* negative delta text */

--text-primary: #1a2a1a;   /* headings, card values */
--text-secondary: #4a3a28; /* body text */
--text-muted:   #8a7a60;   /* labels, eyebrows, captions */
--text-xmuted:  #b0a090;   /* placeholder, axis labels */

/* Nav-specific (on dark jade bg) */
--nav-text:     #f5f0e8;
--nav-link:     #90c8a8;
--nav-link-active-bg: rgba(255,255,255,0.12);
--nav-badge-bg: rgba(201,72,58,0.15);
--nav-badge-border: rgba(201,72,58,0.35);
--nav-badge-text: #e8a898;
```

### Typography

| Role | Font | Weight | Size |
|---|---|---|---|
| Page titles | Source Serif 4 | 700 | 26–28px |
| Score / large numbers | Source Serif 4 | 700 | 48–56px |
| Card values | Source Serif 4 | 700 | 18–22px |
| Section eyebrows | DM Sans | 700 | 9px, uppercase, tracked |
| Body / labels | DM Sans | 400–600 | 11–14px |
| Data deltas / badges | DM Mono | 500 | 10–12px |
| Axis labels / timestamps | DM Mono | 400 | 10px |

Google Fonts import:
```
Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,600;0,8..60,700;0,8..60,900;1,8..60,400
DM+Sans:wght@300;400;500;600
DM+Mono:wght@400;500
```

### Spacing & Shape

- Card border-radius: `8px`
- Small elements (badges, pills): `4–6px`
- Card padding: `20–24px`
- Section gap: `16px`
- Page padding: `32px` (desktop), `16px` (mobile)
- Card border: `1px solid var(--border)`
- Card top accent border: `3px solid var(--primary)` (or `--accent` for negative indicators)

---

## Component Specs

### Navigation

- Background: `var(--primary)` (#1a7a55)
- Height: 52px, `sticky top-0 z-20`
- Logo chip: `var(--accent)` bg, white text, 4px radius
- Title: Source Serif 4 700, `var(--nav-text)`
- Eyebrow: "Canadian Economic Intelligence", DM Sans 500 10px, `var(--nav-link)`, uppercase
- Links: DM Sans 500 12px, `var(--nav-link)`, active state gets `var(--nav-link-active-bg)` bg + `var(--nav-text)` colour
- Health score badge (right): `var(--nav-badge-bg/border/text)`, DM Mono, 20px border-radius
- Live dot: 6px circle, `#4ade80`, CSS pulse animation
- Mobile: hamburger menu below `md:`, same dark jade bg
- **DataFreshness widget**: merge into the right-side cluster; restyle the "As of YYYY-MM" pill to use `var(--nav-badge-bg)` bg + `var(--nav-badge-border)` border + `var(--nav-link)` text; restyle the refresh button to `rgba(255,255,255,0.08)` bg, `var(--nav-link)` icon, jade hover ring — so it sits cohesively on the jade nav rather than clashing with slate/blue styles

### Page Layout

- Max-width: 1200px, centered
- Page header: title (Source Serif 4 700 28px) + eyebrow above + subtitle below + data period badge right-aligned
- Section labels: 9px DM Sans 700 uppercase tracked, `var(--text-muted)`, 1px bottom border `var(--border)`, `mb-4`

### Dashboard — Health Score Card

- White card, 8px radius, left column (~280px)
- Large score: Source Serif 4 700 56px, colour `var(--primary)`
- `/ 10` in Source Serif 4 400 18px, `var(--text-xmuted)`
- Status pill below: jade bg-tint + border, dot + text
- Progress bar: 4px, `var(--surface-2)` track, jade fill, animated width on mount (0.6s ease-out)
- Component sub-rows: 4 items, name + mini bar + value, all 10px DM Sans/Mono
- **SVG gauge `<text>` elements**: update the inline `fontFamily` attribute from `"Inter, sans-serif"` to `"Source Serif 4, serif"` on both the score value and "out of 10" text nodes — CSS font-family does not cascade into SVG text; inline attributes are required

### Dashboard — Trend Chart

- White card, right column (flex-1)
- Uses Recharts `BarChart` (replacing current LineChart) — cleaner in editorial style
- Bar fill: `var(--primary)` at 20% opacity for history, 100% for latest bar
- Grid: horizontal only, `var(--surface-2)` stroke
- Axes: DM Mono 10px, `var(--text-xmuted)`
- Tooltip: white card, jade text
- Summary stats below chart (change since start, MoM delta)

### Indicator Cards

Grid: `grid-cols-2 md:grid-cols-4`, gap 10px

Each card:
- White background, 1px border `var(--border)`, 6px radius
- **3px top border**: use the existing `invert` flag on each entry in the `INDICATORS` array — `invert: true` → `var(--accent)` (#c9483a) top border; `invert: false` / undefined → `var(--primary)` (#1a7a55) top border
- Label: 9px DM Sans 700 uppercase `var(--text-muted)`
- Value: Source Serif 4 700 20px `var(--text-primary)`, unit in 14px 400 `var(--text-muted)`
- Delta: DM Mono 500 10px, colour `var(--positive)` / `var(--negative)` / `var(--text-xmuted)`
- Sparkline: 28px tall, `var(--surface-2)` bg, single gradient line
- Hover: `translateY(-1px)` + `box-shadow: 0 4px 16px rgba(26,122,85,0.08)`

### Charts (Indicators / Forecasts pages)

- Background: white card
- Primary series: `var(--primary)` (#1a7a55)
- Secondary series: `var(--accent)` (#c9483a)
- Grid: `var(--surface-2)`, horizontal lines only
- Axis text: DM Mono 10px, `var(--text-xmuted)`
- Tooltip: white bg, jade border-left accent, Source Serif 4 value
- P10/P90 confidence band (Forecasts): keep the existing two-`<Area>` hollow-band pattern; change P90 `<Area>` fill to `rgba(26,122,85,0.10)` and P10 `<Area>` fill to `#ffffff` (white overlay) — this produces a jade-tinted band without restructuring the chart

### Indicators — Series Selector

- The pill/button strip above the chart selects the active indicator series
- **Active pill**: `bg-[var(--primary)]` white text, 6px radius
- **Inactive pill**: `bg-[var(--surface-2)]` bg, `var(--text-secondary)` text, `1px solid var(--border)`, hover → `var(--border-strong)` border

### Ask Page

- Question input: the current implementation uses a single-line `<input type="text">` — keep it as `<input>`, do not convert to `<textarea>`; restyle with white bg, `var(--border)` border, 8px radius, DM Sans 14px, jade focus ring (`outline-color: var(--primary)`)
- Submit button: jade bg, white DM Sans 600, 6px radius
- Answer panel: white card with 3px jade left border, Source Serif 4 for answer text
- Source chips: `var(--surface-2)` bg, DM Mono 10px

### About Page

- Phase cards: white, left border accent cycling jade/red
- Tech stack grid: `var(--surface-2)` bg chips
- **CTA banner**: replace `bg-blue-700` with `bg-[var(--primary)]`; replace `text-blue-700` link colour with `text-[var(--primary)]`

---

## Motion

All animations are CSS-only (no additional libraries required).

| Element | Animation | Duration |
|---|---|---|
| Indicator cards | `fadeSlideUp` (opacity 0→1, translateY 8px→0) staggered 60ms per card | 0.4s ease-out |
| Score progress bar | CSS `width` transition on mount | 0.6s ease-out |
| Score gauge | `stroke-dasharray` SVG transition | 0.8s ease-out |
| Top row cards | `fadeSlideUp` 0ms + 80ms delay | 0.4s |
| Sparklines | `opacity` 0→1 | 0.3s, 0.2s delay |
| Nav live dot | `opacity` pulse loop | 2s infinite |
| Card hover | `transform` + `box-shadow` | 0.15s ease |

```css
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

---

## Files to Change

| File | Change |
|---|---|
| `frontend/index.html` | Replace Inter with Source Serif 4 + DM Sans + DM Mono |
| `frontend/tailwind.config.ts` | Extend `fontFamily`: `serif: ['Source Serif 4', 'serif']`, `sans: ['DM Sans', 'sans-serif']`, `mono: ['DM Mono', 'monospace']`; extend `colors` with the token palette |
| `frontend/src/index.css` | Full CSS variable + utility class rewrite |
| `frontend/src/App.tsx` | Nav (jade bg, DataFreshness restyle, new layout), Footer, page wrapper |
| `frontend/src/pages/Dashboard.tsx` | Score card (SVG font attrs), trend bar chart, indicator grid |
| `frontend/src/pages/Indicators.tsx` | Series selector pills, chart colours, table styling |
| `frontend/src/pages/Forecasts.tsx` | Chart colours, confidence band fill colours |
| `frontend/src/pages/Ask.tsx` | Input + answer panel styling |
| `frontend/src/pages/About.tsx` | Phase cards, stack chips, CTA banner |
| `frontend/src/pages/Report.tsx` | Download card styling |

---

## Out of Scope

- No new features or data changes
- No changes to backend, API, or chart data shape
- No new npm dependencies (animations via CSS only)
- Tailwind config changes limited to extending theme tokens
