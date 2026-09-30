---
id: dinotraining-wave-15-6
title: "Wave 15.6: MLOps — model cards, export, ONNX and MLflow"
initiative: dinotraining
initiative_version: 14
status: in_progress
depends_on: dinotraining-wave-15-5
demo_state: "A head trained here appears live in a local MLflow server (params, recipe, per-epoch metrics, the model card and export bundle as artifacts, a registered model version); in the Library, Export writes a zip whose predict.py reproduces the app's predictions on a picture, and whose ONNX file gives the same outputs in onnxruntime; models trained before are sent to MLflow in one step."
created: 2026-09-30
hash: 2204d9c3
---

# Wave 15.6: MLOps — model cards, export, ONNX and MLflow

**Jan's request (2026-09-30):**
- "Trainierte Modelle sollten exportiert werden können … was alles gebraucht wird, um es
  in eine Applikation einzubinden."
- "Eine weitere neue Wave zum Thema MLOps … eine Schnittstelle für MLOps-Tools, z. B.
  MLflow."
- Order: before the website. The recipe stays as it is: required for fine-tuning,
  optional for heads.

## What already exists

- **Heads:**
  - One `.safetensors` file of a few KB in `data/heads/<id>.safetensors`.
  - Everything needed to use it lives only in SQLite (`head_instances`): backbone, head
    type, class names in order, datasets, config, best metrics.
  - The modules are in `app/ml/heads/modules.py`, the decoding in `decode.py`.
- **Fine-tuned foundation models:** `foundation-instances/<id>/instance.json`, with weights
  of kind `sam-mask-decoder`, RF-DETR or DINO.
  - Some are `.pt` (pickle).
- **Training history (per-epoch metrics):** in memory while a job runs. Only the best
  epoch's metrics are persisted.
- **The job runners** are pluggable (local now, a hyperscaler later, doc 11). Training
  goes through them, never through the UI.
- **Our own API** is open: REST `/api/v1` with OpenAPI, and MCP.

## Decisions

- **The model card is the contract.** One JSON (`model.json`) says everything an
  application needs:
  - identity, task, backbone (id, HuggingFace repo and revision);
  - head type, classes in order;
  - preprocessing (size, normalisation, fit, tiling);
  - how to decode the outputs;
  - metrics, training (epochs, datasets, recipe);
  - licences.
  - Export, ONNX and MLflow all carry the same card.
- **MLflow through its REST API** (`/api/2.0/mlflow/...`), not the `mlflow` Python package.
  - The package pulls in a large dependency tree; the few calls we need are plain HTTP.
  - A `Tracker` interface keeps other tools (Weights & Biases, ClearML) possible later.
- **Tracking never breaks training.** An unreachable MLflow is a job note and a log
  warning; the model is still saved.
- **Credentials** (`MLFLOW_TRACKING_USERNAME` / `_PASSWORD` or `_TOKEN`) live in `.env`,
  like `HF_TOKEN`. They are never shown or logged.
- **ONNX where the model allows it:** DINO backbone + head, as one graph.
  - SAM fine-tunes are exported as weights plus card only; the card says why.
  - `onnx` / `onnxruntime` are optional dependencies (an "export" extra), checked at use.

## Demo-State

1. **Settings:** in Admin, MLflow is set up (tracking URI of a local `mlflow server`;
   experiment "DinoTraining"). "Test connection" says it can reach it.
2. **A head is trained** here (3 epochs). The MLflow UI shows the run live:
   - params: settings and recipe;
   - tags: datasets and backbone;
   - the metric curves per epoch.
   - At the end: `model.json` and the export zip as artifacts, and a registered model
     version.
3. **Library → Export** writes `<name>.zip`:
   - `model.json`, weights (`.safetensors`), `head.py`, `predict.py` and `README.md`;
   - `model.onnx` for a DINO head.
   - Unzipped in a fresh folder with the listed requirements, `python predict.py
     picture.jpg` prints the same predictions the Inference Viewer shows.
   - `model.onnx` in onnxruntime gives the same outputs within 1e-4.
4. **"Show where it is"** opens the model's folder.
5. **"Send existing models to MLflow"** creates one run per model trained before, with its
   card and final metrics. Models already sent are skipped.
6. **MCP:** `get_model_card`, `export_model`, `get_mlflow_status`.

*(This wave is not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | model-card | docs/120-model-card.md | complete | — |
| 2 | export-bundle | docs/121-export-bundle.md | complete | model-card |
| 3 | onnx-export | docs/122-onnx-export.md | complete | export-bundle |
| 4 | mlflow-tracking | docs/123-mlflow-tracking.md | complete | model-card |
| 5 | mlflow-backfill | docs/124-mlflow-backfill.md | planned | mlflow-tracking, export-bundle |

### Feature notes

1. **model-card (120).**
   - `ModelCard` built from a head instance or a fine-tuned instance.
   - `GET /api/v1/models/{kind}/{id}/card`; the MCP tool `get_model_card`.
   - Per-epoch history is persisted from now on (in the instance's config / `instance.json`),
     so cards and MLflow have curves.
   - Older models say "history not recorded".
2. **export-bundle (121).**
   - `POST /api/v1/exports` writes a zip to a folder the user picked (the desktop dialog),
     or streams it (browser).
   - `.pt` weights are converted to safetensors.
   - `head.py` is the head's module source, standalone; `predict.py` is a runnable
     example using `transformers` for the backbone.
   - The README lists the requirements, with pinned versions from our environment.
   - Library: "Export" and "Show where it is" per model. MCP: `export_model`.
3. **onnx-export (122).**
   - DINO backbone + head traced into one ONNX graph with dynamic batch. The outputs are
     the raw head outputs; the card says how to decode them.
   - Parity checked with onnxruntime at export time; the bundle records the maximum
     difference.
   - Not offered where it cannot work, with the reason.
4. **mlflow-tracking (123).**
   - Settings (URI, experiment, register models on/off) and `.env` credentials.
   - `GET /api/v1/mlops/status` and "Test connection".
   - A `Tracker` with an MLflow REST implementation, hooked into both runners:
     - run created at start (params, tags);
     - metrics per epoch;
     - at the end: status, card and bundle as artifacts, registered model version.
   - Failures become job notes. The MCP tool `get_mlflow_status`.
5. **mlflow-backfill (124).**
   - "Send existing models to MLflow" (Admin) and MCP: one run per stored model with its
     card, final metrics, params and tags.
   - Idempotent through a tag holding our model id.

## Open Research

- **Artifact upload:** does the MLflow server's proxied artifact store accept
  `PUT /api/2.0/mlflow-artifacts/artifacts/<exp>/<run>/artifacts/<file>`? Verify live
  against `mlflow server` (installed in a scratch venv, not in the app).
- **Model Registry `source`:** `runs:/<run_id>/<path>` versus the artifact URI. Check
  which one the registry accepts over REST.
- **ONNX:**
  - Does DINOv2/v3 from `transformers` trace cleanly at our torch version?
  - Is the interpolated position embedding (variable input size) exportable, or does the
    card fix the input size?
