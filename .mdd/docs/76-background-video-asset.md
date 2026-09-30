---
id: 76-background-video-asset
title: Background Video Asset — Mirror-Stitched Particle Loop
edition: DinoTraining
depends_on: []
relates: [54-distribution-licensing, 77-app-background-layer]
source_files:
  - scripts/build_background_video.py
  - apps/frontend/public/background/particles-loop.mp4
  - apps/frontend/public/background/particles-poster.jpg
  - apps/frontend/public/background/PROVENANCE.md
  - apps/frontend/public/THIRD_PARTY_ASSETS.md
routes: []
models: []
test_files:
  - backend/tests/test_background_video_script.py
data_flow: greenfield
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [look-and-feel, video, loop, licensing, assets, pyav]
path: App Shell/Look & Feel
initiative: dinotraining
wave: dinotraining-wave-10
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Mirroring reverses the particles' drift at the halfway point (29 s). It is seamless, but an attentive eye sees the direction change once a minute. That is inherent to mirror-stitching, which was the request; a crossfade loop would avoid it at the cost of a ghosting overlap." 
security_read_sites: []
sister_projects: []
---

# 76 — Background Video Asset

## Purpose

Requested: *"download the Pixabay video 'octagon abstract lights particle' and mirror-stitch it
so it loops seamlessly, then use it as the application's background."*

A clip that plays forwards and then backwards has no seam, because its last frame leads back
into its first. This doc produces that file, small enough to ship in the installer, with
its provenance and licence recorded.

## Source

| | |
|---|---|
| Page | https://pixabay.com/videos/octagon-abstract-lights-particle-5192/ (by *tommyvideo*, 2016) |
| File | `https://cdn.pixabay.com/video/2016/09/13/5192-183786490_large.mp4` |
| As downloaded | 13,351,552 bytes, sha256 `233e123d…de73349`, 1920×1080, 29.97 fps, 870 frames, 29.03 s |
| Licence | Pixabay Content License: free for use in an app, attribution not required. The file must not be redistributed *on its own*, and bundling it inside the app is use, not standalone redistribution. |
| Downloaded | 2026-09-29, with Jan's explicit go-ahead (file, source and size stated). |

**The 13 MB source is not committed**, only the derived loop is. The script re-downloads by
URL and checks the sha256, so the asset is reproducible and the provenance is verifiable.

## Business Rules

1. **Mirror, not crossfade.** Frames 0…N−1, then N−2…1. The two turn-around frames are not
   repeated: a frame shown twice in a row is a visible stall at 30 fps.
2. **Downscale before holding anything.** Frames are scaled to 1280×720 and spooled to disk
   as they decode. `ffmpeg -vf reverse` would hold all 870 1080p frames in memory, which
   is several gigabytes.
3. **H.264 Main, yuv420p, `+faststart`, no audio.** WKWebView plays it natively, and
   faststart lets playback begin before the file has loaded.
4. **A size budget of ≤ 8 MB.** The installer is 181–377 MB (doc 58), and a background
   should cost single-digit MB. The script fails loudly if the output is over budget.
   The motion is soft bokeh, so a high CRF costs almost nothing visible.
5. **A poster frame** (JPEG, the loop's first frame) for reduced motion and for the first
   paint.
6. **Provenance travels with the asset.** `PROVENANCE.md` sits beside it. Doc 54's
   `THIRD_PARTY_LICENCES` generation gains the entry.

## Built and measured (2026-09-29)

- **Output:** `particles-loop.mp4` has 1,738 frames (870 forwards, 868 back), 1280×720,
  H.264 Main, yuv420p, 30 fps, 58.0 s, **4.04 MB** (budget 8). It took 40 s on this Mac. The
  "large" rendition turned out to be the full 1920×1080, so there was headroom to downscale.
- **The seam, measured** on 160×90 greys:
  - last → first frame: mean |Δ| **2.40**;
  - ordinary frame steps: median 1.81, p95 2.37, max 3.01.

  The loop point is inside the normal range of motion, and **no frame repeats** (zero steps
  of 0).
- **The poster is bright and warm.** Orange and pink bokeh on dark red makes a strong scrim
  a requirement for doc 77, not an option.

## Known Issues

## Bugs

(none yet — populated by /mdd bug when issues are reported)
