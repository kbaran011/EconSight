# UI Redesign — Editorial Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Inter/IBM-blue aesthetic with the approved Editorial design system — jade green (#1a7a55), Source Serif 4 display font, warm parchment backgrounds, and CSS entrance animations.

**Architecture:** CSS custom properties defined once in `index.css` drive every colour reference. Tailwind is extended for font families only; all colours use `bg-[var(--token)]` arbitrary-value syntax. Each page is restyled independently so changes are isolated and reviewable.

**Tech Stack:** React 18, TypeScript, Tailwind CSS v3, Recharts, Vite. Verification: `npx tsc -b --noEmit` + `npx eslint src/` after each task.

**Spec:** `docs/superpowers/specs/2026-06-15-ui-redesign-design.md`

---

## File Map

| File | What changes |
|---|---|
| `frontend/index.html` | Swap Inter Google Fonts link for Source Serif 4 + DM Sans + DM Mono |
| `frontend/tailwind.config.ts` | Replace `fontFamily.sans: Inter` with DM Sans; add `serif` + `mono` families |
| `frontend/src/index.css` | Full rewrite: CSS variables, `@keyframes fadeSlideUp`, utility classes |
| `frontend/src/App.tsx` | Nav (jade bg, DataFreshness restyle), footer, page background |
| `frontend/src/pages/Dashboard.tsx` | Score card (bar replaces gauge ring, SVG fonts), trend BarChart, indicator grid |
| `frontend/src/pages/Indicators.tsx` | Series selector pills, chart colours, table |
| `frontend/src/pages/Forecasts.tsx` | Chart colours, confidence band fill values |
| `frontend/src/pages/Ask.tsx` | Input, submit button, answer card, source chips, copy button |
| `frontend/src/pages/About.tsx` | Phase cards, stack chips, CTA banner |
| `frontend/src/pages/Report.tsx` | Download card |

---

## Task 1: Foundation — Fonts, Tailwind, CSS Variables

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/src/index.css`

This task establishes every design token. All subsequent tasks depend on it.

- [ ] **Step 1: Replace Google Fonts link in `index.html`**

  Replace the current `<link>` tag that loads Inter with:

  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,600;0,8..60,700;0,8..60,900;1,8..60,400&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet" />
  ```

- [ ] **Step 2: Update `tailwind.config.ts` font families**

  Replace the entire `theme.extend` block:

  ```ts
  theme: {
    extend: {
      fontFamily: {
        sans:  ['DM Sans',       'system-ui', 'sans-serif'],
        serif: ['Source Serif 4','Georgia',   'serif'],
        mono:  ['DM Mono',       'monospace'],
      },
    },
  },
  ```

  Remove the `colors` extension entirely (brand/surface keys are no longer used).

- [ ] **Step 3: Rewrite `frontend/src/index.css`**

  Replace the entire file with:

  ```css
  @tailwind base;
  @tailwind components;
  @tailwind utilities;

  @layer base {
    :root {
      /* Surface */
      --bg:            #faf7f2;
      --surface-2:     #f5f0e8;
      --card:          #ffffff;
      --border:        #e0d8cc;
      --border-strong: #ccc4b4;

      /* Brand */
      --primary:       #1a7a55;
      --primary-dark:  #145e42;
      --accent:        #c9483a;
      --positive:      #1a6a3a;
      --negative:      #c9483a;

      /* Text */
      --text-primary:   #1a2a1a;
      --text-secondary: #4a3a28;
      --text-muted:     #8a7a60;
      --text-xmuted:    #b0a090;

      /* Nav (on jade bg) */
      --nav-text:              #f5f0e8;
      --nav-link:              #90c8a8;
      --nav-link-active-bg:    rgba(255,255,255,0.12);
      --nav-badge-bg:          rgba(201,72,58,0.15);
      --nav-badge-border:      rgba(201,72,58,0.35);
      --nav-badge-text:        #e8a898;
    }

    html {
      font-family: 'DM Sans', system-ui, sans-serif;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    body {
      background-color: var(--bg);
      color: var(--text-primary);
      font-size: 14px;
      line-height: 1.6;
    }

    * { border-color: var(--border); }
  }

  @keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  @keyframes navPulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.35; }
  }

  @layer components {
    /* Section eyebrow label */
    .section-label {
      @apply text-[9px] font-bold uppercase tracking-[0.14em] border-b pb-1.5 mb-4;
      color: var(--text-muted);
      border-color: var(--border);
      font-family: 'DM Sans', sans-serif;
    }

    /* Page eyebrow (above title) */
    .page-eyebrow {
      @apply text-[10px] font-semibold uppercase tracking-[0.12em] mb-1;
      color: var(--text-muted);
      font-family: 'DM Sans', sans-serif;
    }

    /* Indicator card stat label */
    .stat-label {
      @apply text-[9px] font-bold uppercase tracking-[0.1em] mb-1.5;
      color: var(--text-muted);
      font-family: 'DM Sans', sans-serif;
    }

    /* Indicator card value */
    .stat-value {
      @apply text-[20px] font-bold leading-tight tracking-tight;
      color: var(--text-primary);
      font-family: 'Source Serif 4', serif;
    }

    /* Delta badge */
    .delta {
      @apply text-[10px] font-medium mt-0.5;
      font-family: 'DM Mono', monospace;
    }
    .delta-up-good { color: var(--positive); }
    .delta-up-bad  { color: var(--negative); }
    .delta-dn-good { color: var(--positive); }
    .delta-neutral { color: var(--text-xmuted); }

    /* White card base */
    .ed-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
    }

    /* Table cells */
    .table-th {
      @apply text-[9px] font-bold uppercase tracking-[0.1em] py-2.5 px-4 text-left border-b whitespace-nowrap;
      color: var(--text-muted);
      border-color: var(--border);
    }
    .table-td {
      @apply text-[13px] py-2.5 px-4 border-b;
      color: var(--text-secondary);
      border-color: var(--border);
    }

    /* Nav live dot */
    .nav-live-dot {
      @apply w-1.5 h-1.5 rounded-full;
      background: #4ade80;
      animation: navPulse 2s ease-in-out infinite;
    }
  }
  ```

- [ ] **Step 4: Verify TypeScript + lint**

  ```bash
  cd frontend && npx tsc -b --noEmit && npx eslint src/
  ```

  Expected: no errors.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/index.html frontend/tailwind.config.ts frontend/src/index.css
  git commit -m "feat: editorial design tokens — Source Serif 4, DM Sans, jade palette"
  ```

---

## Task 2: Navigation & App Shell

**Files:**
- Modify: `frontend/src/App.tsx`

The nav sits on every page. This task also updates the footer and page background wrapper.

- [ ] **Step 1: Update the `Nav` function in `App.tsx`**

  Replace the entire `Nav` function (keep imports intact). The key changes:
  - Nav `div` background: `bg-[var(--primary)]` height `h-[52px]`
  - Logo chip: `bg-[var(--accent)]` text-white rounded-[4px] w-7 h-7
  - Title: `font-serif font-bold text-[16px]` color `text-[var(--nav-text)]`
  - Eyebrow "Canadian Economic Intelligence": hidden on small screens, `text-[10px] font-medium uppercase tracking-[0.08em]` color `text-[var(--nav-link)]`, separated from title by a `w-px h-4 bg-white/15` divider
  - Nav links: `text-[12px] font-medium` color `text-[var(--nav-link)]`; active: `bg-[var(--nav-link-active-bg)] text-[var(--nav-text)]`
  - Health score badge: `bg-[var(--nav-badge-bg)] border border-[var(--nav-badge-border)] text-[var(--nav-badge-text)] font-mono text-[11px] px-3 py-1 rounded-full`
  - Live dot: use `.nav-live-dot` class
  - **DataFreshness pill restyle**: change the "As of" pill className to `bg-[var(--nav-badge-bg)] border border-[var(--nav-badge-border)] text-[var(--nav-link)] text-[11px]`; change the refresh button className to `w-7 h-7 rounded-full bg-white/8 text-[var(--nav-link)] hover:bg-white/15 hover:ring-1 hover:ring-[var(--nav-link)] transition-colors`
  - Mobile menu: same `bg-[var(--primary)]` background, `border-white/10` top border

- [ ] **Step 2: Update footer**

  Footer background: `bg-[var(--primary)]`. Footer text / links: use `text-[var(--nav-link)]` for secondary text, `text-[var(--nav-text)]` for primary.

- [ ] **Step 3: Update main page wrapper**

  The `<main>` wrapper in `App.tsx`: ensure `body` background is `var(--bg)` (already set in CSS). Page content wrapper padding: `px-4 sm:px-8 py-8`.

- [ ] **Step 4: Verify TypeScript + lint**

  ```bash
  cd frontend && npx tsc -b --noEmit && npx eslint src/
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/App.tsx
  git commit -m "feat: nav + shell — jade authority bar, DataFreshness restyle, editorial footer"
  ```

---

## Task 3: Dashboard Page

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

Three sub-components to restyle: `ScoreGauge`, the trend chart, and indicator cards.

- [ ] **Step 1: Update page header**

  Add `page-eyebrow` span above the `<h1>`. Change `<h1>` to `font-serif font-bold text-[28px] tracking-tight text-[var(--text-primary)]`.

- [ ] **Step 2: Update `ScoreGauge` SVG**

  - Change both `<text>` elements: `fontFamily="Source Serif 4, serif"` (inline SVG attribute — CSS does not cascade here)
  - Score value text: `fill="var(--primary)"` (currently uses hardcoded colour)
  - Gauge stroke: `stroke={ring}` — update `scoreColor()` to return jade/amber/red values matching the new palette:
    ```ts
    function scoreColor(s: number) {
      if (s >= 7) return { ring: '#1a7a55', label: 'Strong' }
      if (s >= 5) return { ring: '#d97706', label: 'Moderate' }
      return       { ring: '#c9483a',        label: 'Weak' }
    }
    ```
  - Wrap gauge card in `ed-card p-6`

- [ ] **Step 3: Replace health score trend LineChart with BarChart**

  Import `Bar, BarChart, Cell` from recharts (replace `LineChart, Line`). Render the last 18 months as bars:
  - Each bar uses `fill` `#1a7a55` at `opacity="0.2"` for all bars except the last, which gets `opacity="1"`
  - `CartesianGrid` `vertical={false}` stroke `var(--surface-2)`
  - Axis `tick` style: `{ fontSize: 10, fill: 'var(--text-xmuted)', fontFamily: 'DM Mono, monospace' }`
  - Tooltip: restyle `ChartTooltip` — white bg, `border-[var(--border)]`, value in `font-serif font-bold text-[var(--primary)]`
  - Wrap chart card in `ed-card p-6 lg:col-span-2`

- [ ] **Step 4: Restyle indicator cards**

  For each card in the `INDICATORS.map()` block:
  - Card wrapper: `ed-card p-4 flex flex-col gap-2 transition-all duration-150 hover:-translate-y-px hover:shadow-[0_4px_16px_rgba(26,122,85,0.08)]`
  - Top border: `borderTop: \`3px solid \${invert ? 'var(--accent)' : 'var(--primary)'}\`` as inline style
  - Label: use `.stat-label` class
  - Value: use `.stat-value` class; unit span: `text-[14px] font-normal text-[var(--text-muted)]`
  - Delta: use `.delta` + `.delta-up-good` / `.delta-up-bad` / `.delta-dn-good` / `.delta-neutral` classes (pick based on `good`/`bad` booleans already computed in the render)
  - Add staggered entrance animation: `style={{ animation: 'fadeSlideUp 0.4s ease-out both', animationDelay: \`\${index * 60}ms\`` }}` (add `index` to the `.map((indicator, index) =>` callback)
  - Sparkline container: `h-7 rounded bg-[var(--surface-2)] mt-1 overflow-hidden`

- [ ] **Step 5: Add `section-label` to each section heading**

  Replace existing `<p className="section-title">` with `<p className="section-label">`.

- [ ] **Step 6: Verify TypeScript + lint**

  ```bash
  cd frontend && npx tsc -b --noEmit && npx eslint src/
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/pages/Dashboard.tsx
  git commit -m "feat: dashboard — editorial score card, bar chart trend, animated indicator grid"
  ```

---

## Task 4: Indicators Page

**Files:**
- Modify: `frontend/src/pages/Indicators.tsx`

- [ ] **Step 1: Restyle series selector pills**

  In the pill/button strip, replace current `bg-blue-700`/`bg-white` conditional with:
  ```tsx
  className={`px-3 py-1 rounded-[6px] text-[12px] font-medium border transition-colors ${
    isActive
      ? 'bg-[var(--primary)] text-white border-transparent'
      : 'bg-[var(--surface-2)] text-[var(--text-secondary)] border-[var(--border)] hover:border-[var(--border-strong)]'
  }`}
  ```

- [ ] **Step 2: Restyle chart**

  - Wrap chart in `ed-card p-6`
  - `CartesianGrid` `vertical={false}` stroke `var(--surface-2)`
  - All `<Line>` components: keep existing `color` from `SERIES` array but replace blue entries with `#1a7a55` (primary) and second series with `#c9483a` (accent). Update the `SERIES` colour values directly.
  - Axis tick style: `{ fontSize: 10, fill: 'var(--text-xmuted)', fontFamily: 'DM Mono, monospace' }`
  - Custom tooltip: white bg, `border border-[var(--border)]`, value in `font-serif font-bold text-[var(--text-primary)]`, label in `text-[var(--text-muted)]`

- [ ] **Step 3: Restyle data table**

  - Table wrapper: `ed-card overflow-hidden`
  - `thead`: `bg-[var(--surface-2)]`
  - Use `.table-th` and `.table-td` classes (already defined in `index.css`)
  - Remove old `text-slate-*` / `border-slate-*` classes

- [ ] **Step 4: Verify TypeScript + lint**

  ```bash
  cd frontend && npx tsc -b --noEmit && npx eslint src/
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/pages/Indicators.tsx
  git commit -m "feat: indicators — editorial pills, jade chart colours, restyled table"
  ```

---

## Task 5: Forecasts Page

**Files:**
- Modify: `frontend/src/pages/Forecasts.tsx`

- [ ] **Step 1: Restyle target selector pills**

  Same pattern as Indicators (Task 4, Step 1) — active: `bg-[var(--primary)] text-white`, inactive: `bg-[var(--surface-2)]`.

- [ ] **Step 2: Restyle chart and confidence band**

  - Wrap chart in `ed-card p-6`
  - Main forecast `<Line>`: `stroke="#1a7a55"` `strokeWidth={2}`
  - Scenario lines: Base `stroke="#1a7a55"` at 60% opacity, Upside `stroke="#1a6a3a"`, Downside `stroke="#c9483a"`
  - P90 `<Area>`: `fill="rgba(26,122,85,0.10)"` `stroke="none"`
  - P10 `<Area>`: `fill="#ffffff"` `stroke="none"` (white overlay to produce hollow band)
  - Grid + axis tick styles same as Task 4 Step 2
  - Custom tooltip: same editorial style

- [ ] **Step 3: Restyle detail table**

  Same as Indicators table (Task 4 Step 3).

- [ ] **Step 4: Verify TypeScript + lint**

  ```bash
  cd frontend && npx tsc -b --noEmit && npx eslint src/
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/pages/Forecasts.tsx
  git commit -m "feat: forecasts — jade confidence band, editorial chart, restyled table"
  ```

---

## Task 6: Ask Page

**Files:**
- Modify: `frontend/src/pages/Ask.tsx`

- [ ] **Step 1: Restyle input and submit button**

  - Input `<input>`: `bg-white border border-[var(--border)] rounded-lg px-4 py-2.5 text-[14px] font-sans text-[var(--text-primary)] placeholder-[var(--text-xmuted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent flex-1`
  - Submit button: `bg-[var(--primary)] text-white font-sans font-semibold text-[13px] px-5 py-2.5 rounded-[6px] hover:bg-[var(--primary-dark)] transition-colors disabled:opacity-50`

- [ ] **Step 2: Restyle example question chips**

  - Chip: `bg-[var(--surface-2)] border border-[var(--border)] text-[var(--text-secondary)] text-[12px] px-3 py-1.5 rounded-[6px] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-colors cursor-pointer`

- [ ] **Step 3: Restyle `AnswerCard`**

  - Card wrapper: `ed-card p-5 border-l-[3px] border-l-[var(--primary)]`
  - Question text: `font-serif font-semibold text-[16px] text-[var(--text-primary)]`
  - Answer text: `font-serif text-[15px] text-[var(--text-secondary)] leading-relaxed`
  - Method badge: `bg-[var(--surface-2)] text-[var(--text-muted)] text-[10px] font-mono px-2 py-0.5 rounded`
  - Source chips: `bg-[var(--surface-2)] border border-[var(--border)] text-[10px] font-mono text-[var(--text-muted)] px-2 py-0.5 rounded`

- [ ] **Step 4: Restyle `CopyButton`**

  `text-[11px] font-medium border rounded px-2 py-0.5 transition-colors` with `text-[var(--text-muted)] border-[var(--border)] hover:text-[var(--primary)] hover:border-[var(--primary)]`

- [ ] **Step 5: Verify TypeScript + lint**

  ```bash
  cd frontend && npx tsc -b --noEmit && npx eslint src/
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/pages/Ask.tsx
  git commit -m "feat: ask page — jade input focus ring, editorial answer cards, restyled chips"
  ```

---

## Task 7: About & Report Pages

**Files:**
- Modify: `frontend/src/pages/About.tsx`
- Modify: `frontend/src/pages/Report.tsx`

- [ ] **Step 1: Restyle About phase cards**

  - Each phase card: `ed-card p-6 border-l-[3px]` — alternate `border-l-[var(--primary)]` and `border-l-[var(--accent)]` based on index parity
  - Phase number: `font-serif font-bold text-[32px] text-[var(--text-xmuted)]`
  - Title: `font-serif font-bold text-[18px] text-[var(--text-primary)]`
  - Status badge (complete): `bg-[var(--primary)]/10 text-[var(--primary)] border border-[var(--primary)]/20`
  - Status badge (upcoming): `bg-[var(--surface-2)] text-[var(--text-muted)] border border-[var(--border)]`
  - List items: `text-[13px] text-[var(--text-secondary)]`

- [ ] **Step 2: Restyle About tech stack chips**

  Each chip: `bg-[var(--surface-2)] border border-[var(--border)] text-[12px] text-[var(--text-secondary)] px-3 py-1 rounded-[4px]`

- [ ] **Step 3: Restyle About CTA banner**

  - Replace `bg-blue-700` with `bg-[var(--primary)]`
  - Replace `text-blue-700` link colour with `text-[var(--primary)]`
  - CTA card background (if separate from the banner): `bg-[var(--primary)]`

- [ ] **Step 4: Restyle Report page**

  - Main download card: `ed-card p-8 max-w-lg mx-auto`
  - Download button: `bg-[var(--primary)] text-white font-semibold px-6 py-3 rounded-[6px] hover:bg-[var(--primary-dark)] transition-colors`
  - Description text: `text-[var(--text-secondary)]`
  - Section labels: use `.section-label` class

- [ ] **Step 5: Verify TypeScript + lint**

  ```bash
  cd frontend && npx tsc -b --noEmit && npx eslint src/
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/pages/About.tsx frontend/src/pages/Report.tsx
  git commit -m "feat: about + report — editorial phase cards, jade CTA, restyled download"
  ```

---

## Task 8: Push & Verify Live

- [ ] **Step 1: Push to main**

  ```bash
  git push origin main
  ```

- [ ] **Step 2: Wait for Railway deploy**

  Watch for frontend service to finish building (≈90 seconds):
  ```bash
  cd "/Users/barandursun/AI PROJECT/EconSight" && railway status
  ```

- [ ] **Step 3: Smoke-test live endpoints**

  ```bash
  curl -s -o /dev/null -w "%{http_code}" https://frontend-production-f45a3.up.railway.app/dashboard
  curl -s -o /dev/null -w "%{http_code}" https://econsight-production.up.railway.app/api/indicators
  ```

  Both should return `200`.

- [ ] **Step 4: Visual check**

  Open `https://frontend-production-f45a3.up.railway.app/dashboard` and verify:
  - Jade green navigation bar
  - Source Serif 4 on score number and page title
  - Parchment background (not white/grey)
  - Indicator cards with coloured top borders
  - No blue IBM colours anywhere visible
