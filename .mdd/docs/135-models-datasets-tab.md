---
id: 135-models-datasets-tab
title: Models & Datasets — the Entry Point after Start here, with Official Models, Datasets and My Models
edition: DinoTraining
depends_on: [51-library-tab, 38-intro-tab]
relates: [136-dataset-import, 137-dataset-guide, 138-osdar23-example]
source_files:
  - apps/frontend/src/tabs/tabs.ts
  - apps/frontend/src/tabs/ModelsTab.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
  - apps/frontend/src/tabs/LibraryTab.tsx (gains `kinds` and `headed`)
  - apps/frontend/src/styles.css
  - apps/frontend/src/i18n/GLOSSARY.md
  - backend/app/i18n/de_requirements.py
  - apps/frontend/src/components/SubTabBar.tsx
  - apps/frontend/src/App.tsx
  - apps/frontend/src/tabs/introContent.ts
  - apps/frontend/src/i18n/en/*.ts
  - apps/frontend/src/i18n/de/*.ts
  - backend/app/api/v1/*.py (error texts naming the tab)
  - backend/app/i18n/de_errors.py
  - README.md
routes: []
models: []
test_files:
  - apps/frontend/src/tabs/ModelsTab.test.tsx
  - apps/frontend/src/components/SubTabBar.test.tsx
  - apps/frontend/src/tabs/IntroTab.test.tsx
data_flow: reads-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [ui, tabs, navigation, models, datasets, library, i18n]
path: UI/ModelsDatasets
initiative: dinotraining
wave: dinotraining-wave-15-8
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 135 — Models & Datasets

## Purpose

- **Jan (2026-10-01):** "Rename the Admin/Models to Models/Datasets and shift it after
  Start here, as this is the actual entry point."
- Three sub-tabs, **Official Models**, **Datasets** and **My Models**: "Official and My
  models is clear. Just shift the existing things in there."
- **Decided:**
  - the Library tab goes, its datasets into *Datasets*, its heads and fine-tuned models
    into *My Models*;
  - *Official Models* is today's Admin page, appearance included.

## The tab

- **Name:** "Models & Datasets" / "Modelle & Datensätze".
- **Tab order:** Start here, **Models & Datasets**, Inspect, Studio, Prepare, Training,
  Inference, Generator, Connection. The Library and Admin tabs are gone.
- **Sub-tabs:** the same keyboard pattern as the main tabs (arrow keys, Home/End, roving
  tabindex). The chosen sub-tab is remembered, so leaving and returning lands where
  you were.
  - **Official Models:** the Admin page unchanged: downloads, system, GPU, token, head
    catalogue, starter set, appearance.
  - **Datasets:** the Library's datasets (list, select, delete). Docs 136–138 add the
    import, the guide and OSDaR23 here.
  - **My Models:** the Library's trained heads and fine-tuned models (export, delete).
- **Bulk selection** stays per sub-tab: a selection on Datasets never deletes a head.

## Everywhere it was named

- **Start here:**
  - the stages begin with "Get models and data" (this tab), then "Look at your data
    first" (Inspect);
  - the Library and Admin stages fold into the first.
- **Texts that said "Admin / Models", "the Admin tab" or "the Library":**
  - Studio, Training, the Inference empty state, the setup tips;
  - the backend's "not installed" errors and their German map;
  - all now say "Models & Datasets" ("Modelle & Datensätze").
- **README:** the features section and its contents follow the new order; the
  "Library" and "Admin / Models" sections merge into "Models & Datasets".

## Verified (2026-10-01)

- **Frontend (1136 tests):**
  - the new `ModelsTab` (4): opens on Official Models (the former Admin page); Datasets
    shows only datasets and My Models only heads and fine-tunes, without the Library's
    own heading; the sub-tab survives leaving and returning; German;
  - `SubTabBar` (2): one selected, focusable tab with its `aria-controls`; arrow keys
    wrap, Home and End;
  - the existing Library tests unchanged: it still renders everything when used whole.
  - Updated where they named the old tabs: the tab bar, the German shell, Start here
    (8 stages, not 9), the Studio's keep-alive test, and four "where to get a model"
    hints.
- **Backend (1895 tests):** every "not installed" error now says "Models & Datasets";
  the German maps follow (errors and fine-tune requirements); five tests updated.
- **In the running app (German):**
  - tabs Hier starten · Modelle & Datensätze · Datensätze ansehen · …;
  - sub-tabs Offizielle Modelle · Datensätze · Meine Modelle;
  - Datensätze lists the 18 datasets.
  - Found on the way: the active sub-tab's dark text had too little contrast on the light
    theme's dark green. It now uses the theme's background: 4.68:1 light, over 10:1
    dark.
- **README:** "Models & Datasets" right after Start here, absorbing Library and Admin;
  the contents, first steps and model-download mentions follow.
