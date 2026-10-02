---
id: 160-v-rex-logo
title: V-Rex Logo — Jan's T-Rex With Sunglasses Replaces the Drawn Emblem
edition: DinoTraining
depends_on: [134-app-emblem, 159-rename-v-rex]
relates: [133-download-site, 151-msix-package, 154-store-listing]
source_files:
  - branding/v-rex-logo.png
  - branding/v-rex-logo-1024.png
  - apps/desktop/src-tauri/icons/
  - apps/frontend/public/emblem.png
  - apps/frontend/index.html
  - apps/frontend/src/App.tsx
  - website/emblem.svg
  - website/deploy/update-site.sh
  - README.md
routes: []
models: []
test_files:
  - apps/frontend/src/App.emblem.test.tsx
data_flow: greenfield
last_synced: 2026-10-02
status: complete
phase: all
mdd_version: 11
tags: [branding, logo, icons, v-rex, website, msix]
path: UI/Look/Logo
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Trademark: the logo follows the Jurassic Park logo (T-Rex skeleton on a yellow disc, jungle silhouette), with sunglasses as the twist. Doc 134 had avoided that look for this reason. Jan chose it knowingly (2026-10-02). Store certification or a rights holder may object; the fallback is doc 134's own drawn emblem, in git history (branding/emblem.svg)."
security_read_sites: []
sister_projects: []
---

# 160 — V-Rex Logo

## Jan (2026-10-02)

- "Please use that as the new logo": a T-Rex skeleton with sunglasses on a yellow disc in a
  black ring, a jungle silhouette below. A 500 px PNG with transparency.
- **Asked about the trademark question** (doc 134 had stayed away from the Jurassic Park
  look). Offered:
  - doc 134's own emblem with sunglasses;
  - the image redrawn as SVG.
- **Chose: the image as it is.**

## Where it went

- **The source:** `branding/v-rex-logo.png`, exactly as given.
- **The app icons:** `branding/v-rex-logo-1024.png`, a Lanczos upscale (Tauri asks for
  1024 px), run through `npx tauri icon`. That regenerates every icon in
  `apps/desktop/src-tauri/icons/`:
  - `.icns` and `.ico`;
  - the PNG sizes;
  - the Square*/StoreLogo tiles the MSIX takes (doc 151).
  - The Android/iOS folders it also writes were removed; there is no mobile build.
- **The UI:** `apps/frontend/public/emblem.png`, 320 px, quantized to 48 colours. It is
  12 KB instead of 105 KB, with a mean difference of 1/255. It is the header's logo and
  the favicon.
- **The website:**
  - `website/emblem.svg` stays the file name, now a wrapper with the same PNG embedded
    (33 KB);
  - **why:** the server's `update-site.sh` updates itself from the repo but copies only
    `*.svg`. A new `emblem.png` would be missing from the first deploy, and possibly
    longer;
  - the site's references are unchanged.
- **The README:** shows `branding/v-rex-logo.png`.
- **Removed:** doc 134's `branding/emblem.svg` and `apps/frontend/public/emblem.svg` (kept
  in git history as the fallback).

## Verified (2026-10-02)

- **The UI** loads `/emblem.png` (320 px) as the header logo and as the favicon.
- **The icons** were checked on a contact sheet at their real sizes (32, 44, 50, 64, 128,
  150 and 256 px):
  - from 64 px the sunglasses read;
  - at 32 px a yellow coin with a dark dino remains.
- **Tests:** `App.emblem.test.tsx` (the logo before the name, the favicon, the PNG ships);
  frontend 1195; Rust 56 (the icons compile into the shell).

## Found on the way: a test that needed a live backend

- **`HeadTrainerTab.recipe.test.tsx` failed** once the forgotten dev backend on :8756 was
  stopped.
  - The run's settings come from `getParameters`, which the test did not mock.
  - It had been passing only because that backend answered.
  - **Fixed:** the test mocks the parameter catalogue.
- **Guard:**
  - Measured first: 142 real requests leaked out of the suite, all incidental (the
    backend badge, lists).
  - `test-setup.ts` now makes every real `fetch` reject at once, as an unreachable
    backend does. No test's outcome depends on whether a server happens to run.
  - **Proven:** with a backend running, the unmocked test now fails; mocked, it passes.
