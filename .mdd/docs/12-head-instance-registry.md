---
id: 12-head-instance-registry
title: Head Instance Registry — Provenance, Weights, and the Cross-Tab Picker Contract
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-2
wave_status: active
depends_on: [03-dataset-store, 08-head-registry, 11-training-job-runner]
relates: [15-head-catalog-import]
source_files:
  - backend/app/datasets/db.py
  - backend/app/ml/heads/instances.py
  - backend/app/ml/heads/store.py
  - backend/app/api/v1/heads.py
  - backend/app/api/v1/router.py
  - backend/app/ml/training/persist.py
  - apps/frontend/src/api/headInstances.ts
routes:
  - GET /api/v1/heads
  - GET /api/v1/heads/{instance_id}
  - DELETE /api/v1/heads/{instance_id}
models:
  - head_instances
test_files:
  - backend/tests/test_head_instances.py
  - backend/tests/test_heads_api.py
data_flow: greenfield
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [provenance, checkpoints, safetensors, head-instances, cross-tab-contract, sqlite]
path: Training/Heads
integration_contracts:
  - function: HeadInstanceStore.list_all(task=, backbone=)
    when: any tab offering the user a head to run — Waves 3 and 4
    why: heads must be presented by task, provenance and training data, never by filename
  - function: HeadInstance.summary
    when: rendering a head in any picker
    why: one description everywhere, so the same head never reads differently in two tabs
satisfies_contracts:
  - from: 11-training-job-runner
    function: TrainingJob.best_state
    when: persisting a finished run
    status: done
    verified_at: "backend/app/ml/training/persist.py:66"
  - from: 08-head-registry
    function: HeadTypeSpec (task, id, primary_metric)
    when: recording task and selection criterion on an instance
    status: done
    verified_at: "backend/app/ml/training/persist.py:61"
    note: >-
      register_trained_head is handed a resolved HeadTypeSpec by the caller that already
      ran get_head_type; recorded as the spec-consumption site so the entry names a call
      site that exists in this feature.
security_read_sites: []
known_issues: []
sister_projects: []
---

# 12 — Head Instance Registry

## Purpose

Persists trained heads with the provenance that makes them meaningful, and is the
**single contract every other tab uses to offer a head to the user**. Wave 3's viewer,
Wave 3's same-task comparison and Wave 4's expert annotator all read this one list.

## Architecture

Weights on disk, metadata in the shared SQLite index — the same split Wave 1 uses for
datasets, and for the same reason: SQL answers "which heads do this task on this
backbone" without opening a single weight file.

```
TrainingJob (best_state, history)          catalogue / community import (15)
            └──────────────┬────────────────────────┘
                  HeadInstanceStore.register_*
                           │
        data/heads/<id>.safetensors   +   head_instances row
                           │
                    list_all(task=, backbone=)  ─► Waves 3 & 4 pickers
```

**Weights are written as safetensors, including our own.** Consistency with the rule in
`15` matters more than convenience: if every head in the system is safetensors, the
loader never needs a pickle path at all, and there is no branch for an attacker to reach.

## Data Model

### `head_instances` table (schema version 2)

| Column | Notes |
|---|---|
| `id` | hex uuid |
| `name` | user-facing label, defaulted from task + datasets |
| `kind` | `pretrained-default` / `community` / `trained-here` — CHECK constrained |
| `head_type_id`, `task` | resolved through `08` |
| `backbone_id`, `backbone_family`, `embed_dim` | what it can be run against |
| `num_classes`, `class_names` | JSON array; order is the trained class order |
| `dataset_ids` | JSON array — only meaningful for `trained-here` |
| `metrics`, `primary_metric`, `primary_metric_value` | JSON + the selection criterion |
| `config` | JSON snapshot of the `TrainingConfig` |
| `source_repo`, `source_digest` | provenance for imported heads |
| `epochs_trained`, `best_epoch` | |
| `weights_path`, `created_at` | |

`class_names` order is load-bearing: index 3 in the weights means whatever index 3 meant
at training time, and nothing in a tensor file records that. Storing the order beside the
weights is what keeps a checkpoint interpretable a month later.

### `HeadInstance.summary`

A one-line description built from the record — e.g.
*"Object detection · 2 classes · trained on e2e-shapes · mAP 0.52"*, or
*"Depth estimation · pretrained default (NYUd)"*. Every picker renders this, so a head
never reads differently in two tabs.

## API Endpoints

- `GET /api/v1/heads?task=&backbone=` — the picker contract. Both filters optional;
  `task` powers same-task comparison, `backbone` hides heads that cannot run.
- `GET /api/v1/heads/{instance_id}` — full record. `404` when unknown.
- `DELETE /api/v1/heads/{instance_id}` — removes row and weights. Idempotent: deleting an
  already-absent head returns `removed: false`, not an error.

## Business Rules

- **A `trained-here` instance requires datasets, classes and a metric.** Registering a run
  with no metric would produce a head the user cannot evaluate or compare — exactly the
  filename-only listing this feature exists to prevent.
- **Deleting a row deletes its weights.** An orphaned safetensors file is invisible disk
  usage the Admin tab cannot account for.
- **Weight paths are confined** through `ensure_within` against the heads directory, never
  built by string concatenation.
- **Registration is atomic in the useful direction**: weights are written first, then the
  row. A weights file with no row is recoverable garbage; a row pointing at a missing file
  is a head that fails when selected.

## Data Flow

Consumes `TrainingJob.best_state` and `history` from `11`, and `HeadTypeSpec` from `08`.
Produces the instance list consumed by `14-trainer-config-ui`, Wave 3 and Wave 4.

## Dependencies

`03-dataset-store` (shared DB module), `08-head-registry`, `11-training-job-runner`

## Security

`instance_id` is a lookup key, never a path component until it has passed
`ensure_within`. No user-supplied paths and no deserialisation of untrusted data —
safetensors is a data-only format with no code execution path, which is the whole reason
it is used here as well as in `15`.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
