---
id: 167-store-images
title: Store Images — Poster, Box Art and App Tile Icons From the Logo, Upscaled Crisp
edition: DinoTraining
depends_on: [160-v-rex-logo, 154-store-listing]
relates: [155-store-submission]
source_files:
  - scripts/build_store_images.py
  - packaging/store/images/
routes: []
models: []
test_files: []
data_flow: greenfield
last_synced: 2026-10-02
status: complete
phase: all
mdd_version: 11
tags: [microsoft-store, branding, logo, images]
path: Installer/Windows/MSIX/Listing/Images
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 167 — Store Images

## Jan (2026-10-02)

- He needs, for the Store listing, from the logo:
  - 9:16 poster art 1440×2160;
  - 1:1 box art 2160×2160;
  - 1:1 app tile icons 300, 150 and 71 px.
- "Can you upscale it?"

## How (`scripts/build_store_images.py`)

- **The logo is two colours on transparency:** yellow `#FADC02` and black, measured; only
  2.7 % of its pixels are edges.
- **Upscaled once to 2160 px,** then every pixel is put back between black and yellow. The
  same goes for its alpha, with a narrow smoothing band (`EDGE`). The edges stay crisp,
  where a plain Lanczos upscale of the 500 px source is visibly soft.
- **The smaller sizes** are scaled down from that master.
- **Poster art:**
  - the logo on the app's dark ground (`#14161a`);
  - "V-Rex" in the logo's yellow (Futura Condensed ExtraBold);
  - "Vision Representation & Experimentation" in the app's dim text colour (Futura
    Medium).
- **Box art:** the logo on the dark ground. Poster and box art have no transparency.
- **Tile icons:** the logo on transparency.

## Verified (2026-10-02)

- All five files have the requested size.
- A crop of the box art against a plain upscale: the crisp one has clean edges.
- The tile icons were checked on dark and light ground at 300, 150 and 71 px.
