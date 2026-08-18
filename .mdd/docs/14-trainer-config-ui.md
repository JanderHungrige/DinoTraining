---
id: 14-trainer-config-ui
title: Head Trainer Tab — Config, Live Progress and Saved Heads
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-2
wave_status: active
depends_on: [08-head-registry, 12-head-instance-registry, 13-training-metrics-stream]
relates: [07-backbone-feature-extractor]
source_files:
  - apps/frontend/src/hooks/useTrainerOptions.ts
  - apps/frontend/src/hooks/useTrainingRun.ts
  - apps/frontend/src/components/TrainerForm.tsx
  - apps/frontend/src/components/TrainingProgress.tsx
  - apps/frontend/src/components/HeadInstanceList.tsx
  - apps/frontend/src/tabs/HeadTrainerTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/components/TrainingProgress.test.tsx
  - apps/frontend/src/components/TrainerForm.test.tsx
data_flow: greenfield
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [head-trainer, ui, live-metrics, sse, accessibility, react]
path: Training/UI
integration_contracts: []
satisfies_contracts:
  - from: 13-training-metrics-stream
    function: streamTrainingJob(jobId, handlers)
    when: showing live progress for a running job
    status: done
    verified_at: "apps/frontend/src/hooks/useTrainingRun.ts:57"
  - from: 12-head-instance-registry
    function: listHeadInstances()
    when: listing heads the user has trained
    status: done
    verified_at: "apps/frontend/src/tabs/HeadTrainerTab.tsx:31"
  - from: 08-head-registry
    function: listHeadTypes(backbone)
    when: offering head types, with compatibility against the chosen backbone
    status: done
    verified_at: "apps/frontend/src/hooks/useTrainerOptions.ts:65"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 14 — Head Trainer Tab

## Purpose

The visible half of Wave 2: pick datasets, a backbone and a head type, start training,
watch loss and metrics arrive live, and see the saved head appear. Everything it renders
comes from the backend registries — the UI declares no task, metric or head type of its
own.

## Architecture

```
useTrainerOptions   datasets + backbones + head types (+ compatibility)
        │
   TrainerForm      config with good defaults, nothing required beyond selection
        │
useTrainingRun      POST /training/jobs → streamTrainingJob (SSE)
        │
 TrainingProgress   epoch table + metric series, keys read from the payload
        │
HeadInstanceList    GET /heads, refreshed when a run completes
```

### The UI hardcodes nothing task-shaped

- Head types, their descriptions and their **metric names** come from `08` via the API.
- Metric series are `metricKeys(history)` — whatever arrived. A segmenter reporting
  `miou` charts without a frontend change.
- The **primary metric is highlighted**, and which one that is comes from the job payload.
- Incompatible head types render their `incompatible_reason` rather than being greyed
  out, per the wave's requirement to explain rather than hide.
- Non-trainable types (depth) are shown as *usable but not trainable here*, pointing at
  the pretrained default — visible, not silently absent, since the user explicitly asked
  for depth to exist.

### Live progress without a chart library

Metric history renders as an accessible table plus lightweight inline SVG sparklines.
Adding a charting dependency for two series would be weight in a desktop installer for
something 40 lines of SVG does — and a table is readable by a screen reader, which a
canvas chart is not.

## Business Rules

- **Start is disabled until the selection is valid**, with the reason stated next to the
  button rather than left for the user to infer from a dead control.
- **A run survives leaving the tab.** The stream reconnects on remount and the backend
  re-sends a snapshot; saving happens server-side regardless (`13`).
- **Cancel is offered only while running** and reports the outcome.
- **`skipped_mixed_class_images` is surfaced.** Silently training on fewer images than the
  user annotated is exactly the kind of quiet loss this project keeps avoiding.

## Data Flow

Consumes `/datasets`, `/backbones`, `/head-types?backbone=`, `/training/jobs`,
`/training/jobs/{id}/events`, `/heads`. Writes nothing directly — training state lives
in the backend.

## Dependencies

`08-head-registry`, `12-head-instance-registry`, `13-training-metrics-stream`

## Security

No new surface. All calls go through the typed client's runtime guards.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
