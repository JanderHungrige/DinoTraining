---
id: 34-inference-picker-upfront
title: Inference Picker Upfront — Choose Heads Before There Is an Image
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-5
wave_status: complete
depends_on: [19-side-by-side-viewer, 32-shared-head-picker]
relates: [17-image-input-source, 18-multi-head-compose]
source_files:
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
  - apps/frontend/src/components/HeadRunPanel.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/tabs/InferenceViewerTab.test.tsx
data_flow: reads-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [inference-viewer, head-picker, ordering, react, accessibility]
path: Inference/Compare
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The hint (\"Pick an image or a folder above…\") is a `role=\"status\"` line rather than anything the panel itself knows. A panel that could describe its own blocked state would not need the caller to explain it, but that means teaching `HeadRunPanel` about images, which it deliberately knows nothing about."
sister_projects: []
---

# 34 — Inference Picker Upfront

## Purpose

Let the Inference Viewer's heads be chosen **before** an image or folder is loaded, so the
slowest decision in the tab — which of N heads to compare — no longer sits behind a folder
read.

## Architecture

Wave 5's plan asked for this in one line and told the planner to **scope it against what
already ships**, which turned out to be most of it. `HeadRunPanel` already selected heads
before running, filtered by task, derived the backbone from the selection and disabled
incompatible heads. `useHeadRun` already lived at tab level, so a selection already survived
image changes.

The only real gap was rendering: the panel sat inside `{current && …}`, so none of that was
reachable until an image existed. The fix is moving it out of the guard — not rebuilding a
working control.

```
before                              after
  ImageSourcePicker                   ImageSourcePicker
  {current && (                       HeadRunPanel        ← always rendered
     HeadRunPanel                     {!current && hint}
     path + SideBySideViewer          {current && (path + SideBySideViewer)}
  )}
```

## Business Rules

1. **"Nothing to run on" must not mean "you may not choose."** This is the whole feature,
   and it is also the bug the first attempt shipped: passing `disabled={!current}` made the
   *entire* panel inert, which reproduced the old behaviour with extra steps. `HeadRunPanel`
   therefore grew a second prop — `disabled` makes the panel inert (used while a folder is
   loading), `runDisabled` blocks only the Run button.
2. **The blocked state is explained, not merely enforced.** A disabled Run button with no
   reason is a dead end; a `role="status"` line names the missing thing.
3. **The selection survives the image arriving.** Already true — `useHeadRun` is tab-level —
   and now observable, which is what makes it worth stating.

## Data Flow

None new. `useHeadRun` owns the selection exactly as it did in Wave 3; this feature changes
only where its panel is rendered and which of its controls are disabled when.

## Dependencies

- **19-side-by-side-viewer** — the tab this reorders.
- **32-shared-head-picker** — sibling feature; `HeadRunPanel` stays the *comparison*
  control here and is deliberately not replaced by the single-select picker.

## Security

None.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
