---
id: 10-preprocessing-pipeline
title: Preprocessing Pipeline — Task-Aware Geometry With Targets That Follow
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-2
wave_status: active
depends_on: [07-backbone-feature-extractor, 08-head-registry]
relates: [09-head-implementations]
source_files:
  - backend/app/ml/preprocess.py
test_files:
  - backend/tests/test_preprocess.py
routes: []
models: []
data_flow: greenfield
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [preprocessing, letterbox, center-crop, target-transform, augmentation, geometry]
path: Training/Preprocessing
integration_contracts:
  - function: plan_preprocessing(capabilities, spec)
    when: any code path that turns an image into pixel_values for a head
    why: preprocessing is derived from backbone + head, never chosen by the user or a caller
  - function: apply_geometry(plan, image)
    when: preparing any image whose annotations must stay aligned
    why: returns the GeometryTransform that targets must be passed through; skipping it is the silent-drop bug
satisfies_contracts:
  - from: 08-head-registry
    function: HeadTypeSpec.geometry
    when: deriving the plan — geometry is read from the spec, never inferred from task
    status: done
    verified_at: "backend/app/ml/preprocess.py:107"
    note: >-
      This module consumes a HeadTypeSpec it is handed; resolving a head-type id via
      get_head_type() is the caller's job and lands with 11-training-job-runner. Recorded
      as the spec-field contract rather than the lookup so the entry describes a call site
      that actually exists here.
security_read_sites: []
known_issues: []
sister_projects: []
---

# 10 — Preprocessing Pipeline

## Purpose

Turns a PIL image into `pixel_values` for a given backbone + head, and — the part that
actually matters — returns the geometry transform so **boxes and masks can be moved
through exactly the same operation**. This is the feature that pays off the finding in
`07`: the stock processor centre-crops, which silently deletes annotations for dense
tasks while training loss still looks healthy.

Per `CLAUDE.md`, preprocessing is **derived internally from the chosen backbone + head**
— never asked of the user, never passed in by a caller.

## Architecture

```
plan_preprocessing(capabilities, spec) → PreprocessPlan   (size, geometry, mean/std)
                    │
apply_geometry(plan, image) → (resized PIL image, GeometryTransform)
                    │                                  │
        to_pixel_values(plan, image)        transform_boxes / transform_mask
                    ▼                                  ▼
             (1, 3, H, W) tensor                 targets in the same frame
```

`GeometryTransform` is the whole design. It records `scale`, `pad_x`, `pad_y` and the
output size, so a target transform is not a re-derivation of what happened to the image
— it *is* what happened to the image.

### The two geometries

| Geometry | Used by | Operation | Can annotations be lost? |
|---|---|---|---|
| `center-crop` | classification | resize shortest edge, crop centre | **Yes** — anything outside the crop |
| `aspect-preserve` | detection, segmentation, depth | letterbox: scale to fit, pad the remainder | **No** — nothing leaves the frame |

Letterboxing is chosen for dense tasks precisely because it is lossless: every pixel of
the original survives, so no box or mask region can fall outside. Padding costs some
resolution; silently dropping ground truth costs a model that trains to nothing for
reasons nobody can see.

`center-crop` remains correct for classification, where the target is one label for the
whole image and geometry cannot invalidate it.

### Output size

Derived, and always a multiple of `patch_size` — `07` rejects indivisible inputs, so a
non-conforming size would fail at the forward pass instead of here.

- classification → 224 → 16×16 grid at patch 14
- dense tasks → 448 → 32×32 grid at patch 14

Dense tasks get the larger input because detection and segmentation quality is bounded
by grid resolution; a 16×16 grid cannot express small objects.

Normalisation reads `image_mean` / `image_std` from the model's own
`preprocessor_config.json`, falling back to ImageNet statistics. Hardcoding would break
silently for any future backbone trained with different statistics.

## Data Model

### `PreprocessPlan` (frozen)
`size: int`, `geometry: PreprocessGeometry`, `patch_size: int`, `mean/std: tuple[float,float,float]`

### `GeometryTransform` (frozen)
`scale: float`, `pad_x: float`, `pad_y: float`, `out_w: int`, `out_h: int`,
`source_size: tuple[int, int]`

## Business Rules

- **Targets move with the image or the feature is wrong.** `transform_boxes` returns
  `(boxes, keep_indices)`. The indices are not optional bookkeeping: dropping a box
  without dropping its label silently misaligns every remaining label in the sample.
- **A degenerate box after clipping is dropped, not clamped to zero area.** Zero-area
  boxes fail the dataset store's CHECK constraint and mean nothing to a loss.
- **Letterbox never drops.** A test asserts `keep_indices` covers every input box under
  `aspect-preserve`, for randomised boxes. If that ever fails, the geometry is broken.
- **Masks use nearest-neighbour.** Bilinear interpolation of a label map invents class
  ids that were never in the annotation.
- **The plan is derived, not configured.** `plan_preprocessing` takes only capabilities
  and the head spec.

## Data Flow

Greenfield. Consumes `BackboneCapabilities` (`07`) and `HeadTypeSpec.geometry` (`08`);
produces `pixel_values` for `07.extract` and aligned targets for `11-training-job-runner`.

## Dependencies

- `07-backbone-feature-extractor` — `BackboneCapabilities`, patch-size divisibility rule
- `08-head-registry` — `HeadTypeSpec.geometry`

## Security

Reads `preprocessor_config.json` from the model cache via `resolve_model_dir`, which
confines. Images arrive already decoded from callers that validated them.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
