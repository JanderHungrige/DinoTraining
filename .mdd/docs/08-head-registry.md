---
id: 08-head-registry
title: Head Registry — The Head-Type Contract Everything Dispatches Off
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-2
wave_status: active
depends_on: [07-backbone-feature-extractor]
relates: []
source_files:
  - backend/app/ml/heads/__init__.py
  - backend/app/ml/heads/registry.py
  - backend/app/api/v1/head_types.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/heads.ts
routes:
  - GET /api/v1/head-types
test_files:
  - backend/tests/test_head_registry.py
  - backend/tests/test_head_types_api.py
data_flow: greenfield
last_synced: 2026-08-17
status: complete
phase: all
mdd_version: 11
tags: [head-registry, extensibility, task-contract, metrics, render-hint, compatibility]
path: Training/Heads
integration_contracts:
  - function: get_head_type(head_type_id)
    when: anywhere a head's task, metrics, losses or rendering must be known
    why: the alternative is an if/elif on task that must be edited in five places to add a head type
  - function: check_compatibility(spec, capabilities)
    when: before offering any head for training, download or import
    why: incompatibility must be explained to the user, not silently greyed out
satisfies_contracts:
  - from: 07-backbone-feature-extractor
    function: read_capabilities(model_id)
    when: compatibility is checked against a backbone
    status: done
    verified_at: "backend/app/api/v1/head_types.py:86"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 08 — Head Registry

## Purpose

Defines what a *head type* is, so that adding one is a registry entry rather than an
edit to the training loop, the metrics stream, the checkpoint format, the inference
viewer and the generator. This is the central abstraction of Wave 2 — features 3 to 9
all dispatch off it.

## Architecture

The registry is **pure metadata and imports no torch.** The API layer, the compatibility
check and (later) the head-catalog import all need to reason about head types without
paying a multi-second torch import or loading a model. Feature 3
(`09-head-implementations`) supplies the actual `nn.Module` builders, keyed by head-type
id, in a separate module.

```
registry.py   (no torch)  head type metadata + compatibility
     │
     ├── api/v1/head_types.py     what the trainer UI lists
     ├── 09-head-implementations  builders keyed by id
     ├── 11-training-job-runner   loss + metric set + best-model criterion
     └── 12-head-instance-registry  task + render hint recorded on every instance
```

## Data Model

### `HeadTypeSpec` (frozen dataclass)

| Field | Type | Why it exists |
|---|---|---|
| `id` | `str` | Stable key, e.g. `dense-detector` |
| `task` | `HeadTask` | `classification` / `detection` / `segmentation` / `depth` |
| `title` | `str` | Shown in the trainer UI |
| `description` | `str` | One line of guidance for the user |
| `trainable` | `bool` | Whether *this app* can fine-tune it |
| `target_format` | `TargetFormat \| None` | What labels it trains against; `None` when not trainable |
| `consumes` | `FeatureUse` | `cls` or `patch-grid` — which part of `BackboneFeatures` |
| `geometry` | `PreprocessGeometry` | `center-crop` or `aspect-preserve` |
| `metrics` | `tuple[str, ...]` | Declared here so the metrics stream never hardcodes names |
| `primary_metric` | `str \| None` | Best-model selection criterion; `None` when not trainable |
| `primary_metric_mode` | `"max" \| "min" \| None` | Whether higher or lower wins |
| `render_hint` | `RenderHint` | How Waves 3/4 draw the output |
| `compatible_families` | `frozenset[ModelFamily]` | Backbone families this head supports |

**`geometry` is the direct consequence of what feature 7 found.** The stock DINOv2
processor centre-crops to 224, which is correct for classification and silently drops
annotations for dense tasks. Rather than leaving that as prose, each head type *declares*
the geometry it requires and `10-preprocessing-pipeline` obeys it.

### Invariants (enforced in `__post_init__`, not merely documented)

- `trainable=True` ⟹ `target_format`, `primary_metric` and `primary_metric_mode` are all set.
  A trainable head with no best-model criterion means save-best-only silently saves the last
  epoch.
- `trainable=False` ⟹ all three are `None`. Depth is the deliberate case: the registry must
  not assume a training loop exists for every head type.
- `primary_metric` must appear in `metrics`. Selecting on a metric that is never computed
  is a silent no-op.
- `metrics` must be non-empty when trainable.

### Built-in head types

| id | task | trainable | consumes | geometry | primary metric |
|---|---|---|---|---|---|
| `linear-classifier` | classification | ✅ | `cls` | center-crop | `accuracy` (max) |
| `dense-detector` | detection | ✅ | patch-grid | aspect-preserve | `map` (max) |
| `linear-segmenter` | segmentation | ✅ | patch-grid | aspect-preserve | `miou` (max) |
| `linear-depth` | depth | ❌ | patch-grid | aspect-preserve | — |

## API Endpoints

### `GET /api/v1/head-types?backbone=<model_id>`

Lists head types. When `backbone` is supplied, each entry also carries a compatibility
verdict *with a reason* — the wave requires explaining why a head does not fit rather
than greying it out.

```json
{
  "head_types": [
    {
      "id": "dense-detector", "task": "detection", "title": "…",
      "trainable": true, "target_format": "boxes",
      "metrics": ["map", "map_50"], "primary_metric": "map",
      "render_hint": "boxes",
      "compatible": true, "incompatible_reason": null
    }
  ]
}
```

Errors: `404` for an unknown `backbone`; `409` when the named backbone is not installed
(its capabilities cannot be read, so no verdict is possible).

## Business Rules

- **Adding a head type must not touch the training loop.** Anything a consumer needs to
  branch on lives in the spec.
- **Compatibility is explained.** `check_compatibility` returns a reason string on failure,
  never a bare boolean.
- **Type-level vs instance-level compatibility.** A head *type* is compatible with a
  backbone family; a specific *weights instance* additionally has to match `embed_dim`.
  A linear head is constructed to whatever `embed_dim` the backbone reports, so
  `embed_dim` is not a type-level constraint — it is checked in `15-head-catalog-import`
  when importing pretrained weights, whose shapes are already fixed.
- **The registry is immutable at runtime.** `HEAD_TYPES` is a frozen mapping and each spec
  is a frozen dataclass; nothing mutates it after import.

## Data Flow

Greenfield. Reads `BackboneCapabilities` from `07-backbone-feature-extractor` for the
compatibility verdict; produces metadata consumed by features 3, 4, 5, 7, 8, 9 and
Waves 3–4.

## Dependencies

- `07-backbone-feature-extractor` — `BackboneCapabilities`, `read_capabilities`

## Security

No user-supplied paths, no network, no filesystem writes. `head_type_id` and `backbone`
arrive from the API as opaque strings and are resolved by dictionary lookup against a
fixed table — an unknown key is a 404, never a lookup that touches disk.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
