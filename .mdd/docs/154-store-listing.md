---
id: 154-store-listing
title: Store Listing — What the Microsoft Store Page Says, the Privacy Policy and the Certification Notes
edition: DinoTraining
depends_on: [133-download-site]
relates: [155-store-submission, 151-msix-package]
source_files:
  - packaging/store/README.md
  - packaging/store/listing-en.md
  - packaging/store/listing-de.md
  - website/privacy.html
  - website/index.html
  - website/site.js
  - website/site.css
routes: []
models: []
test_files: []
data_flow: greenfield
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [microsoft-store, listing, privacy-policy, website, i18n]
path: Installer/Windows/MSIX/Listing
initiative: dinotraining
wave: dinotraining-wave-15-10
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 154 — Store Listing

## Purpose

- **Everything Partner Center asks for, as files in the repo,** so Jan copies rather than
  writes, and each release can carry them.

## The listing (`packaging/store/`)

- **`listing-en.md`, `listing-de.md`:** product name, short description, description,
  features, search terms, system requirements, links.
  - **The first lines name the first start's download** (Python and PyTorch from GitHub,
    PyPI and pytorch.org, about 1–6 GB; the Visual C++ runtime from Microsoft if needed),
    as policy 10.2.4 asks for code loaded after install.
  - **Only what the app does:** formats as the code has them (imports COCO, YOLO, Pascal
    VOC, OpenLABEL; exports COCO and the app's own format), heads as the registry has them
    (classification, detection, segmentation, depth).
- **`README.md`:** category (Developer tools), properties, the IARC answers, pricing,
  licence (MIT), the screenshot list (four views, 1366×768 or larger, EN and DE) and the
  notes for certification (how a tester gets past the first start).

## The privacy policy (`website/privacy.html`)

- **Served by doc 133's site** at `https://dino.w3rth.de/privacy.html` (the updater copies
  every `website/*.html`), English and German (`#de`) on one page.
- **Says:** no account, telemetry, analytics or advertising; what is downloaded from where;
  what goes only where the user sends it (their cloud storage, MLflow, "Report an issue",
  which sends nothing itself); what uninstalling removes; contact through GitHub issues.
- **The download page** links to it, and its open-source fact now says the pictures stay
  on the computer "or in cloud storage you connect yourself" (Wave 15.9), with "No
  telemetry".

## Not in this doc

- **Screenshots:** taken from the installed MSIX on Windows once doc 152 has measured it.
  The list is in the README.
- **Entering it in Partner Center:** doc 155's checklist, Jan's step.
