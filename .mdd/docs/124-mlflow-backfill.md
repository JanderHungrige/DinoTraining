---
id: 124-mlflow-backfill
title: MLflow Backfill — the Models Trained Before, Sent in One Step, Each Once
edition: DinoTraining
depends_on: [123-mlflow-tracking, 121-export-bundle]
relates: [120-model-card]
source_files:
  - backend/app/mlops/backfill.py
  - backend/app/api/v1/mlops.py
  - backend/app/mcp/model_tools.py
  - apps/frontend/src/api/mlops.ts
  - apps/frontend/src/components/MlflowBackfill.tsx
  - apps/frontend/src/components/MlflowPanel.tsx
  - apps/frontend/src/i18n/en/admin.ts
  - apps/frontend/src/i18n/de/admin.ts
  - backend/app/mlops/mlflow_client.py
  - backend/app/i18n/de_errors.py
routes:
  - POST /api/v1/mlops/backfill
  - GET /api/v1/mlops/backfill/{job_id}
models: []
test_files:
  - backend/tests/test_mlflow_backfill.py
  - apps/frontend/src/components/MlflowBackfill.test.tsx
  - backend/tests/test_mcp_server.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [mlops, mlflow, backfill, model-registry]
path: MLOps/MLflow/Backfill
initiative: dinotraining
wave: dinotraining-wave-15-6
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 124 — MLflow Backfill

## Purpose

Jan: "Can the information be imported into MLflow somehow?" Everything trained before
MLflow was set up — trained heads and fine-tuned models — goes there in one step, as if
it had been tracked.

## What each model becomes

- **One run per model**, named after the model:
  - its start time is the model's creation time;
  - params: the stored settings (`config` or `parameters`);
  - tags: kind, base, datasets, recipe, `dinotraining.model = <kind>:<id>`, and
    `dinotraining.backfilled = true`.
- **Metrics:**
  - with a stored history (doc 120), every epoch at its step;
  - otherwise the stored final metrics at step = epochs trained;
  - a fine-tune adds its `baseline_*` at step 0.
- **Artifacts and registry:** the card and the export bundle as artifacts, and a registry
  version, exactly as a tracked run (`log_model`). The run ends FINISHED.
- **Which models:** trained heads (`trained-here`) and fine-tuned models. Pretrained
  defaults and community imports were not trained here; they are skipped and counted.

## Once each

- Before sending, the experiment is searched for a run tagged `dinotraining.model =
  <kind>:<id>`. A model already there, sent before or tracked live, is **skipped**.
- Pressing it twice sends nothing twice.

## A job, with progress

- **`POST /api/v1/mlops/backfill`** starts it in the background and returns a job:
  `{job_id, state, total, sent, skipped, failed, notes}`.
- **`GET /api/v1/mlops/backfill/{job_id}`** reads its progress.
- **A model that fails** (e.g. a file missing) is counted and named in the notes; the rest
  continue. An unreachable MLflow stops the job with that reason.
- **Admin → Connection → MLflow:** "Send existing models to MLflow" shows "12 of 28 sent,
  3 already there, 1 failed" as it runs.
- **MCP:** `send_models_to_mlflow` starts it and returns the job; `get_mlflow_status`
  (doc 123) says where the runs are.

## Verified (2026-09-30)

- **Tests:**
  - `test_mlflow_backfill.py` (2), with real stored models and a fake MLflow:
    - every model trained here is sent once;
    - a head's epochs are logged at their steps, then its finals;
    - the backfilled tag, the start time, the card and FINISHED are set;
    - a fine-tune's finals come with `baseline_*`;
    - the pretrained head is skipped;
    - pressing it again sends nothing.
  - `MlflowBackfill.test.tsx` (2).
  - Backend and frontend suites are green.
- **Live, the real library against the real MLflow 3 server:**
  - Admin → Connection → MLflow → "Bisherige Modelle an MLflow senden" counted up to
    "25 von 30 gesendet, 5 schon dort oder nicht hier trainiert, 0 fehlgeschlagen. Fertig."
    - The 5 were 3 heads not trained here (defaults, imports), with the note in German, and
      the 2 heads already tracked live in doc 123's check.
  - MLflow then held 27 runs, all FINISHED, and 15 registered model names. Models with the
    same name are versions of one registered model.
  - A second press: 0 sent, 30 skipped.

## Bugs

(none yet)
