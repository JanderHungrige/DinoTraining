---
id: 168-store-link
title: Store Link — The Download Site and the README Point to V-Rex in the Microsoft Store
edition: DinoTraining
depends_on: [133-download-site, 155-store-submission]
relates: [156-store-aware-app]
source_files:
  - website/index.html
  - website/site.js
  - website/site.css
  - README.md
routes: []
models: []
test_files: []
data_flow: greenfield
last_synced: 2026-10-04
status: complete
phase: all
mdd_version: 11
tags: [website, microsoft-store, download]
path: Website/StoreLink
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 168 — Store Link

## Jan (2026-10-04)

- "Can you put the Microsoft link on the website?" The link:
  https://apps.microsoft.com/detail/9pkppdw39fcz?hl=en-US&gl=DE

## What changed

- **The Windows card leads with the Store:**
  - "Get it from the Microsoft Store" / "Im Microsoft Store holen" (the primary button);
  - "Signed by Microsoft, no warning, and it updates itself.";
  - then "Or the installer directly:" and the EXE button with its SmartScreen note, as
    before.
- **The link has no `hl`/`gl` parameters,** so the Store shows each visitor their own
  language and market.
- **A text button, not Microsoft's badge image:** the badge would load from Microsoft's
  servers on every visit, and the site contacts no one but GitHub for its release data.
- **The README** offers the Store first for Windows.
- **Corrected on the way:** "The installers are small (about 20 MB)". Since doc 165's
  backgrounds they are about 35–45 MB (EN/DE).

## Verified (2026-10-04)

- **A local copy of the site with the live `latest.json`:**
  - the Store button opens `https://apps.microsoft.com/detail/9pkppdw39fcz`;
  - the EXE button reads "Download for Windows (34 MB)" and links
    `V-Rex_1.0.0_x64-setup.exe`;
  - screenshot of the card checked.
