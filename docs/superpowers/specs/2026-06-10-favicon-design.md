# EconSight — Favicon Redesign

**Date:** 2026-06-10  
**Status:** Approved  
**Goal:** Replace the unrelated purple lightning-bolt favicon with the EconSight ES monogram so the browser tab matches the nav logo.

---

## Change

**File:** `frontend/public/favicon.svg`

Replace the entire file with a 32×32 SVG: blue rounded square (`fill="#1d4ed8"`, `rx="6"`) with centred white bold "ES" text, matching the nav logo in `App.tsx`.

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#1d4ed8"/>
  <text x="16" y="22" text-anchor="middle" font-size="13" font-weight="700"
        font-family="Inter, system-ui, sans-serif" fill="white" letter-spacing="-0.5">ES</text>
</svg>
```

No other files change. `frontend/index.html` already has `<link rel="icon" type="image/svg+xml" href="/favicon.svg" />`.

---

## Success Criteria

- Browser tab shows the blue ES square instead of the purple lightning bolt.
- Nav logo and favicon are visually consistent.
