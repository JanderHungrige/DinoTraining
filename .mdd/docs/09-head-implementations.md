---
id: 09-head-implementations
title: Head Implementations — The Four Built-In Heads
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-2
wave_status: active
depends_on: [07-backbone-feature-extractor, 08-head-registry]
relates: []
source_files:
  - backend/app/ml/heads/modules.py
  - backend/app/ml/heads/builders.py
test_files:
  - backend/tests/test_head_modules.py
  - backend/tests/test_head_builders.py
routes: []
models: []
data_flow: greenfield
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [heads, linear-probe, anchor-free-detection, segmentation, depth, torch-modules]
path: Training/Heads
integration_contracts:
  - function: build_head(head_type_id, capabilities, num_classes)
    when: the trainer or the inference engine needs a head module
    why: constructing nn.Module subclasses directly bypasses the width/class validation
  - function: decode_ltrb_to_boxes(box_ltrb, grid, patch_size)
    when: turning detector output into boxes, anywhere
    why: the ltrb-to-xywh conversion must happen exactly once, as with Wave 1's detector
satisfies_contracts:
  - from: 08-head-registry
    function: get_head_type(head_type_id)
    when: building any head — the spec drives width, class count and feature use
    status: done
    verified_at: "backend/app/ml/heads/builders.py:74"
  - from: 07-backbone-feature-extractor
    function: extract(backbone, pixel_values)
    when: every head's forward consumes BackboneFeatures
    status: done
    verified_at: "backend/app/ml/heads/modules.py:27"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 09 — Head Implementations

## Purpose

The four built-in heads as `nn.Module`s, plus the builder registry that maps a
head-type id to its constructor. This is the first real test of `08-head-registry`:
if any head needs something the spec cannot express, the contract is wrong.

## Architecture

**Every head has the same call signature.** That is the whole point:

```python
head(features: BackboneFeatures) -> dict[str, Tensor]
```

A uniform `dict[str, Tensor]` output rather than four bespoke return types is what
lets `11-training-job-runner` stay generic — it never branches on task. Each head
reads `cls` or `patches` according to its spec's `consumes`, so the dispatch that
would otherwise live in the trainer lives in the head.

| Head | Output keys | Shapes |
|---|---|---|
| `linear-classifier` | `logits` | `(B, C)` |
| `dense-detector` | `class_logits`, `box_ltrb`, `centerness` | `(B,C,Gh,Gw)`, `(B,4,Gh,Gw)`, `(B,1,Gh,Gw)` |
| `linear-segmenter` | `logits` | `(B, C, Gh, Gw)` |
| `linear-depth` | `depth` | `(B, 1, Gh, Gw)` |

Heads output at **patch resolution**. Upsampling to image resolution needs the target
size, which the head does not know — `upsample_logits` is provided for the loss and
the renderer to call with an explicit size.

### Detection geometry

Anchor-free, FCOS-style: each patch cell predicts class logits, four **ltrb distances**
to the box edges, and a centerness score. Distances pass through `softplus` and are
scaled by `patch_size`, so they are positive and in pixels — a raw linear output would
let the model predict negative extents and produce inverted boxes.

`decode_ltrb_to_boxes` converts to the store's xywh convention. As in Wave 1's
detector, that conversion exists in exactly one place so nothing downstream has to
guess which convention it is holding.

## Data Model

`HeadBuildConfig`: `num_classes: int | None`. Required and `>= 1` for trainable heads;
must be `None` for `linear-depth`, which has no classes.

## Business Rules

- **Heads are trainable; backbones are not.** Every head parameter has
  `requires_grad=True` on construction. `07` freezes the backbone; this is the other
  half of that pairing, and both are asserted in tests.
- **Width comes from the backbone, never a constant.** Each head is constructed against
  `capabilities.embed_dim`, which is why `embed_dim` is not a type-level compatibility
  constraint in `08`.
- **The builder table must cover every registry spec.** A spec with no builder is a
  runtime failure the moment a user selects it; a test asserts the two stay in sync.
- **`linear-depth` is buildable but not trainable.** It must construct for inference —
  "not trainable" is about *this app fine-tuning it*, not about whether the module
  exists.

## Data Flow

Greenfield. Consumes `BackboneFeatures` from `07`, and `HeadTypeSpec` from `08` for
width, class count and feature use.

## Dependencies

- `07-backbone-feature-extractor` — `BackboneFeatures`, `BackboneCapabilities`
- `08-head-registry` — `HeadTypeSpec`, `get_head_type`

## Security

Pure tensor code. No user paths, no network, no deserialization of untrusted data —
loading third-party weights into these modules is `15-head-catalog-import`'s boundary.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
