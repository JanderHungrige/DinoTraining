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
known_issues: []
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

## Second version (2026-10-02): no blur, brighter

- **Jan:** "Keep that as a backup. But it seems much darker than the original. Leave out
  the blur too." The source is *Trees in the forest* on Pexels
  (https://www.pexels.com/video/trees-in-the-forest-5121476/).
- **Backup:** the git tag `background-forest-blur3` (the first version, 1.3 MB).
- **Why it was dark:** the app's scrim (0.5/0.45 black) and the 60 % panels.
- **Why the scrim could not just get thinner:** unblurred, the sky between the trees is
  near-white (247, 245, 243). Over it, text fell below AA already at a 0.35 scrim.
- **The fix:**
  - the video's highlights are tone-mapped (`curves`, white to 72 %), the midtones lifted;
  - then the scrim is 0.25/0.2;
  - compared on one frame against the original, the blurred version and a gentler curve
    (B, needing a 0.3 scrim): A is the brightest that passes.
- **Size:** 3.5 MB (CRF 32, sharp).
- **Contrast:** at least 4.64:1 over the brightest pixel; the script's constants follow
  the new scrim.

## Third version (2026-10-02): the plain video, an experiment in dev

- **Jan:** "Still very blurred and dark. No animation to be seen. Just put the video in as
  it is, without blur or anything."
- **What he saw:**
  - **The blur** came from the panels, not the video: `backdrop-filter: blur(10px)` on
    the page-wide panel, and 14 px on the header.
  - **720p** stretched over a large screen looks soft by itself.
  - Under blur and darkening, the camera's slow move through the forest did not read as
    motion.
- **Now:**
  - the video only re-encoded, at **1080p** (CRF 33, 7.5 MB);
  - **no scrim**, **no backdrop blur**;
  - the panels keep only their tint (60 %), so text has something under it.
  - Seen in the UI: the video plays (1920 px) and is sharp.
- **Legibility:** over the brightest frames the dim text falls below AA (doc 163's numbers:
  about 2.6:1 with no scrim). The contrast script now fails on purpose until Jan decides.
- **Backups:** the tags `background-forest-blur3` and `background-forest-curve-a`.
