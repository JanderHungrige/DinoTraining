---
id: 134-app-emblem
title: App Emblem — a Round Coin with a Mirrored T-Rex Skeleton, Yellow on Black, No Text
edition: DinoTraining
depends_on: []
relates: [133-download-site]
source_files:
  - branding/emblem.svg
  - apps/desktop/src-tauri/icons/
  - website/site.css
  - website/deploy/update-site.sh
  - apps/frontend/src/styles.css
  - apps/frontend/public/emblem.svg
  - apps/frontend/index.html
  - apps/frontend/src/App.tsx
  - website/index.html
  - website/emblem.svg
  - README.md
routes: []
models: []
test_files:
  - apps/frontend/src/App.emblem.test.tsx
data_flow: greenfield
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [branding, logo, emblem, icons, tauri, website]
path: Branding/Emblem
initiative: dinotraining
wave: dinotraining-wave-15-8
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 134 — App Emblem

## Purpose

- **Jan (2026-10-01):** "the round coin with the T-rex skeleton, but not red-black:
  yellow-black and mirrored". **Decided:** an own emblem, without text.
- **Why own:** the Jurassic Park logo is Universal's trademark, and the printables model
  is fan art of it. An app distributed publicly must not carry it.
- **So the style is borrowed, not the artwork:**
  - a coin with a ring;
  - a T-rex skeleton in profile, mouth open, facing **right** (the film's faces left);
  - drawn here as bones (round-capped strokes, joints, ribs). Nothing is traced.

## The emblem

- **`branding/emblem.svg`** is the single source:
  - viewBox 512, a black coin with a yellow ring, a yellow field (#F5C518), the
    skeleton in near-black (#141414);
  - the eye socket left open.
- **It must read at 16 px:**
  - the silhouette carries it: skull, neck curve, tail;
  - no detail it depends on is thinner than 1/32 of the coin.

## Where it goes

- **App icons:** `npx tauri icon branding/emblem.svg` writes every size (.icns, .ico,
  PNGs, Windows Store logos) into `apps/desktop/src-tauri/icons/`.
- **The app header:** the emblem before "DinoTraining", 28 px.
- **The web UI's favicon:** `apps/frontend/public/emblem.svg`.
- **The download site:** the header, the favicon, and a large emblem in the hero.
- **The README:** a centred emblem at the top.

## Verified (2026-10-01)

- **Three drafts, compared at 512, 128, 64, 32 and 16 px**, on dark and light:
  1. The first had a small, round head that read as a fish.
  2. The second has a larger, angular skull with the big window before the eye, a
     straighter tail and heavier legs, so it reads as a T-rex.
  3. The third moves the figure down and in by 5 %, because the snout touched the
     ring.
  At 16 px a yellow coin with a dark animal shape remains.
- **`npx tauri icon branding/emblem.svg`** rendered every desktop size; checked
  `icon.png` (512 px) by eye. It also wrote Android and iOS icons, which this app does
  not need, so they were removed.
- **The app header:** the emblem at 28 px before the name; the heading's accessible
  name stays "DinoTraining" (the image is decorative); the favicon is `/emblem.svg`.
  Two tests.
- **The download site:** the header (30 px), the hero (132 px) and the favicon; the
  updater now copies `*.svg`. It goes live with the next merge to main.
