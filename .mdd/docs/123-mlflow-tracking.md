---
id: 123-mlflow-tracking
title: MLflow Tracking — Every Training Run Logged Live, the Model Registered, Never at the Cost of Training
edition: DinoTraining
depends_on: [120-model-card, 121-export-bundle, 11-training-job-runner, 93-finetune-framework]
relates: [124-mlflow-backfill]
source_files:
  - backend/app/core/config.py
  - backend/app/mlops/mlflow_client.py
  - backend/app/mlops/tracking.py
  - backend/app/mlops/tracking_hooks.py
  - backend/app/ml/training/job.py
  - backend/app/ml/training/runner.py
  - backend/app/finetune/runner.py
  - backend/app/api/v1/mlops.py
  - backend/app/api/v1/router.py
  - backend/app/main.py
  - backend/app/mcp/model_tools.py
  - backend/app/i18n/de_errors.py
  - apps/frontend/src/api/mlops.ts
  - apps/frontend/src/components/MlflowPanel.tsx
  - apps/frontend/src/tabs/ApiTab.tsx
  - apps/frontend/src/i18n/en/admin.ts
  - apps/frontend/src/i18n/de/admin.ts
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/mlops/status
  - PUT /api/v1/mlops/settings
  - DELETE /api/v1/mlops/settings
  - POST /api/v1/mlops/test
models: []
test_files:
  - backend/tests/test_mlflow_client.py
  - backend/tests/test_mlflow_tracking.py
  - apps/frontend/src/components/MlflowPanel.test.tsx
  - backend/tests/test_finetune_runner.py
  - backend/tests/test_mcp_server.py
  - backend/tests/conftest.py
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [mlops, mlflow, tracking, model-registry, training]
path: MLOps/MLflow
initiative: dinotraining
wave: dinotraining-wave-15-6
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "If saving a head fails after a complete run (disk full), its MLflow run stays RUNNING: the run ends on 'saved', which then never comes. The job itself says the save failed."
  - "Artifacts are uploaded through the server's artifact proxy only; a server with a client-side artifact store (s3://, file://) is refused with the fix (--serve-artifacts)."
security_read_sites:
  - backend/app/mlops/mlflow_client.py (MLFLOW_TRACKING_PASSWORD / MLFLOW_TRACKING_TOKEN, sent as HTTP auth, never logged)
sister_projects: []
---

# 123 — MLflow Tracking

## Purpose

- **Jan:** "an interface for MLOps tools, e.g. MLflow".
- **What it does:** every head training and every fine-tune shows up in the user's MLflow
  as a run:
  - its settings and recipe as params;
  - its data and base model as tags;
  - its metrics per epoch.
  - At the end: the model card and the export bundle as artifacts, and a registered model
    version.

## MLflow's REST API, verified against a real server (2.x)

| Call | Path |
|---|---|
| experiment by name / create | `GET /api/2.0/mlflow/experiments/get-by-name`, `POST …/experiments/create` |
| run | `POST …/runs/create` (returns `artifact_uri` `mlflow-artifacts:/<exp>/<run>/artifacts`), `POST …/runs/update` (status, end time) |
| params, metrics, tags | `POST …/runs/log-batch` (≤ 100 params and ≤ 1000 metrics per call; chunked) |
| artifacts | `PUT /api/2.0/mlflow-artifacts/artifacts/<exp>/<run>/artifacts/<path>` (the server's artifact proxy) |
| registry | `POST …/registered-models/create` (already existing is fine), `POST …/model-versions/create` with `source: runs:/<run>/model` |

- **A documentation mismatch:** the docs page lists the registry under
  `…/mlflow/model-registry/…`. The server answers only `…/mlflow/registered-models/…`, as
  checked live.
- **No `mlflow` package:** plain `httpx` with a 10 s timeout. `MlflowClient` is the only
  place these paths live.

## Settings (`.env`, like `HF_TOKEN`)

| Key | Meaning |
|---|---|
| `MLFLOW_TRACKING_URI` | e.g. `http://127.0.0.1:5001`. Unset means tracking is off. |
| `DINO_MLFLOW_EXPERIMENT` | experiment name, default `DinoTraining` |
| `DINO_MLFLOW_REGISTER` | register each saved model (default on) |
| `MLFLOW_TRACKING_USERNAME` / `MLFLOW_TRACKING_PASSWORD` | HTTP Basic (MLflow's basic-auth app) |
| `MLFLOW_TRACKING_TOKEN` | bearer token (hosted MLflow) |

- The `MLFLOW_*` names are MLflow's own, so an existing setup carries over.
- **Admin → Connection → MLflow:**
  - the URI, experiment, register on/off, and the credentials (write-only);
  - **Test connection**, which says whether the server answered and the experiment exists
    or was created;
  - **Disconnect**.
- **The API:**
  - `GET /mlops/status` never returns a secret, only whether one is set;
  - `PUT` / `DELETE /mlops/settings`;
  - `POST /mlops/test`.

## What a run holds

| | Head training | Fine-tune |
|---|---|---|
| run name | the job's name, or head type and datasets | the fine-tune's name |
| params | the training config (flattened; values over 500 characters shortened) | the parameter set |
| tags | `dinotraining.kind`, `dinotraining.base`, datasets, recipe, app version; `dinotraining.model` = `heads:<id>` once saved | same, with `finetuned:<id>` |
| metrics | `train_loss`, `val_loss` and each metric, with step = epoch | `train_loss` and each metric per epoch, plus `baseline_*` |
| artifacts | `model/model.json` (the card), `model/<name>.zip` (the bundle, without ONNX to keep runs light) | the same |
| registry | registered model `<name>` gets a new version from `runs:/<run>/model` | the same |
| end | `FINISHED` / `FAILED` / `KILLED` (cancelled) | the same |

## Never at the cost of training

- Every MLflow call is caught.
- **The first failure** (unreachable, 401, 5xx) disables tracking for the rest of that
  job. It is written into the job's notes as "MLflow: …", which the Training tab already
  shows, and logged with context.
- The model is saved regardless.
- A run whose job fails or is cancelled is ended with that status.

## How it hooks in

- **Head training:**
  - `TrainingJob` gains listeners, called on each recorded epoch and on finish.
  - A hook registered at startup (`tracking_hooks.install`) attaches a tracker to each new
    job when MLflow is configured.
  - Saving goes through the runner's existing `on_complete`, wrapped to upload and
    register afterwards.
  - `runner.py` stays under 300 lines.
- **Fine-tuning:** the runner calls the tracker directly at start, per epoch, on save and
  at the end.
- **MCP `get_mlflow_status`:** configured, reachable, experiment. An agent can tell the user
  where the runs are.

## Verified (2026-09-30)

- **Tests:**
  - `test_mlflow_client.py` (6), against a simulated server:
    - experiment create, run, params in batches of 100;
    - artifact proxy path, registry with an existing model;
    - a local artifact store refused with the fix;
    - Basic and Bearer auth;
    - unreachable, and not set up.
  - `test_mlflow_tracking.py` (9):
    - the run begins on the first epoch;
    - the first failure is one note, and the run is still ended;
    - a head run logs epochs, then the saved model, then FINISHED; cancelled ends KILLED;
    - without MLflow nothing is attached;
    - `.env` settings, and secrets never come back;
    - a scheme-less URI is refused;
    - a registry name has no ':' or '/'.
  - `test_finetune_runner.py`: a fine-tune reports its baseline, epochs 1–3 and the saved
    model.
  - `MlflowPanel.test.tsx` (2).
  - The test isolation also removes `MLFLOW_*` from the environment, so a developer's
    MLflow never receives test runs.
  - Backend: 1885 green; frontend: 1094; ruff, mypy and tsc clean.
- **Live, against a real MLflow 3 server** (`mlflow server` on 127.0.0.1:5055 in a scratch
  venv):
  - Admin → Connection → MLflow: saving the URI and pressing "Verbindung testen" answered
    "Verbunden. Das Experiment „DinoTraining“ hat die ID 2."
  - A dense detector head was trained for 3 epochs on "Wave 11 intake check". MLflow
    showed:
    - 22 params and the `dinotraining.*` tags;
    - `val_loss` at steps 1–3 (1.514 → 1.392 → 1.224), and `map` per epoch;
    - `model/model.json` and the bundle zip as artifacts;
    - the run FINISHED;
    - registered model "Object detection - black-bishop +11 more", version 1.
- **Found live and fixed:**
  1. MLflow refuses ':' and '/' in registered model names, and the app's names have them
     ("Object detection: …"). The registration failed; the job said so and trained on.
     Names are now cleaned (`registry_name`).
  2. That failure left the run RUNNING, because tracking was off after the first error.
     Ending the run is now always tried, best effort, with no second note.
  3. The documentation lists the registry under `…/model-registry/…`; the server serves
     it at `…/mlflow/registered-models/…`.

## Bugs

(none yet)
