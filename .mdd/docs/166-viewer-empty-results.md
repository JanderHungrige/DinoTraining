---
id: 166-viewer-empty-results
title: Inference Viewer — Say Why a Result Is Empty, and Let the User Set the Detection Threshold
edition: DinoTraining
depends_on: [18-multi-head-compose, 21-same-task-head-compare]
relates: [20-inference-overlay-render, 62-tiled-inference]
source_files:
  - apps/frontend/src/lib/scoreFilter.ts
  - apps/frontend/src/components/ScoreThreshold.tsx
  - apps/frontend/src/components/SideBySideViewer.tsx
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
  - apps/frontend/src/hooks/useHeadRun.ts
  - apps/frontend/src/components/HeadRunPanel.tsx
  - apps/frontend/src/look.css
  - apps/frontend/src/components/SequencePanel.tsx
  - apps/frontend/src/i18n/en/run.ts
  - apps/frontend/src/i18n/de/run.ts
routes: []
models: []
test_files:
  - apps/frontend/src/lib/scoreFilter.test.ts
  - apps/frontend/src/components/ScoreThreshold.test.tsx
  - apps/frontend/src/hooks/useHeadRun.threshold.test.ts
  - apps/frontend/src/tabs/InferenceViewerTab.mode.test.tsx
data_flow: reads-existing
last_synced: 2026-10-02
status: complete
phase: all
mdd_version: 11
tags: [bugfix, inference-viewer, detection, threshold, ux]
path: Fixes/Viewer/EmptyResults
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 166 — Inference Viewer: Why a Result Is Empty

## Jan (2026-10-02)

- "A serious bug. The Inference Viewer shows nothing after a run. 0 backbone passes.
  DINOv2 says one backbone pass, but also nothing is shown."

## What was found (live, `dev`, the real backend and models)

- **The backend is fine.** `POST /inference/compose` answered 200 for every detection
  head. RF-DETR (nano) on an OSDaR23 picture: 4 boxes (train 0.89, train 0.41, two traffic
  lights), drawn correctly in the viewer.
- **The head that showed nothing** (`2221b5f5`, "Object detection: person +2 more",
  29.09.):
  - its test mAP is **0.007**: practically untrained, from the video-split experiments;
  - its best score on the picture was 0.21, and the viewer's fixed threshold is 0.30, so
    it returned `boxes: []`;
  - the viewer showed an empty picture without a word.
- **Other heads** of the same series found 2–7 boxes; the older person heads (mAP 0.5–0.58)
  up to 22.
- **"0 backbone passes"** is the cost line when only foundation models run (they make no
  backbone pass). It read as if nothing had run.

## Fix

- **The threshold belongs to the user:**
  - the viewer asks for every candidate (`score_threshold: 0`; the backend caps at 50 per
    head);
  - a slider "Show boxes from" (0.05–0.95, default 0.30, remembered) filters in the
    browser, so moving it needs no new run.
- **An empty detection pane says why:**
  - "No box at 0.30 or above. Best guess here: 0.21. Lower the threshold to see it.";
  - or "This model found nothing in this picture." (EN/DE).
- **The cost line** leaves out "backbone passes" when there were none: only the time.

## Verified (2026-10-02)

- **In the running app, with the weak head on the OSDaR23 picture:**
  - the note reads "No box at 0.30 or above. Best guess here: 0.21";
  - the slider at 0.15 draws 13 boxes, the note goes;
  - still one `compose` request in total.
- **Tests:** frontend 1215. New:
  - the filter keeps boxes, scores and classes in step;
  - the empty reasons;
  - other kinds untouched;
  - the note in EN/DE;
  - the run asks with `score_threshold: 0`.

## The actual cause (Jan: "not even the picture is shown")

- **Jan's viewer was in "A video or a folder" with a single picture as the path**
  (`~/Downloads/osdar23/…/000_….png`; the pane browser we share had it remembered).
- **In that mode:**
  - the viewer showed only "That path is not a sequence", and no picture;
  - "Run models" was still enabled and ran the picture for real (hence "1 backbone
    pass");
  - but results are drawn only in the single-image view, so nothing appeared.
- **Ruled out:** reading the picture from `~/Downloads` works (the backend's
  `read_image`, 0.29 s).
- **Fix:**
  - **"Run models" is disabled in the video mode**; the player analyses a sequence itself;
  - **a single picture there offers "Open it as a single image"** (EN/DE), which switches
    the mode and shows it.
- **Test:** `InferenceViewerTab.mode.test.tsx` replays Jan's state:
  - in the video mode with a single picture, Run is disabled;
  - "Open it as a single image" shows the picture and enables Run;
  - it fails without the fix.
- Frontend 1216 tests.
