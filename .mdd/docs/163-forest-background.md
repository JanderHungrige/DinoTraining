---
id: 163-forest-background
title: Forest Background — Jan's Pexels Boomerang Loop, Softly Blurred, Replaces the Particles
edition: DinoTraining
depends_on: [77-app-background-layer, 80-legibility-and-motion-pass]
relates: [133-download-site, 157-sketch-everywhere]
source_files:
  - apps/frontend/public/background/particles-loop.mp4
  - apps/frontend/public/background/particles-poster.jpg
  - apps/frontend/public/background/PROVENANCE.md
  - website/index.html
  - website/site.js
  - scripts/build_background_video.py
routes: []
models: []
test_files:
  - apps/frontend/src/components/BackgroundVideo.test.tsx
data_flow: greenfield
last_synced: 2026-10-02
status: in_progress
phase: all
mdd_version: 11
tags: [look-and-feel, background, video, website, licence]
path: UI/Look/Background
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The Pexels page of the original clip is not recorded yet (PROVENANCE.md: to be added by Jan)."
security_read_sites: []
sister_projects: []
---

# 163 — Forest Background

## Jan (2026-10-02)

- First asked for an icegif.com forest GIF. Its licence says "Free for Personal & Social
  Use", too narrow for an app in the Store and on GitHub, and its origin is unknown. So it
  was not used.
- Then: "I found one on Pexels, made it a boomerang for an endless loop. Try it. Feel free
  to compress it again. Test whether a little blur does it good in the background."

## What was done

- **Compressed:**
  - 1920×1080, 34 MB with sound → 1280×720, H.264 Main, CRF 30, no sound;
  - the last frame dropped (it nearly repeats the first: a stall at the seam);
  - the exact commands are in `PROVENANCE.md`.
- **Blur, compared:**
  - three versions under the app's scrim: sharp (5.7 MB), sigma 3 (1.3 MB), sigma 6
    (0.8 MB);
  - **sigma 3 chosen:** the forest still reads as a forest, the detail no longer competes
    with the panels, and the panels blur it once more (10 px).
- **The same file names** (`particles-loop.mp4`, `particles-poster.jpg`): the site's
  updater copies exactly these, and a new name would stop its first deploy.
- **The website's credit** names Pexels (EN/DE). The old Pixabay script is marked as the
  former loop's.

## Verified (2026-10-02)

- **Contrast** (`check_background_contrast.py` over every 10th frame): every text colour
  at least 5.12:1 on the panel over the brightest frame. Over the darkest it is at least
  8.83:1.
- **In the UI:** the loop loads at 1280 px behind the header and panels. The browser pane
  does not autoplay, so motion was not seen there.
- `BackgroundVideo.test.tsx` passes.

## Open

- **Jan:** check it in the running app, in motion. Then: the link to the Pexels page for
  `PROVENANCE.md`.
