---
id: 07-backbone-feature-extractor
title: Backbone Feature Extractor — Frozen DINO Features & Capability Descriptor
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-2
wave_status: active
depends_on: [01-app-shell, 02-model-manager]
relates: []
source_files:
  - backend/app/ml/backbone.py
  - backend/app/api/v1/backbones.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/backbones.ts
  - apps/frontend/src/api/types.ts
routes:
  - GET /api/v1/backbones
models: []
test_files:
  - backend/tests/test_backbone.py
  - backend/tests/test_backbones_api.py
data_flow: greenfield
last_synced: 2026-08-17
status: complete
phase: all
mdd_version: 11
tags: [dinov2, dinov3, frozen-backbone, feature-extraction, patch-grid, capability-descriptor]
path: Training/Backbone
integration_contracts:
  - function: read_capabilities(model_id)
    when: before registering or offering any head instance for a backbone
    why: head compatibility is checked against the descriptor, never against a hardcoded assumption
  - function: extract(backbone, pixel_values)
    when: any head — training or inference — needs backbone features
    why: the single place patch tokens become a (B, D, Gh, Gw) grid; duplicating the reshape is how the register-token bug returns
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "preprocess() uses the backbone's own AutoImageProcessor, which for dinov2-small is do_resize(shortest_edge=256) + do_center_crop(224x224). Correct for classification, DESTRUCTIVE for detection and segmentation: a 200x900 image is cropped to its centre 224x224, so ground-truth boxes/masks outside the crop vanish and partial ones need clipping. Confirmed empirically — 640x480 and 200x900 both came back as (1,3,224,224). 10-preprocessing-pipeline must supply a task-aware transform (aspect-preserving resize/pad for dense tasks) and transform the targets alongside the image. Loss would look healthy while the head learns from annotations that were silently dropped."
sister_projects: []
---

# 07 — Backbone Feature Extractor

## Purpose

Turns an image into frozen DINOv2/v3 features that every head type consumes, and
publishes the **backbone capability descriptor** — patch size, embedding dimension,
prefix-token count, layer count — that head compatibility is validated against.

This is the first feature of Wave 2 and nothing else in the wave can be built before
it, because it fixes the tensor contract (`cls` vector + `(B, D, Gh, Gw)` patch grid)
that the head registry, the trainer, and later the inference viewer all depend on.

## Architecture

```
PIL image(s)
   │  preprocess()            AutoImageProcessor for this backbone
   ▼
pixel_values (B, 3, H, W)
   │  extract()               frozen forward pass, no_grad
   ▼
BackboneFeatures
   ├─ cls      (B, D)         → classification heads
   ├─ patches  (B, D, Gh, Gw) → detection / segmentation / depth heads
   └─ grid     (Gh, Gw)
```

The backbone is **frozen**: `eval()` mode, `requires_grad_(False)` on every parameter,
and the forward pass runs under `torch.no_grad()`. All three, not one — `no_grad` alone
still leaves parameters that an optimizer constructed over `model.parameters()` would
happily update.

Loaded backbones are cached per `(model_id, device)`, matching `ml/detector.py`.
Loading is seconds and hundreds of MB; per-request loading would make training and the
inference viewer unusable.

## Data Model

### `BackboneCapabilities` (frozen dataclass)

| Field | Type | Notes |
|---|---|---|
| `model_id` | `str` | Registry key, e.g. `dinov2-base` |
| `family` | `ModelFamily` | `dinov2` / `dinov3` |
| `patch_size` | `int` | 14 for DINOv2, 16 for DINOv3 |
| `embed_dim` | `int` | Head input width — the main compatibility axis |
| `num_prefix_tokens` | `int` | `1` (CLS) `+ num_register_tokens` |
| `num_layers` | `int` | For heads that may want intermediate layers |
| `image_size` | `int` | Default training resolution from the model config |

`read_capabilities(model_id)` builds this from the on-disk `config.json` **without
loading weights**. That matters: `head-catalog-import` must tell a user whether a head
fits their 1.2 GB backbone without loading it, and the Admin tab lists capabilities for
every installed backbone at once.

### `BackboneFeatures` (frozen dataclass)

| Field | Type | Notes |
|---|---|---|
| `cls` | `Tensor (B, D)` | Pooled CLS token |
| `patches` | `Tensor (B, D, Gh, Gw)` | Channels-first, so heads are plain `nn.Conv2d` |
| `grid` | `tuple[int, int]` | `(Gh, Gw)` |

## API Endpoints

### `GET /api/v1/backbones`

Lists every backbone in the catalogue with its install state and, when installed, its
capabilities. No auth (loopback-only backend, consistent with Wave 1).

```json
{
  "backbones": [
    {
      "id": "dinov2-base",
      "family": "dinov2",
      "installed": true,
      "gated": false,
      "capabilities": {
        "patch_size": 14, "embed_dim": 768, "num_prefix_tokens": 1,
        "num_layers": 12, "image_size": 518
      }
    },
    { "id": "dinov3-vitb16", "family": "dinov3", "installed": false,
      "gated": true, "capabilities": null }
  ]
}
```

`capabilities` is `null` for anything not installed — the descriptor is read from the
model's own config, so it cannot be known before download. Errors: `500` via the global
handler only; an unreadable config for one backbone degrades that entry to
`capabilities: null` rather than failing the whole list.

## Business Rules

- **Never download implicitly.** `load_backbone` raises `ModelNotInstalledError` for an
  uninstalled model, exactly as `load_detector` does. A multi-GB fetch is the Admin
  tab's job.
- **A detector is not a backbone.** `load_backbone("grounding-dino-tiny")` raises
  `ValueError`; the registry `kind` is checked, mirroring `_require_spec`.
- **Prefix tokens are read, never assumed.** DINOv3 adds register tokens, so the patch
  tokens do not start at index 1. Slicing at a hardcoded `1` silently misaligns the grid
  by the number of registers and yields features that train to garbage.
- **The grid is validated, not trusted.** After slicing, `N_patches` must equal
  `Gh * Gw` computed from the input resolution. A mismatch raises `FeatureShapeError`
  with both numbers — this is the loud failure that catches a wrong
  `num_prefix_tokens` or a non-divisible input size.
- **Input must divide by the patch size.** A 225 px image on a patch-14 backbone
  silently drops a row of pixels in some implementations; reject it here instead.
- **Frozen means frozen.** Any code path that returns a backbone must have run
  `requires_grad_(False)`; feature 5 (`training-job-runner`) builds its optimizer from
  head parameters only, and this is the second line of defence.

## Data Flow

Greenfield for the tensor path. The install-state half reuses Wave 1:
`registry.get_model` → `paths.resolve_model_dir` → `paths.is_installed`, the same chain
`02-model-manager` uses for the Admin tab, so "installed" means the identical thing in
both tabs.

## Dependencies

- `01-app-shell` — FastAPI app, `/api/v1` router, global exception handler
- `02-model-manager` — model catalogue, cache paths, install detection, download

## Security

Accepts no user-supplied paths or repo ids. `model_id` is a registry key looked up via
`get_model`; the cache path comes from `resolve_model_dir`, which confines. Image input
arrives as already-decoded `PIL.Image` objects from callers that did their own
validation (`04-grounding-dino-annotator` established that boundary).

Weights are loaded from the local cache only — no network access in this module.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
