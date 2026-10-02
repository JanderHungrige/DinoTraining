---
id: 164-settings-tab
title: Settings Tab — Light, Dark or Like the System; the Moving Background; the Background's Credit
edition: DinoTraining
depends_on: [77-app-background-layer, 157-sketch-everywhere, 163-forest-background]
relates: [80-legibility-and-motion-pass, 111-i18n-framework]
source_files:
  - apps/frontend/src/tabs/SettingsTab.tsx
  - apps/frontend/src/components/AppearancePanel.tsx
  - apps/frontend/src/lib/look.tsx
  - apps/frontend/src/look.css
  - apps/frontend/src/tabs/tabs.ts
  - apps/frontend/src/App.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
  - apps/frontend/src/i18n/en/app.ts
  - apps/frontend/src/i18n/de/app.ts
  - apps/frontend/vite.config.ts
  - scripts/check_background_contrast.py
routes: []
models: []
test_files:
  - apps/frontend/src/tabs/SettingsTab.test.tsx
  - apps/frontend/src/sketch.test.ts
  - apps/frontend/src/tabs/IntroTab.test.tsx
data_flow: greenfield
last_synced: 2026-10-02
status: complete
phase: all
mdd_version: 11
tags: [settings, theme, light-mode, dark-mode, background, credits, look-and-feel]
path: UI/Settings
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 164 — Settings Tab

## Jan (2026-10-02)

- "We'll also do a settings tab with dark / light mode, animation on/off (that's
  somewhere else right now), the Pexels credit
  (https://www.pexels.com/video/trees-in-the-forest-5121476/)."

## The tab

- **"Settings" / "Einstellungen"**, the last tab, after the loop. The intro does not list it
  as a step, and its tests say so.
- **Appearance:**
  - **Colour scheme:** like the system (default), dark, light.
    - Applied as `data-theme` on `<html>` by `LookProvider`.
    - "System" is resolved there from `prefers-color-scheme`, live.
    - Remembered as `look.theme`.
  - **Animated background:** the switch from doc 77, moved here from Models & Datasets ›
    Official models.
  - The reduced-motion note as before.
- **Credits:** "Trees in the forest", a video from Pexels (Pexels License), linked.
- **The language** stays in the top bar, where every tab can change it.

## The light theme

- **One block, `:root[data-theme='light']` in `look.css`.** It outranks the dark `:root`
  tokens wherever they are; there is no OS media query in any stylesheet.
- **Measured over the forest** (brightest pixel 183 after doc 163's tone-mapping):
  - a light scrim of 0.25/0.2;
  - panels at 75 % and the header at 85 %;
  - the text colours a shade darker than plain light-on-white (doc 157's set);
  - lowest contrast 4.63:1, and the forest still shows through.
  - A dark scrim with 75 % panels failed (4.08).
- **The sketch hand** follows by itself: its ink is `--text`.
- `check_background_contrast.py` checks both schemes again.

## Found on the way: the look tests read empty stylesheets

- **The problem:**
  - Vitest hands every `.css` to a test as an empty string, `?raw` included.
  - Three of doc 157's checks (no light override, every sketched class still exists)
    passed without seeing a rule; only the load order in `main.tsx` was really checked.
- **Fixed:** `vite.config.ts` processes `.css?raw` imports only, so the look tests read the
  real files and every other test stays as light as before.
- **Proven:**
  - the files now arrive with their content (`styles.css` 75 KB, not 0);
  - a class added to `sketch.css` that exists nowhere else makes the test fail.

## Verified (2026-10-02)

- **Tests:** 1205 frontend tests, TypeScript clean. New:
  - the system scheme, followed live;
  - a choice applied at once, remembered, and winning over the system;
  - the switch and the credit link;
  - German.
- **The running UI:**
  - Settings shows the three schemes, the switch and the credit;
  - choosing "Light" turns the page light at once (`data-theme="light"`, text
    `rgb(26,29,35)`, panel at 0.75) and is stored;
  - Models & Datasets in light: dark sketch ink on light, green wash on the open tabs;
  - the switch is gone from Models & Datasets.
- **One full run** had a timing failure in `ParameterForm.test.tsx`. It passes alone and in
  three further full runs.
