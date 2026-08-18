---
id: 13-training-metrics-stream
title: Training API & Live Metrics Stream
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-2
wave_status: active
depends_on: [08-head-registry, 11-training-job-runner, 12-head-instance-registry]
relates: [14-trainer-config-ui]
source_files:
  - backend/app/api/v1/training.py
  - backend/app/api/v1/router.py
  - backend/app/ml/training/runner.py
  - backend/app/ml/training/job.py
  - apps/frontend/src/api/client.ts
  - apps/frontend/src/api/training.ts
routes:
  - POST /api/v1/training/jobs
  - GET /api/v1/training/jobs
  - GET /api/v1/training/jobs/{job_id}
  - GET /api/v1/training/jobs/{job_id}/events
  - POST /api/v1/training/jobs/{job_id}/cancel
models: []
test_files:
  - backend/tests/test_training_api.py
data_flow: greenfield
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [sse, live-metrics, training-api, streaming, job-polling]
path: Training/Runner
integration_contracts:
  - function: GET /training/jobs/{job_id}/events
    when: any UI showing training progress
    why: the stream is the only live view; polling the status endpoint in a loop is the thing it replaces
satisfies_contracts:
  - from: 11-training-job-runner
    function: JobRunner.submit / get / cancel
    when: every training route
    status: done
    verified_at: "backend/app/api/v1/training.py:154"
  - from: 12-head-instance-registry
    function: register_trained_head(job, spec, capabilities)
    when: a job completes with weights
    status: done
    verified_at: "backend/app/ml/training/runner.py:196"
    note: >-
      Wired as the runner's on_complete callback rather than in the SSE handler, so a run
      is saved whether or not anyone is watching the stream.
security_read_sites: []
known_issues: []
sister_projects: []
---

# 13 — Training API & Live Metrics Stream

## Purpose

The HTTP surface for training — start, poll, cancel — plus a **Server-Sent Events**
stream carrying loss and metrics as each epoch finishes. Feature `14` renders it; this
feature owns everything below the UI.

## Architecture

SSE rather than WebSocket. The traffic is strictly one-way (server → browser),
`EventSource` reconnects on its own, and it is plain HTTP so it needs no separate
upgrade path through the Tauri shell. A WebSocket would add a second protocol for no
capability we use.

```
POST /training/jobs ──► JobRunner.submit ──► worker thread
                                  │
GET  …/events  ──► async generator polls job state ──► text/event-stream
                                  │
              on completion ──► register_trained_head ──► 12
```

### Saving is a runner callback, not the stream's job

`LocalJobRunner` takes an optional `on_complete`. `get_job_runner()` wires it to
`register_trained_head`. Doing this in the SSE handler instead would mean **a run only
gets saved if someone was watching** — close the tab and the weights are lost. The
callback fires in the worker thread regardless of who is connected.

### Event shapes

| Event | When | Payload |
|---|---|---|
| `status` | on connect, and on every state change | full job status |
| `epoch` | each finished epoch | `epoch`, `train_loss`, `val_loss`, `metrics` |
| `done` | terminal state | final status + `head_instance_id` when saved |

**`metrics` is an open dict.** Keys are whatever the head type declared in `08` —
`accuracy`/`macro_f1`, `map`/`map_50`/`map_75`, `miou`/`pixel_accuracy`. Neither this
feature nor the UI may hardcode them, or adding a head type breaks the charts.

A comment heartbeat (`: ping`) goes out on idle so intermediaries do not close a
long-running connection between epochs.

## API Endpoints

- `POST /training/jobs` — body is the `TrainingConfig` fields. `404` unknown head type,
  `409` a head type that is not trainable (depth), `422` invalid config.
- `GET /training/jobs` — all jobs this process knows about, newest first.
- `GET /training/jobs/{job_id}` — one job. `404` when unknown.
- `GET /training/jobs/{job_id}/events` — SSE. `404` when unknown.
- `POST /training/jobs/{job_id}/cancel` — `{cancelled: bool}`; `false` when already
  finished, which is not an error.

## Business Rules

- **Jobs are in-memory and not persisted.** They describe a live thread; a `running` row
  surviving a restart would describe a thread that no longer exists — the same reasoning
  Wave 1 applied to download jobs. The *outcome* is durable via `12`.
- **The stream terminates.** When the job reaches a terminal state the generator emits
  `done` and returns; it never leaves a connection open on a finished job.
- **Disconnects are not errors.** A closed client is logged at debug and the generator
  exits; training continues, because the run does not belong to the viewer.
- **Depth is refused with 409, not 400.** The request is well-formed; the *state of the
  world* makes it impossible, and the message points at the pretrained default.

## Data Flow

Consumes `TrainingJob` from `11`. Produces SSE frames for `14` and, on completion, a
registered head instance in `12`.

## Dependencies

`08-head-registry`, `11-training-job-runner`, `12-head-instance-registry`

## Security

Loopback-only backend, consistent with Wave 1. `job_id` is a dictionary key, never a
path. Config fields are validated by Pydantic before reaching `TrainingConfig`, whose
own `__post_init__` is the second gate.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
