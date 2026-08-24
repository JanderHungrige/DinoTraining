---
id: 36-depth-foundation-model
title: Depth Foundation Model — One Model, One Prediction, No Head
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-6
wave_status: complete
depends_on: [02-model-manager, 16-inference-engine, 35-model-licence-surfacing]
relates: [20-inference-overlay-render, 23-mask-annotator-registry, 37-foundation-model-in-viewer]
source_files:
  - backend/app/ml/foundation/registry.py
  - backend/app/ml/foundation/depth.py
  - backend/app/ml/foundation/build.py
  - backend/app/ml/inference/payloads.py
  - backend/app/ml/registry.py
  - backend/app/api/v1/foundation.py
  - backend/app/api/v1/router.py
routes:
  - GET /api/v1/foundation
  - POST /api/v1/foundation/predict
models: []
test_files:
  - backend/tests/test_foundation.py
  - backend/tests/test_foundation_api.py
  - backend/tests/test_registry.py
data_flow: greenfield
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [foundation-model, depth-anything, depth-estimation, registry, licensing, transformers]
path: Inference/Compare
integration_contracts:
  - consumer: 37-foundation-model-in-viewer
    function: "build_foundation(id)"
    when: "any code that maps a foundation id to an implementation"
satisfies_contracts:
  - from: 35-model-licence-surfacing
    function: "ModelSpec(non_commercial=…)"
    when: "any catalogue entry whose licence forbids commercial use"
    status: done
    verified_at: "backend/app/ml/registry.py — depth-anything-v2-base/-large"
security_read_sites: []
known_issues:
  - "Only the monocular path is used. DA V2 is single-image by construction, so the multi-view question the wave doc raised does not arise for it — but it will for whatever replaces it, and `FoundationModel.predict` takes one image."
  - "`build_foundation` caches instances process-wide and forever. Fine for three small depth models; a catalogue with several multi-GB foundation models would want eviction, and the cache is the place to put it."
  - "`predict` returns a `Prediction` whose `instance_id` is the *foundation* id. Nothing collides today because head-instance ids are uuid hex, but the two namespaces are only distinct by convention."
  - "Depth Anything **3** is not takeable — no transformers integration, and its package pins `numpy<2` against this environment's 2.5.2. Recorded in `.mdd/BACKLOG.md`; when it gains support it is a catalogue entry plus one case in `build_foundation`."
sister_projects: []
---

# 36 — Depth Foundation Model

## Purpose

Add a **self-contained** model — one that predicts without a trained head — to an app whose
whole inference path is built around backbone + head, without bending either concept.

## Architecture

This is the wave's main design question, and the code answers it. `run_heads` (doc 18)
exists to cache **one backbone forward** and fan it out to N heads sharing a `PassKey`.
Depth Anything V2 is a complete predictor — its own DINOv2 variant, its own DPT head, its
own preprocessing — so it cannot share that pass with anything. Registering it as a
`HeadInstance` whose backbone is itself would put a branch inside the one module that
deliberately never branches on what it is running.

So it gets its own contract, keyed by id, **exactly mirroring Wave 4's `MaskAnnotator`**:

```
FoundationSpec (registry.py)   what the app offers
        │
build_foundation(id)           the ONLY id → implementation map
        │
DepthAnythingModel.predict()   image → Prediction(render_hint="depth-map")
        │
        └─▶ the same Prediction a head produces — so the viewer and the
            overlay registry need no new concepts
```

Both paths converge on `Prediction`. That is the registry working as designed rather than
being worked around: doc 20 dispatches on `render_hint` and has never known what produced
the payload.

### Depth Anything V2, not V3

V3 was the wave's plan and is not loadable here:

- Its `config.json` is **not a transformers config** — no `architectures`, no `model_type`,
  only a bespoke `__object__` block naming `depth_anything_3.model.da3`. `AutoModel` cannot
  open it.
- The `depth-anything-3` package requires **`numpy<2`**; this environment runs numpy 2.5.2
  under torch 2.13. It also pulls `open3d`, `evo`, `e3nn`, a pinned `moviepy==1.0.3` and a
  second `fastapi`.

Same reasoning that took SAM 3 over SAM 3.1. Confirmed with Jan; V3 is in the backlog.

## Data Model

Three catalogue entries. **Only Small is Apache-2.0** — which is why doc 35 ran first:

| id | size | licence | `non_commercial` |
|---|---|---|---|
| `depth-anything-v2-small` | 95 MB | Apache-2.0 | `False` |
| `depth-anything-v2-base` | 371 MB | CC BY-NC 4.0 | `True` |
| `depth-anything-v2-large` | 1250 MB | CC BY-NC 4.0 | `True` |

## API Endpoints

### `GET /api/v1/foundation`
Lists what is offered, with `installed`, `licence`, `non_commercial`, `approx_size_mb` and
`render_hint`. The licence appears here as well as in the admin panel because the viewer is
where a user meets a model they already installed, and "may I use this output?" is asked
there.

### `POST /api/v1/foundation/predict`
`{image_path, foundation_id}` → the same `PredictionResponse` a head returns.

| Case | Status |
|---|---|
| model not downloaded | **409** — it exists, the fix is to download it |
| unknown foundation id | 404 |
| image missing | 404 |
| image unreadable | 415 |
| anything else invalid | 422 |

## Business Rules

1. **`build_foundation` is the only id → implementation map.** A
   `if foundation_id == "…"` anywhere else is a defect, exactly as `task ===` is in
   `components/overlays/`. A test greps for `DepthAnythingModel(` outside `build.py` and
   `depth.py`.
2. **Weights are never auto-downloaded.** The loader checks `is_installed` *before*
   `from_pretrained`, which would otherwise reach the network. Added to the existing
   every-loader-refuses test rather than tested separately.
3. **The depth encoding is shared, not reimplemented.** `encode_depth_map` was split out of
   `depth_payload` so a foundation model's map and a trained head's are byte-identical in
   shape. They arrive by different routes — the head through letterbox geometry, this
   through the model's own processor — and the renderer must not be able to tell.
4. **No classes.** `class_names` is empty rather than a placeholder, so
   `Prediction.class_name` never invents one for a map that has no classes.

## Data Flow

`read_image` → `processor(images=…)` → `model(**inputs)` →
`post_process_depth_estimation(target_sizes=[(h, w)])` — which returns depth already at
**source** resolution, so none of `inference/geometry.py` applies — → `encode_depth_map` →
`Prediction` → `PredictionResponse`.

## Dependencies

- **02-model-manager** — download, cache layout, `is_installed`.
- **16-inference-engine** — `Prediction`, `PredictionResponse`, `describe`.
- **35-model-licence-surfacing** — `non_commercial`, which two of these entries need.

## Security

`foundation_id` is a registry key, never a path or a repo id — the same guarantee doc 02
gives the model catalogue, so a traversal attempt fails at the lookup. `image_path` is a
user-supplied path, handled by the existing `read_image`. No new download path: weights
come only through the admin job.

## Verified

Against real weights on 2026-08-20 — Depth Anything V2 Small, downloaded through the app's
own admin endpoint (**94 MB on disk against a 95 MB estimate**), run on MPS over a chess
photograph: a 640×640 depth map at source resolution, range 0.759–6.888, 26 KB PNG,
**873 ms** including load. The board reads as a receding plane and the single piece
separates from it — the prediction is structurally right, not merely well-shaped.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
