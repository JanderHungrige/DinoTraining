---
id: 78-lato-typography
title: Lato Typography — Self-Hosted
edition: DinoTraining
depends_on: []
relates: [79-draft-sketch-controls, 54-distribution-licensing]
source_files:
  - apps/frontend/src/main.tsx
  - apps/frontend/src/look.css
  - apps/frontend/package.json
  - apps/frontend/package-lock.json
  - apps/frontend/public/THIRD_PARTY_ASSETS.md
routes: []
models: []
test_files:
  - apps/frontend/src/look.test.ts
data_flow: greenfield
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [look-and-feel, typography, fonts, licensing, offline]
path: App Shell/Look & Feel
initiative: dinotraining
wave: dinotraining-wave-10
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Only the latin subset is bundled: it covers English and German (Latin-1, umlauts and ß), but not Polish or Czech diacritics. Those fall back to the system font per glyph. Adding latin-ext costs roughly 40 KB more."
  - "The app asks for weight 600 in a few headings. Lato ships 400 and 700 here, so the browser renders those at 700, which is slightly heavier than before."
security_read_sites: []
sister_projects: []
---

# 78 — Lato Typography

## Purpose

Requested: *"Font Lato"* (https://fonts.google.com/specimen/Lato).

## Business Rules

1. **Self-hosted, never the Google CDN.** The desktop app must work offline, and a CDN
   link is a request to Google on every launch. `@fontsource/lato` 5.3.0 was installed with
   Jan's go-ahead (npm, OFL-1.1, 533 KB unpacked); Vite bundles only the files that are
   imported.
2. **Three faces, latin subset:** 400, 700 and 400 italic, about 70 KB of woff2. The
   packaged CSP's `default-src 'self'` covers bundled fonts.
3. **`font-display: swap`**, so the first paint is never blank while the font loads.
4. **Fallbacks stay:** Lato, then `system-ui`, `-apple-system`, `Segoe UI`, sans-serif.
5. **Licence:** SIL OFL 1.1, listed in `THIRD_PARTY_ASSETS.md`. The font may be bundled and
   redistributed with the app, but not sold on its own.

## Verified (2026-09-29)

- **In the running app:** body, buttons and inputs compute `Lato, system-ui, …`, and
  `document.fonts.check('16px Lato')` is true. 400 and 700 loaded, while italic stays
  unloaded until something asks for it.
- **Every font request went to the app's own origin**, and none went to Google.
- **A production `vite build`** emitted the three woff2 files (about 71 KB) plus woff
  fallbacks next to the CSS, and copied `background/` beside them, so the packaged bundle
  carries both.
- **The unit test checks** the imports and that no Google font URL appears in the entry or
  in index.html. Vitest hands CSS imports back empty, so the stylesheet rule is verified
  live rather than in jsdom.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
