---
id: 80-legibility-and-motion-pass
title: Legibility and Motion Pass — Measured Contrast over the Loop
edition: DinoTraining
depends_on: [77-app-background-layer, 79-draft-sketch-controls]
relates: [76-background-video-asset]
source_files:
  - scripts/check_background_contrast.py
  - apps/frontend/src/look.css
routes: []
models: []
test_files:
  - apps/frontend/src/components/BackgroundVideo.test.tsx
data_flow: greenfield
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [look-and-feel, accessibility, contrast, wcag, reduced-motion]
path: App Shell/Look & Feel
initiative: dinotraining
wave: dinotraining-wave-10
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Contrast is guaranteed on the translucent panel and header, which are the surfaces over the video. Text inside cards sits on solid --bg-raised and was never at risk. Text drawn *on images* (box labels) is on the image, not the loop, and is out of scope here."
  - "The worst case is a single saturated highlight (rgb 254,238,142). Measured at 10 px and at 20 px scale it is the same pixel, because the loop's highlights are large, so the blur buys nothing and the guarantee rests on the surfaces and tokens."
  - "The moving loop, reduced motion and the blur are still to be seen in WKWebView. Chromium screenshots do not capture a playing video, and this is the wave's packaged-app demo item."
security_read_sites: []
sister_projects: []
---

# 80 — Legibility and Motion Pass

## Purpose

Every screen must stay legible over the loop, and calm under reduced motion. That is
measured here, not judged by eye.

## Method

`scripts/check_background_contrast.py` finds the **brightest pixel anywhere in the loop**
(every 10th frame, at blur scale) and composites it exactly as the browser stacks the
layers: video → scrim → translucent surface. It then computes WCAG contrast for every text
colour, on the panel and on the header, in both colour schemes. It exits 1 below AA (4.5:1),
so it can be rerun whenever the loop, a surface or a token changes.

## Findings and fixes

| | before (doc 77 values) | after |
|---|---|---|
| dark `--text-dim` on panel | **2.97** | 5.08 (`#9aa2b1` → `#b3bac6`) |
| dark `--danger` on panel | **2.76** | 5.22 (`#f87171` → `#fca5a5`) |
| dark `--accent` on panel | **4.38** | 5.69 (surface change only) |
| dark header, dim / danger | **4.40 / 4.08** | 6.46 / 6.65 |
| light `--pending` on panel | **4.50** (4.4997) | 5.43 (`#a16207` → `#8f5708`) |

- **Surfaces:** panel 52 → **60 %**, header and tabs 70 → **78 %**, dark scrim bottom 0.38 →
  **0.45**.
- **Why not opacity alone:** that would have needed 72 % and a 0.5 scrim, at which point
  the video is barely visible. Lightening two dark-mode colours a shade does the rest, and
  they still read as the same colours on solid cards.
- **The colour fixes are scoped.** They sit under `not (prefers-color-scheme: light)`, and
  the light scheme was checked to keep its own values: `--text-dim #5c6470`, `--danger
  #b91c1c`.

## Motion

- **Reduced motion:** the video is replaced by the still poster (doc 77, followed live), and
  the buttons lose their turn, press and transition (doc 79). Both are pinned by tests.
- **Image surfaces stay opaque:** the annotation canvas stage (`#000`), the Inspect and
  viewer stages. No particles show through an image being annotated.

## Verified in the running app (2026-09-29)

- **Dark scheme, Inspect tab, screenshot:** the lead text computes `rgb(179,186,198)` on a
  0.6 panel and is clearly legible; the warm background is visible at the edges; the frame
  area is solid black.
- **Light scheme, Admin, screenshot:** pale peach background, cards legible. The dark-mode
  overrides do not leak into light.
- **The contrast script passes:** every colour ≥ 4.5 on both surfaces, in both schemes.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
