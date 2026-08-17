---
id: 06-annotation-workflow
title: Annotation Workflow — Folder, Prompt, Review, Save
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-1
wave_status: complete
depends_on: [01-app-shell, 03-dataset-store, 04-grounding-dino-annotator, 05-annotation-canvas]
relates: [02-model-manager]
source_files:
  - apps/frontend/src/api/datasets.ts
  - apps/frontend/src/api/annotate.ts
  - apps/frontend/src/hooks/useAnnotationSession.ts
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/components/CounterBar.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/hooks/useAnnotationSession.test.ts
  - apps/frontend/src/hooks/useAnnotationSession.save.test.ts
  - apps/frontend/src/hooks/session.testkit.ts
  - apps/frontend/src/components/CounterBar.test.tsx
data_flow: greenfield
last_synced: 2026-08-17
status: complete
phase: all
mdd_version: 11
tags: [annotation, workflow, counters, folder-picker, studio, wave-1-demo]
path: Studio/Annotation
integration_contracts: []
satisfies_contracts:
  - from: 01-app-shell
    function: apiFetch<T>(path, narrow, init)
    when: any frontend call to a /api/v1/* endpoint
    status: done
    verified_at: "apps/frontend/src/api/datasets.ts and api/annotate.ts — no direct fetch() outside client.ts"
  - from: 03-dataset-store
    function: PUT /datasets/{id}/images
    when: saving annotations for one image — the only sanctioned write path
    status: done
    verified_at: "apps/frontend/src/api/datasets.ts saveImageBoxes(); no other write path exists"
  - from: 05-annotation-canvas
    function: toNatural / toDisplay
    when: converting between displayed and image-natural pixels
    status: done
    verified_at: "apps/frontend/src/components/AnnotationCanvas.tsx — the workflow never converts itself"
security_read_sites: []
known_issues:
  - "No keyboard shortcut for next/previous image; navigation is buttons only. The per-image loop is the hot path and should get n/p or arrow keys once real usage shows the rhythm."
  - "Re-visiting an already-annotated image starts empty rather than loading its stored boxes — there is no GET for one image's annotations yet. Saving again overwrites correctly, but the user cannot review past work in place."
  - "The folder text field accepts any path; there is no validation until the backend answers. Under Tauri the native picker avoids this, but the web dev mode shows the error only after Start."
  - "SessionSetup has no test of its own; it is covered indirectly through the live verification. Add one when the dataset generator (Wave 4) reuses it."
sister_projects: []
---

# 06 — Annotation Workflow — Folder, Prompt, Review, Save

## Purpose

The wave's demo-state, assembled: point at a folder, type a prompt, see Grounding DINO
boxes, mark them, save, watch the counter climb. Everything under it already exists —
this feature is the sequencing and the state machine, not new capability.

## Architecture

```
AnnotationStudioTab
  ├─ SessionSetup      folder + dataset + prompt + thresholds → starts a session
  ├─ AnnotationCanvas  (feature 05) review and relabel
  ├─ CounterBar        live counts from the save response
  └─ useAnnotationSession
        GET  /annotate/folder      → the image list
        POST /annotate             → proposals for the current image
        PUT  /datasets/{id}/images → save, returns fresh counts
```

`useAnnotationSession` owns the whole session: image list, index, per-image boxes,
dirty state, counters. The tab is presentational. That split is what makes the
sequencing testable without a browser.

## Business Rules

- **Saving is explicit, and moving on saves first.** Next/Previous save the current
  image if it has unsaved changes. Losing ten minutes of labelling to a misclick is
  the worst outcome this screen can produce.
- **A reviewed image with no boxes is still saved.** "I looked and there is nothing
  here" is a real negative example, and skipping it would silently drop it from the
  dataset.
- **Counts come from the save response**, never incremented locally. The backend's
  aggregate is the number; a local tally would drift the moment a save failed.
- **Re-running the prompt replaces the proposals for the current image** but keeps
  hand-drawn boxes, which represent work the model cannot reproduce.
- **The image list is fetched once per folder.** Re-listing on every navigation would
  make the arrow keys hit the disk.
- **Navigation is bounded** — Previous at the first image and Next at the last are
  disabled rather than wrapping, so the user can tell when they are done.

## Data Flow

`counts` — aggregated by `store.counts()` in the backend → returned by
`PUT /datasets/{id}/images` → held in `useAnnotationSession` → rendered by
`CounterBar`. The counter therefore shows what is actually persisted, not what the UI
believes it sent.

`boxes` — proposed by `POST /annotate` (feature 04, already in store convention) →
edited in `AnnotationCanvas` (feature 05) → sent verbatim to the store (feature 03).
No shape conversion anywhere on that path.

## Dependencies

- `01-app-shell` — `apiFetch`, the Studio tab slot.
- `03-dataset-store` — dataset creation, the save endpoint, counters.
- `04-grounding-dino-annotator` — proposals, folder listing, image streaming.
- `05-annotation-canvas` — the review surface.

## Security

No new input surface: every path the user supplies goes to the feature-04 endpoints,
which own the validation. The folder path is typed by the user (or chosen through the
Tauri dialog) and is never interpolated into markup — React renders it as a text node.

Images are loaded through `GET /api/v1/annotate/image?path=...` rather than `file://`,
because the webview cannot read local files directly. That keeps the image-format
allowlist in front of every byte the UI renders.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
