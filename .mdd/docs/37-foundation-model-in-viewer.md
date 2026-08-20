---
id: 37-foundation-model-in-viewer
title: Foundation Model in the Viewer — Compared Against What You Trained
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-6
wave_status: in_progress
depends_on: [19-side-by-side-viewer, 34-inference-picker-upfront, 36-depth-foundation-model]
relates: [18-multi-head-compose, 20-inference-overlay-render]
source_files:
  - apps/frontend/src/api/foundation.ts
  - apps/frontend/src/api/inference.ts
  - apps/frontend/src/hooks/useHeadRun.ts
  - apps/frontend/src/components/HeadRunPanel.tsx
routes: []
models: []
test_files:
  - apps/frontend/src/hooks/useHeadRun.foundation.test.ts
data_flow: reads-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [inference-viewer, foundation-model, comparison, depth, react, render-hint]
path: Inference/Compare
integration_contracts: []
satisfies_contracts:
  - from: 36-depth-foundation-model
    function: "build_foundation(id)"
    when: "any code that maps a foundation id to an implementation"
    status: done
    verified_at: "the frontend never maps ids — it posts to /foundation/predict"
security_read_sites: []
known_issues:
  - "Foundation models are run one request per model. Heads share a backbone pass; these cannot share anything, so N selected models are N round trips. Fine at one; a catalogue of them would want a batch endpoint."
  - "`elapsed_ms` on a merged result is the **max** of the two, not the wall clock. They run concurrently, so a sum would overstate and either choice is a simplification — the number is a rough cost signal, not a benchmark."
  - "The task filter narrows heads only. A foundation model whose task the filter excludes still shows, because the filter reads `HeadTask` and foundation tasks are plain strings. Harmless with one depth model; wrong the moment there are several kinds."
sister_projects: []
---

# 37 — Foundation Model in the Viewer

## Purpose

Put a foundation model in the Inference Viewer beside the trained heads, so a user can
compare a foundation depth model against a head they trained themselves, on one image.

## Architecture

The two run through genuinely different backends — `POST /inference/compose` shares one
backbone forward across N heads, `POST /foundation/predict` runs a self-contained model —
and their results are **merged into one `ComposedResult`**.

Merging is the whole feature. The panes, the overlay registry and the compare layout all
work off `Prediction[]`; keeping two lists would mean teaching each of them that some
predictions come from somewhere else, for no gain, since a `Prediction` already carries
the `render_hint` that decides how it is drawn.

```
selected heads ──▶ /inference/compose ─┐
                                       ├─▶ one Prediction[] ─▶ panes, overlays
selected foundations ──▶ /foundation/predict (×N) ─┘
```

The two are started with `Promise.all` rather than in sequence: they share nothing, so
serialising would add the depth model's second onto the heads' for no reason.

## Business Rules

1. **A foundation-only run is legitimate.** `run` used to return early without a backbone,
   which is derived from the first selected head. A foundation model needs none, and
   running one with no head selected is the most likely first thing anyone does after
   installing it.
2. **Only installed foundation models are offered.** Listing an absent one puts an action
   in the runner whose only outcome is a 409 telling you to go to the admin panel — which
   is where you would have had to go anyway.
3. **A failed foundation listing is not fatal.** Heads still run; the section is simply
   absent. A model catalogue being unhappy must not take down the panel.
4. **`passes` counts backbone passes only.** A foundation model runs its own forward and is
   not one of them, or doc 18's "two framings collapse seven head types" stops measuring
   what it claims.
5. **They are a separate group in the panel, not a filtered view of the heads.** They have
   no backbone, so `isIncompatible` has nothing to say about them and the backbone tooltip
   would be meaningless. The Run button counts both, because a button that stays dead after
   ticking something reads as broken.
6. **The licence rides along into the viewer.** This is where a user meets a model they
   already installed, and "may I use this output?" is asked here rather than in Admin.

## Data Flow

`GET /api/v1/foundation` → `foundations` (filtered to installed) → checkbox group.
`POST /api/v1/foundation/predict` → `Prediction` → merged into `ComposedResult.predictions`
→ `SideBySideViewer` pane → `renderOverlayFor`, which dispatches on `render_hint` and has
never known what produced the payload.

`isPrediction` is exported from `api/inference.ts` and reused rather than copied: both
endpoints return the shape by design, and a second guard would be free to drift.

## Dependencies

- **36-depth-foundation-model** — the endpoints.
- **34-inference-picker-upfront** — the panel this extends, and its `runDisabled` split.
- **19-side-by-side-viewer** — the N-up panes, unchanged.

## Security

None new. The frontend never maps an id to an implementation; it posts the id and the
backend's registry lookup is what rejects anything unknown.

## Verified

In the running app on 2026-08-20, against real weights. Selected **DINOv2 linear depth
(NYUd)** and **Depth Anything V2 (small)** together over a chess photograph: both endpoints
fired concurrently, three panes rendered (original + both depth maps), and the header read
`1 backbone pass · 439 ms` — one, not two, which is the counting rule holding.

The comparison is the point and it is stark: the trained linear head is coarse and noisy —
it is a linear probe on a 37×37 patch grid — while the foundation model resolves the board
as a clean receding plane with sharp edges and the piece standing on it. That is precisely
the judgement the wave exists to let a user make for themselves.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
