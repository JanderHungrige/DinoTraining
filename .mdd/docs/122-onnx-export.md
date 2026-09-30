---
id: 122-onnx-export
title: ONNX Export — Backbone and Head as One Graph, Checked Against PyTorch at Export Time
edition: DinoTraining
depends_on: [121-export-bundle]
relates: [120-model-card]
source_files:
  - backend/app/mlops/onnx_export.py
  - backend/app/mlops/export.py
  - backend/app/mlops/export_texts.py
  - backend/app/api/v1/model_exports.py
  - backend/pyproject.toml
  - scripts/dev.sh
  - README.md
  - .github/workflows/release.yml
routes: []
models: []
test_files:
  - backend/tests/test_onnx_export.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [mlops, onnx, export, onnxruntime]
path: MLOps/ONNX
initiative: dinotraining
wave: dinotraining-wave-15-6
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The TorchScript exporter (`dynamo=False`) is deprecated in torch 2.x; when it is removed, switch to the dynamo exporter (onnxscript is already installed) and re-check parity."
  - "The packaged sidecar now installs `.[export]`; whether PyInstaller collects onnxruntime's native library correctly is verified only by the next release build."
security_read_sites: []
sister_projects: []
---

# 122 — ONNX Export

## Purpose

- **Who it is for:** an application that is not Python (C++, C#, Java, the web) runs ONNX
  with onnxruntime.
- **What goes into the bundle:** a trained head's bundle gets `model.onnx`, the base model
  and the head as **one graph**. The pictures go in as `pixel_values`, and the head's raw
  outputs come out.

## How

- **The wrapped model:** `pixel_values → base model → token split (num_prefix_tokens,
  grid) → head → outputs`. The token split is the app's `_split_tokens`, so the ONNX graph
  splits exactly as the app does.
- **The export:** `torch.onnx.export` with the TorchScript exporter (`dynamo=False`),
  opset 18.
  - **Input:** `pixel_values` `(batch, 3, size, size)` float32, with the batch dimension
    dynamic. `size` is fixed to the card's preprocessing size, because the grid is part
    of the graph.
  - **Outputs:** named after the head's output keys, in sorted order (e.g. detection
    `box_ltrb`, `centerness`, `logits`).
- **Checked at export time:**
  - onnxruntime runs the file on a random input, and the largest absolute difference to
    PyTorch is written into the card.
  - Above `1e-3` the export is refused, with the number.
- **The card's `onnx` section:** file, input name and shape, output names and shapes,
  opset, exporter, `max_abs_diff`.
  - The preprocessing is the card's `preprocessing` block.
  - The decoding is `outputs.decode`; for detection, `dino_runtime.detection_decode` works
    on onnxruntime's outputs converted to tensors.

## When it is not offered

- **The four trainable head types only**, with the backbone installed (the same condition
  as the runtime).
- **Not for fine-tuned SAM or RF-DETR models;** the card's `onnx.note` says why.
  - SAM's prompt encoder and its mask decoder's image-size handling do not trace as one
    graph.
  - RF-DETR ships its own export tool.
- **The `onnx` / `onnxruntime` packages** are an optional extra (`pip install
  .[export]`, part of the desktop build). Without them the bundle has no `model.onnx`, and
  the card says to install them.

## API

- `POST /api/v1/exports` takes `onnx` (default `true`). Exporting a DINOv2-small head adds
  ~90 MB and ~2 s.

## Rules

1. **No `model.onnx` without its parity check passing.**
2. **The fixed input size is stated** in the card and the README. Feeding another size is
   an onnxruntime shape error, not a silent wrong answer.

## Verified (2026-09-30)

- **Tests:** `test_onnx_export.py` (4), on a tiny real DINOv2 built from a config.
  - One graph, and the outputs match PyTorch within 1e-4.
  - The batch is dynamic (2 pictures).
  - The export is refused above the limit.
  - The app's cached backbone is untouched.
  - Backend: 1869 green; ruff and mypy clean.
- **Live**, on the real head "Object detection: person +2 more" (DINOv2-small):
  - The export zip now holds `model.onnx` (89 MB).
  - The card's `onnx` section: `pixel_values` (batch, 3, 448, 448), outputs `box_ltrb`,
    `centerness`, `class_logits`, opset 18, `max_abs_diff` 4.1e-5.
  - In the unzipped folder, the README's onnxruntime snippet plus the runtime's
    `detection_decode` and `build_payload` gave the same 12 boxes and classes as the
    PyTorch path, at most 4.4e-5 px apart.
- **Installs:** the README and `dev.sh` install `backend[dev,export]`; the release build
  installs `.[export]`.

## Bugs

(none yet)
