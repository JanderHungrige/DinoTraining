---
id: 165-background-choice
title: Background Choice — Every Background Tried, in Settings, Each With Its Own Scrim and Blur
edition: DinoTraining
depends_on: [163-forest-background, 164-settings-tab]
relates: [77-app-background-layer, 80-legibility-and-motion-pass, 133-download-site]
source_files:
  - apps/frontend/src/lib/backgrounds.ts
  - apps/frontend/src/lib/look.tsx
  - apps/frontend/src/components/BackgroundVideo.tsx
  - apps/frontend/src/components/AppearancePanel.tsx
  - apps/frontend/src/look.css
  - apps/frontend/src/i18n/en/app.ts
  - apps/frontend/src/i18n/de/app.ts
  - apps/frontend/public/background/
  - scripts/check_background_contrast.py
routes: []
models: []
test_files:
  - apps/frontend/src/lib/backgrounds.test.ts
  - apps/frontend/src/tabs/SettingsTab.test.tsx
data_flow: greenfield
last_synced: 2026-10-02
status: complete
phase: all
mdd_version: 11
tags: [settings, background, video, look-and-feel, legibility]
path: UI/Settings/Background
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Legibility, by choice: the default (no scrim) puts the dark theme's dim text at 2.63:1 over the brightest pixel of the loop (main text 4.23); light-theme accent/danger reach 4.10/4.37 over the darkest. The bright and dim forests and the particles keep a scrim and pass."
  - "Size: the app now carries 19 MB of background video (was 4 MB): every background ships in the installers."
security_read_sites: []
sister_projects: []
---

# 165 — Background Choice

## Jan (2026-10-02)

- "Once more like now, but the video a little blurred. I think we simply put all versions
  into Settings. The user should decide what they like best."

## The backgrounds

| Choice (EN / DE) | Video | Scrim | Panel blur |
|---|---|---|---|
| **Forest / Wald** (default, new) | 1080p, `gblur` 2.5, 3.4 MB | none | none |
| Forest, sharp / Wald, scharf | 1080p unchanged, 7.5 MB | none | none |
| Forest, bright and calm / Wald, hell und ruhig | 720p tone-mapped, 3.5 MB | 0.25/0.2 | 10/14 px |
| Forest, dim and soft / Wald, gedämpft und weich | 720p `gblur` 3, 1.3 MB | 0.5/0.45 | 10/14 px |
| Particles / Partikel | the original, 4.0 MB | 0.5/0.45 | 10/14 px |

- **The new default's blur** was chosen from three frames compared at 1:1: sharp, 1.5 and
  2.5. Jan asked for "a little blurred"; 2.5 calms the leaves while the forest still
  reads.

## How

- **`lib/backgrounds.ts`** lists them: label, video, poster.
- **`LookProvider`:**
  - remembers the choice (`look.background`);
  - sets `data-background` on `<html>`.
- **`look.css`:**
  - one scrim formula, `rgb(var(--scrim-rgb) / var(--scrim-top))`, and
    `--panel-blur`/`--header-blur`, all zero for the default;
  - each other background sets its own in a `:root[data-background=…]` block;
  - the scrim's colour follows the theme (dark or light).
- **`BackgroundVideo`** plays the chosen file (`key` on `src`, so the element reloads).
- **The default keeps the old file names.** The download site's updater copies exactly
  `particles-loop.mp4` and `particles-poster.jpg`, so the site shows the default.
- **Settings › Appearance:** "Background", five radios, EN/DE.

## Verified (2026-10-02)

- **In the UI, each of the five:**
  - plays its own file (1920 px for both 1080p forests, 1280 px for the others);
  - shows its scrim (0, 0, 0.25, 0.5, 0.5);
  - shows its blur (none, none, 10 px, 10 px, 10 px).
- **Tests** (1209 frontend, TypeScript clean):
  - every listed file is shipped, and nothing unused;
  - the default keeps the site's file names;
  - choosing a background switches `data-background`, the video's `src`, and is stored.
- **Contrast of the default,** measured by the script (now set to it): see known issues.
  The script exits 1 by design until the default changes.
