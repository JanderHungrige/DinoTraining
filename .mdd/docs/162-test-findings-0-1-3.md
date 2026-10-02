---
id: 162-test-findings-0-1-3
title: Findings From Jan's 0.1.3 Test — German Left After Switching, the Studio's Stale Dataset List, Where a Download Lives
edition: DinoTraining
depends_on: [111-language-switch, 138-example-dataset, 136-dataset-import]
relates: [59-reveal-dataset-folder, 104-annotation-targets]
source_files:
  - apps/frontend/src/hooks/useAnnotationTargetList.ts
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/components/DatasetWhere.tsx
  - apps/frontend/src/components/DatasetImport.tsx
  - apps/frontend/src/components/ImageSourceField.tsx
  - apps/frontend/src/i18n/en/datasets.ts
  - apps/frontend/src/i18n/de/datasets.ts
  - apps/frontend/src/i18n/en/studio2.ts
  - apps/frontend/src/i18n/de/studio2.ts
routes: []
models: []
test_files:
  - apps/frontend/src/hooks/useAnnotationTargetList.test.tsx
  - apps/frontend/src/components/SessionSetup.test.tsx
  - apps/frontend/src/components/DatasetWhere.test.tsx
  - apps/frontend/src/components/ImageSourceField.test.tsx
data_flow: reads-existing
last_synced: 2026-10-02
status: complete
phase: all
mdd_version: 11
tags: [bugfix, i18n, annotation-studio, datasets, example-dataset, ux]
path: Fixes/0.1.3
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 162 — Findings From Jan's 0.1.3 Test

Jan (2026-10-02): "Everything worked in general." Three findings.

## 1. German text left after switching to English

- **Cause:**
  - The Studio stays mounted once opened (App's `studioVisited`).
  - Its "What should this dataset train?" choices come from the backend, written in the
    request's language, and were read only once.
  - Switched to English, they stayed German.
- **Measured live:**
  - every tab and sub-tab walked in English (11 pages) for German lines;
  - only the Studio had them.
- **Fix:**
  - `useAnnotationTargetList` reads again when the language changes;
  - so does `SessionSetup` (datasets, heads, general detectors).
  - Afterwards the Studio went from 26 German lines to 0, and the walk is clean.
- **No hard-coded German anywhere:** every German string is in `i18n/de/`.

## 2. The downloaded example missing from the Studio

- **Cause:** the same. `SessionSetup` read the dataset list once, when the Studio was first
  opened. A dataset downloaded or imported later in Models & Datasets was not offered until
  something made it read again (creating a dataset did).
- **Fix:** the setup reads its lists each time the Studio is shown (`active`).
- **Test:** Jan's sequence. It fails without the fix.

## 3. Where is the downloaded dataset?

- **The import result** (folder, example download, cloud link alike) now says:
  - **where its pictures are**, from the backend's dataset-folder answer (doc 59), with
    "Show in Explorer";
  - **how to open it:** Annotation Studio → "A dataset you already have" → its name. No
    folder to pick.
- **The Studio's folder option** says the same when datasets exist: imported or downloaded
  already? Choose "A dataset you already have".

## Tests

- Frontend 1201, TypeScript clean.
- New:
  - the language switch re-reads the targets;
  - the hidden-Studio import sequence;
  - `DatasetWhere` in English and German;
  - the folder hint, shown and not shown.
