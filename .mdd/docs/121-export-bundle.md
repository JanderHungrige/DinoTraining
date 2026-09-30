---
id: 121-export-bundle
title: Export Bundle — a Zip That Runs the Model Outside the App, Built from the App's Own Code
edition: DinoTraining
depends_on: [120-model-card]
relates: [122-onnx-export, 123-mlflow-tracking, 124-mlflow-backfill, 59-reveal-dataset-folder]
source_files:
  - backend/app/mlops/runtime_source.py
  - backend/app/mlops/runtime_glue.tmpl
  - backend/app/mlops/export.py
  - backend/app/mlops/export_texts.py
  - backend/app/api/v1/model_exports.py
  - backend/app/api/v1/router.py
  - backend/app/mcp/model_tools.py
  - apps/frontend/src/api/modelExports.ts
  - apps/frontend/src/components/LibrarySection.tsx
  - apps/frontend/src/components/ModelExportActions.tsx
  - apps/frontend/src/tabs/LibraryTab.tsx
  - apps/frontend/src/i18n/en/admin.ts
  - apps/frontend/src/i18n/de/admin.ts
  - apps/frontend/src/styles.css
  - backend/app/mlops/card.py
routes:
  - POST /api/v1/exports
  - GET /api/v1/exports/{kind}/{instance_id}/location
models: []
test_files:
  - backend/tests/test_model_export.py
  - backend/tests/test_runtime_parity.py
  - apps/frontend/src/components/ModelExportActions.test.tsx
  - backend/tests/test_mcp_server.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [mlops, export, model-card, runtime, library]
path: MLOps/Export
initiative: dinotraining
wave: dinotraining-wave-15-6
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "An export needs the backbone installed here: its config gives the preprocessing. Without it the bundle has the card and weights, and its README says the runtime could not be included."
  - "The runtime downloads the base model from HuggingFace on first use (not from the app's cache); a gated base (DINOv3) needs the user's own HF token there."
security_read_sites: []
sister_projects: []
---

# 121 — Export Bundle

## Purpose

Jan: "Trained models should be exportable … what is needed to build it into an
application." The bundle is a zip that a developer unpacks and runs, without this app.

## Contents of `<name>.zip`

| File | For a trained head | For a fine-tuned model |
|---|---|---|
| `model.json` | the card (doc 120) | the card |
| weights | `head.safetensors` | the weights as `.safetensors` (a `.pt` is converted) |
| `dino_runtime.py` | assembled from the app's own source, see below | — |
| `predict.py` | `python predict.py picture.jpg [--threshold 0.3]` prints the predictions as JSON; for masks and depth it also writes a PNG | — |
| `requirements.txt` | torch, torchvision, transformers, safetensors, pillow, numpy — pinned to the versions this app runs | — |
| `README.md` | what the model does, its classes, the three commands to run it, how to call it from code, how to read its outputs, licences | what it is (e.g. SAM 2.1's mask decoder), which base model it belongs to, and that it runs in this app; loading it elsewhere means replacing that part of the base model |
| `model.onnx` | doc 122 | — |

## The runtime is the app's code, not a copy of it

- **Why:** a hand-written `predict.py` would drift from the app, and a drifted one gives
  confident wrong answers.
- **How:** `dino_runtime.py` is **assembled at export time** from the source of the
  functions inference itself uses (`inspect.getsource`), with the `app.*` imports removed:
  - `preprocess`: `PreprocessPlan`, `GeometryTransform`, letterbox, centre crop,
    `apply_geometry`, `to_pixel_values`;
  - `backbone`: `BackboneFeatures`, the grid and token split;
  - `heads.modules`: the four trainable head modules and their helpers;
  - `heads.decode`: the decoders;
  - `inference.geometry` and `payloads`: mapping back to the picture.
  - Module constants are written as literal values.
- **Hand-written glue** (`runtime_glue.tmpl`) adds `Model.load(folder)` and
  `Model.predict(image, threshold)`. Loading reads the card, loads the backbone with
  `transformers.AutoModel.from_pretrained(card.base.repo_id)`, builds the head and loads the
  weights.
- **A parity test** (`test_runtime_parity.py`) generates the runtime and checks each piece
  against the app on the same inputs: preprocessing, token split, head forward, decode and
  payload. A change in the app that the runtime does not follow fails the build.
- **Supported:** the four trainable head types (linear classifier, dense detector, linear
  segmenter, linear depth). Pretrained defaults and community heads export weights and
  card, and their README says the runtime does not cover them yet.

## API, Library and MCP

- **`POST /api/v1/exports {kind, instance_id, destination?}`:**
  - With a `destination` folder (the desktop picker), it writes `<name>.zip` there and
    returns the path.
  - Without one (the browser), it returns the zip as a download.
  - An unknown model is a 404; a destination that is not a writable folder is a 422.
- **`GET /api/v1/exports/{kind}/{id}/location`:** the folder that holds the model, for
  "Show where it is".
- **Library:** each head and fine-tuned model gets **Export** and **Show where it is**.
  Export in the desktop app asks for a folder; in the browser it downloads.
- **MCP:** `export_model(kind, id, destination)`.

## Rules

1. **The zip never contains a local absolute path or a secret.** The card rule (doc 120)
   applies to every file.
2. **An export is a copy.** Nothing in the library is moved or changed.
3. **`.pt` weights** are loaded with `weights_only=True` before conversion, so exporting
   never runs pickled code.

## Verified (2026-09-30)

- **Tests:**
  - `test_runtime_parity.py` (8): preprocessing (both geometries), the token split, and
    for each head type the head forward, decode and payload.
    - All identical between the app and the generated `dino_runtime.py`.
    - Every trainable head type is covered.
  - `test_model_export.py` (6):
    - the zip holds the card, weights and README, and no local path;
    - no runtime without an installed backbone, and the README says so;
    - export into a folder;
    - 422 for a bad folder, 404 for an unknown model;
    - location;
    - `.pt` becomes safetensors via `weights_only`.
  - `ModelExportActions.test.tsx` (3).
  - Backend and frontend suites are green.
- **The demo's parity, live:**
  - The real head "Object detection: person +2 more" (DINOv2-small, OSDaR23) was exported
    through the API into a scratch folder, unzipped, and `python predict.py picture.png
    --threshold 0.05` was run with no app on the path.
    - The runtime fetched facebook/dinov2-small from HuggingFace itself.
  - The app's `/inference` on the same picture and head gave the same 12 boxes, classes
    signal, signal, … person, identical coordinates (0.0 px difference), scores within
    2.6e-6 (MPS against CPU). The export also names the classes.
- **Library, German:** "Exportieren" on 28 models. "Ordner zeigen" appears only in the
  desktop app, because a browser cannot open a local folder.
- **Found while building:**
  - Dataclasses in a runtime run through `exec` need the module in `sys.modules`. A real
    `import dino_runtime` has that; the parity test registers it.
  - Running `predict.py` with `python -I` drops its own folder from the path. The README
    uses plain `python`.

## Bugs

(none yet)
