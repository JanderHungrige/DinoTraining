---
id: 16-inference-engine
title: Inference Engine — One Image, One Head, Predictions in Original Coordinates
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-3
wave_status: complete
depends_on: [07-backbone-feature-extractor, 08-head-registry, 09-head-implementations, 10-preprocessing-pipeline, 12-head-instance-registry]
relates: [11-training-job-runner, 18-multi-head-compose, 20-inference-overlay-render]
source_files:
  - backend/app/ml/inference/__init__.py
  - backend/app/ml/inference/engine.py
  - backend/app/ml/inference/results.py
  - backend/app/ml/inference/geometry.py
  - backend/app/ml/heads/decode.py
  - backend/app/ml/preprocess.py
  - backend/app/ml/training/runner.py
  - backend/app/api/v1/inference.py
  - backend/app/api/v1/router.py
routes:
  - POST /api/v1/inference
models: []
test_files:
  - backend/tests/test_inference_engine.py
  - backend/tests/test_inference_geometry.py
  - backend/tests/test_head_decode.py
  - backend/tests/test_inference_api.py
data_flow: .mdd/audits/flow-inference-engine-2026-08-18.md
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [inference, frozen-backbone, head-instances, geometry-inversion, decoders, render-hint]
path: Inference/Engine
integration_contracts:
  - function: run_inference(image, backbone_id, instance_id)
    when: any surface that needs a head's prediction for an image
    why: the single place preprocessing, decode and geometry inversion are composed in the right order
  - function: Prediction (task, render_hint, class_names, payload)
    when: rendering or comparing any inference result
    why: the renderer must dispatch off render_hint, never off a task string it re-derives
satisfies_contracts:
  - from: 07-backbone-feature-extractor
    function: extract(backbone, pixel_values)
    when: producing features for any head
    status: done
    verified_at: "backend/app/ml/inference/engine.py:109"
  - from: 07-backbone-feature-extractor
    function: read_capabilities(model_id)
    when: before planning preprocessing for a head
    status: done
    verified_at: "backend/app/ml/inference/engine.py:98"
  - from: 08-head-registry
    function: get_head_type(head_type_id)
    when: resolving task, consumes, geometry and render hint for a head instance
    status: done
    verified_at: "backend/app/ml/inference/engine.py:51"
  - from: 09-head-implementations
    function: build_head(head_type_id, capabilities, num_classes)
    when: constructing the module a stored state dict is loaded into
    status: done
    verified_at: "backend/app/ml/inference/engine.py:67"
  - from: 12-head-instance-registry
    function: HeadInstanceStore.load_weights(instance_id)
    when: loading a head's stored weights before a forward pass
    status: done
    verified_at: "backend/app/ml/inference/engine.py:70"
    note: >-
      Doc 12 also publishes list_all() and HeadInstance.summary as contracts for "any
      tab offering the user a head to run". This feature does not offer a picker — it
      runs a head it was handed — so those are satisfied by 21-same-task-head-compare
      and the viewer, not here. Recorded rather than claimed: an entry naming a
      function this feature never calls is worse than no entry.
security_read_sites: []
known_issues:
  - "`detection_decode` decodes one image, not a batch — it indexes `[0]` throughout (`heads/decode.py`). Correct for this feature, which is single-image by design, but `17-image-input-source` must loop per image rather than batching, or generalise the decoder first. Recorded so feature 17 does not rediscover it."
  - "The `masks` and `depth-map` payloads serialise a full source-resolution grid as nested JSON lists — a 900x300 image is 270k numbers, and it measured ~460 ms per call end to end. Fine on loopback for single images; `17-image-input-source` should watch this over a folder run, and RLE or a PNG response is the obvious lever if it bites."
  - "No batching and no shared backbone pass: each call runs its own forward. `18-multi-head-compose` is where that pass gets shared across heads."
sister_projects: []
---

# 16 — Inference Engine

## Purpose

Runs one image through a frozen backbone and one head instance, and returns predictions
**in the original image's coordinate system**, tagged with the head's render hint.

Wave 2 built every piece this needs. The feature's real job is to compose them in the
correct order and to close the three places where Wave 2 only ever needed the *training*
direction of a conversion.

## Architecture

```
image (PIL)  +  backbone_id  +  head_instance_id
        │
        │ 1. resolve      HeadInstanceStore.get -> head_type_id, num_classes, class_names
        │                 get_head_type          -> task, consumes, geometry, render_hint
        │                 read_capabilities      -> embed_dim, patch_size
        │
        │ 2. preprocess   plan_preprocessing(capabilities, spec)     ← derived, never passed in
        │                 prepare_images  -> pixel_values, GeometryTransform
        │
        │ 3. features     load_backbone -> extract  -> cls (B,D) + patches (B,D,Gh,Gw)
        │
        │ 4. head         build_head -> load_state_dict(strict=True) -> to(device) -> forward
        │
        │ 5. decode       decode_for(spec)   ← registry keyed by head type, never if/task
        │
        │ 6. invert       predictions back into ORIGINAL image coordinates
        ▼
   Prediction { instance_id, task, render_hint, class_names, payload, timings }
```

**Preprocessing is derived, never configured.** The API accepts no size or geometry
argument. That is doc 10's rule and it is what makes a head behave identically in the
trainer and the viewer — if the viewer could pass its own geometry, a head would score one
way during training and another way here, for reasons invisible to the user.

## Data Model

### `Prediction` (frozen dataclass)

| Field | Type | Notes |
|---|---|---|
| `instance_id` | `str` | which head produced this |
| `head_type_id`, `task` | `str` | resolved from the registry |
| `render_hint` | `RenderHint` | `labels` / `boxes` / `masks` / `depth-map` — what feature 20 dispatches on |
| `class_names` | `tuple[str, ...]` | training class order; index N here is index N in the payload |
| `payload` | `dict[str, object]` | shape depends on render hint, below |
| `grid` | `tuple[int, int]` | patch grid the head ran at, for diagnostics |
| `elapsed_ms` | `float` | so the viewer can show cost without timing it itself |

### Payload per render hint

| Hint | Payload |
|---|---|
| `labels` | `scores: list[float]` over `class_names`, plus `top: list[{index, score}]` |
| `boxes` | `boxes: list[[x,y,w,h]]` in **original image pixels**, `scores`, `classes` |
| `masks` | `mask: list[list[int]]` class index per pixel at original resolution, or RLE |
| `depth-map` | `depth: list[list[float]]` in metres at original resolution, plus `min`/`max` |

Boxes are xywh, absolute pixels, top-left origin — the dataset store's convention, so a
prediction can be reviewed or saved as an annotation in Wave 4 without a second conversion.

## API Endpoints

### `POST /api/v1/inference`

JSON: `{ image_path, backbone_id, instance_id, score_threshold? }`.

**Path-based, not multipart.** Wave 1 established that this is a desktop app whose images
live in a folder the user picked (`app/ml/images.py`), so the client sends a path and the
backend reads it. An upload endpoint would be a second input contract and would push
megabytes over loopback for a file already on the same machine.

| Status | When |
|---|---|
| `200` | prediction returned |
| `404` | unknown head instance, or no such file |
| `409` | backbone not installed — download it first |
| `409` | the head's backbone does not match the requested backbone |
| `415` | the path is not a readable image |
| `422` | malformed request, or a threshold outside 0..1 |

## Business Rules

- **The head must be moved to the backbone's device.** `build_head` returns a CPU module;
  `load_backbone` honours `settings.resolved_device`. `runner.py:135` sets the precedent
  and this must match it. Verified empirically in Wave 2: the mismatch raises at the first
  matmul, not at load, so it is invisible until a real forward pass.
- **A head only runs against the backbone it was registered for.** `HeadInstance.backbone_id`
  is authoritative; running a 384-wide head against a 768-wide backbone is refused with an
  explanation rather than allowed to produce a shape error.
- **Decoding goes through `decode_for`.** No `if task ==` anywhere in this feature. The
  registry gains entries for the four head types that previously had none (see below).
- **Predictions are returned in original image coordinates.** The caller receives numbers
  it can draw directly. Every conversion happens here, once.
- **Backbone stays frozen.** Inference runs under `torch.no_grad()` via `extract`; nothing
  in this path constructs an optimizer or touches `requires_grad`.

## Changes to existing Wave 2 code

Three gaps, all because Wave 2 only ever needed the training direction. Full reasoning in
the data-flow doc.

1. **`preprocess.py` gains `invert_boxes` / `invert_mask`** — the inverse of
   `transform_boxes` / `transform_mask`. A detector on a letterboxed 448 frame returns
   boxes in *that* frame; drawing them on a 200×900 original needs the pad and scale undone.
   Without it every box is slightly wrong, which looks almost right — the worst failure mode.
2. **`DECODERS` extended from 3 entries to 7.** It covered only *trainable* head types,
   which was complete for the training loop but leaves `decode_for` raising for all four
   non-trainable types — including all three default heads this wave uses as its smoke test.
   The four additions are `identity_decode`.
3. **`decode.py` moves from `training/` to `heads/`.** It is keyed by head-type id, imports
   only from `heads.*`, and now has two consumers. Leaving it under `training/` would make
   the inference engine import from the training package and misdescribe the dependency.
   Two importers, both updated; the test file is renamed to match.

`test_unknown_head_type_raises` used `linear-depth` as its example of an unregistered type.
The *intent* — a missing decoder raises rather than silently returning identity — is kept;
the example changes to a genuinely unregistered spec, because depth now has a decoder.

## Data Flow

See `.mdd/audits/flow-inference-engine-2026-08-18.md`.

## Dependencies

`07` (features + capabilities), `08` (head-type contract), `09` (`build_head`, box decode),
`10` (preprocessing plan + geometry), `12` (instance lookup + safetensors weights).

## Security

Accepts an uploaded image and two registry ids. `instance_id` and `backbone_id` are lookup
keys, never path components. The image is decoded with Pillow behind a size ceiling — the
same boundary `04-grounding-dino-annotator` established for uploaded imagery.

**No new deserialisation path.** Weights come only from `HeadInstanceStore.load_weights`
(safetensors), so doc 15's property that the app has no reachable pickle branch survives
this wave unchanged.

## Known Issues

- `detection_decode` decodes one image, not a batch — it indexes `[0]` throughout
  (`heads/decode.py`). Correct for this feature, which is single-image by design, but
  `17-image-input-source` must loop per image rather than batching, or generalise the
  decoder first. Recorded here so feature 17 does not discover it as a surprise.
- The `masks` and `depth-map` payloads serialise a full source-resolution grid as nested
  JSON lists — a 900x300 image is 270k numbers. Fine on loopback for single images;
  `17-image-input-source` should watch this over a folder run, and RLE or a PNG response
  is the obvious lever if it bites.
- No batching. Each call runs one backbone forward pass; `18-multi-head-compose` is where
  that pass gets shared across heads.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
