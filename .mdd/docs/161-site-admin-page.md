---
id: 161-site-admin-page
title: Site Admin Page — The MSIX Test Build and Its Checklist on dino.w3rth.de, Easy to Remove
edition: DinoTraining
depends_on: [133-download-site, 153-msix-smoke-ci]
relates: [152-msix-runtime, 155-store-submission]
source_files:
  - website/admin.html
  - website/index.html
  - website/privacy.html
  - website/site.css
routes: []
models: []
test_files: []
data_flow: greenfield
last_synced: 2026-10-02
status: deprecated
phase: all
mdd_version: 11
tags: [website, msix, testing, admin]
path: Website/Admin
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 161 — Site Admin Page

## Jan (2026-10-02)

- "Put the files I need to download and test on dino.w3rth.de. Maybe have an 'admin' tab in
  the top line. There have the files for download and tell me again what to test. Make it
  easy to delete again."

## What it is

- **`website/admin.html`:**
  - the two downloads;
  - the steps: trust the certificate, install, the checklist with "OK?" boxes,
    uninstall, troubleshooting;
  - `noindex, nofollow`;
  - an "Admin" link in the top bar of `index.html` and `privacy.html`.
- **The files** are a GitHub pre-release, **`msix-test-0.1.3`**:
  - `V-Rex_0.1.3_x64_test.msix` and `V-Rex_test.cer` from the 0.1.3 release run
    (36989282042), with their SHA-256;
  - **a pre-release on purpose:** GitHub's "latest" (and so `latest.json` and the site's
    download buttons) stays v0.1.3, and no binary goes into git.
- **The certificate's private key** existed only on the CI runner, so trusting the
  certificate lets through nothing but this package.

## To remove it

1. Delete `website/admin.html`.
2. Delete the two `<a href="admin.html">Admin</a>` lines (marked "Doc 161").
3. Delete the `.admin` block at the end of `website/site.css`.
4. `gh release delete msix-test-0.1.3 --cleanup-tag -R JanderHungrige/DinoTraining`.
5. Merge into `main`; the site updates within 10 minutes.

## Verified (2026-10-02)

- **Both download links** answer 200 with the right sizes (832 B, 26 224 220 B).
- **The pages, locally:**
  - the Admin link opens the page;
  - the downloads and the steps read as intended;
  - no sideways scrolling at 456 px.
- **GitHub's latest release** is still v0.1.3.

## Removed (2026-10-03)

- Jan's MSIX testing was done and 1.0.0 is released: the page, its links, its styles
  and the pre-release `msix-test-0.1.3` were removed, as "To remove it" describes.
