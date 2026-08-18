---
id: 18-multi-head-compose
title: Multi-Head Compose — N Heads, One Backbone Pass Per Framing
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-3
wave_status: complete
depends_on: [16-inference-engine]
relates: [07-backbone-feature-extractor, 10-preprocessing-pipeline, 21-same-task-head-compare]
source_files:
  - backend/app/ml/inference/compose.py
  - backend/app/ml/inference/engine.py
  - backend/app/api/v1/inference.py
routes:
  - POST /api/v1/inference/compose
models: []
test_files:
  - backend/tests/test_inference_compose.py
  - backend/tests/test_inference_compose_api.py
  - backend/tests/test_inference_api.py
  - backend/tests/test_inference_source_api.py
  - backend/tests/inference_api_testkit.py
data_flow: .mdd/audits/flow-multi-head-compose-2026-08-18.md
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [inference, feature-cache, backbone-pass, head-composition, preprocessing-geometry, comparison]
path: Inference/Compose
integration_contracts:
  - function: run_heads(image, backbone_id, instance_ids)
    when: any surface that runs more than one head over the same image
    why: running heads one at a time repeats a backbone pass that is provably identical,
      and the grouping rule is not obvious enough to re-derive per caller
satisfies_contracts:
  - from: 16-inference-engine
    function: run_inference(image, backbone_id, instance_id)
    when: a single head is run over an image
    status: done
    verified_at: "backend/app/ml/inference/engine.py:157"
    note: >-
      Satisfied by taking the implementation over rather than by calling it: run_inference
      now delegates to run_heads with a one-element list, so the doc-16 entry point and its
      five status codes are unchanged while there is only one copy of the sequence.
      test_inference_engine.py passes unmodified apart from its patch target, which is the
      regression check for the refactor.
security_read_sites: []
known_issues:
  - "The saving is bounded by response serialisation, not by the passes. Measured on the 900x300 panorama with the three default heads: 2 passes instead of 3, ~0.43 s composed against ~0.66 s for three separate calls — but the response is 5.5 MB, almost all of it the mask and depth grids doc 16 flagged. Sharing passes cannot improve that; RLE or a PNG response is the lever, and it belongs to 20-inference-overlay-render."
  - "No cross-call cache: adding a fourth head to an image already run re-runs its pass. Deliberate — see 'Where the cache lives'. It goes behind the same key with doc 17's `item_id` plus an mtime if a consumer ever needs it, and would show up as `passes: 0`."
  - "`engine.py` is 262 lines with `_build_payload` and its four helpers still in it. The next change to payload shaping (likely 20-inference-overlay-render) should split `payloads.py` out rather than push this file past the 300-line gate."
sister_projects: []
---

# 18 — Multi-Head Compose

## Purpose

Run **N head instances over one image with the minimum number of backbone forward
passes**. This is what makes comparison cheap, and it is why the engine and the compose
step are separate features: the engine owns *features from an image*, compose owns *many
heads from one set of features*.

It is also where the wave's Open Research on backbone-feature caching lands. That question
is answered below.

## Architecture

```
image + backbone_id + [instance_id, …]
        │
        │ 1. resolve every head first — one bad id fails before any compute
        │
        │ 2. group by pass key:  (backbone_id, geometry, size)
        │        aspect-preserve @ 448  →  [segmenter, depth]
        │        center-crop     @ 224  →  [classifier]
        │
        │ 3. per group: prepare_images once → extract once → BackboneFeatures
        │
        │ 4. per head in group: forward → decode_for → invert → Prediction
        │
        ▼
ComposedResult { predictions (in the caller's order), passes, elapsed_ms }
```

Today's seven head types collapse to **two passes, not seven** — and three heads over the
three installed defaults run in two passes, which is the feature's whole claim.

## The cache key — and what it deliberately excludes

```
(backbone_id, geometry, size)
```

**`consumes` is not part of the key.** `cls` and `patches` come out of the same
`BackboneFeatures`, so a `cls`-reading head shares a pass with a `patch-grid`-reading one
whenever the framing matches. Including `consumes` would double the passes for no reason.

**One pass cannot be synthesised from another.** The tempting shortcut — serve the 224
centre-crop head by slicing the middle 16×16 out of the 448 letterboxed grid — is wrong
twice over:

- the CLS token is attention over *every* patch in that pass, so it describes the whole
  letterboxed frame, padding included; no slicing changes it;
- a 14 px patch at 448 covers half the real-world extent it does at 224, with interpolated
  position embeddings to match, so the patch tokens differ too.

Run both passes. The saving comes from heads that *share* a framing, not from deriving one
framing from another.

### Where the cache lives, and when it is invalidated

**It lives in the compose call, and it dies with it.** That is the scope over which the
features are provably valid: one image, one backbone, no opportunity for anything to change
underneath them. Nothing is invalidated because nothing outlives the call.

A cross-call cache — "the user added a fourth head to the same image, reuse the passes" —
is deliberately **not** built here, because it cannot be built without answering an
invalidation question no consumer has yet posed: the file on disk can change between calls,
so the key would need a content or mtime component, and the memory ceiling would need an
eviction policy. `load_backbone` already caches the expensive part (the model itself) across
calls, so what a cross-call cache would save is one forward pass, not a model load.

If it is later wanted, it goes behind this same key with `item_id` (doc 17) and an mtime
added, and no caller changes. That is the reason `run_heads` returns `passes` — a
cross-call cache would show up as `passes: 0` without any contract moving.

## API Endpoints

### `POST /api/v1/inference/compose`

JSON: `{ image_path, backbone_id, instance_ids: [str], score_threshold? }`

```json
{
  "predictions": [ /* PredictionResponse, one per head, in request order */ ],
  "passes": 2,
  "elapsed_ms": 812.4
}
```

| Status | When |
|---|---|
| `200` | predictions returned |
| `404` | unknown head instance, or no such file |
| `409` | backbone not installed, or a head registered for a different backbone |
| `415` | the path is not a readable image |
| `422` | empty `instance_ids`, or a threshold outside 0..1 |

`POST /api/v1/inference` (doc 16) is unchanged and now **delegates to this path** with a
single-element list, so there is one implementation of head-running rather than two that
drift.

## Business Rules

- **Every head is resolved before any compute.** One unknown id fails the request before a
  backbone pass has been paid for. Resolving lazily would mean the user waits for a 448 pass
  to learn they mistyped an id.
- **A mismatched backbone fails the whole request, not just that head.** Partial success
  would be a second response shape for every consumer to handle, and the viewer only offers
  heads registered for the selected backbone — a mismatch is a bug in the caller, not a
  routine outcome. The message names the offending head and the backbone that would work.
- **Predictions come back in the caller's order.** Grouping by pass key reorders the work;
  it must not reorder the result. A viewer rendering "head 1, head 2, head 3" in columns
  would otherwise silently mislabel every column.
- **Duplicate instance ids are collapsed**, first occurrence winning. Two identical
  predictions carry no information, and the request is still coherent.
- **`passes` is reported, not inferred.** It is the only externally visible proof the
  feature does what it claims, and it is what a future cross-call cache would move.
- **Per-head `elapsed_ms` excludes the shared pass.** See below.

### What changes in feature 16

`Prediction.elapsed_ms` was the whole call: preprocess + backbone + head + decode. Under
composition that number would double-count the shared pass across every head in a group and
imply the heads cost more than they do.

It now measures **the head's own work** — forward, decode, geometry inversion — while
`ComposedResult.elapsed_ms` is the wall clock for everything. The per-head figures therefore
sum to *less* than the total, and the difference is the shared backbone pass. That gap is
the feature's payoff made visible rather than an inconsistency.

## Data Flow

See `.mdd/audits/flow-multi-head-compose-2026-08-18.md`.

## Dependencies

`16-inference-engine` — this feature generalises it and takes over its implementation.
`10-preprocessing-pipeline` supplies the plan whose `geometry` and `size` *are* the cache
key; `07-backbone-feature-extractor` supplies the single `extract` both passes go through.

## Security

No new input surface. `image_path` is read exactly as doc 16 reads it, and `instance_ids`
are registry lookup keys, never path components. The one new consideration is that a list
lets a caller ask for many heads at once: heads are deduplicated and every id must resolve
before compute starts, so a long list of repeated or invalid ids cannot be used to make the
backend do arbitrary work.

## Verified

Against real weights on the 900×300 panorama, with the three installed default heads
(classification, segmentation, depth on `dinov2-small`):

```
passes      : 2                     ← three heads, two framings
grids       : [16,16] and [32,32]   ← center-crop @224 and aspect-preserve @448
order       : classification, segmentation, depth — as requested
sum head ms : 653          total ms : 2964   (cold; the gap is the two passes + model load)
warm        : ~0.43 s composed  vs  ~0.66 s as three separate calls
```

Error paths confirmed against the running backend: 404 naming *only* the unknown id, 409
naming the backbone that would work, 422 for an empty list, and duplicate ids collapsing to
one prediction.

## Known Issues

- **The saving is bounded by serialisation, not by the passes.** The composed response for
  those three heads is **5.5 MB**, almost all of it the mask and depth grids doc 16 flagged.
  Sharing passes cannot improve that. RLE or a PNG response is the lever, and it belongs to
  `20-inference-overlay-render`.
- **No cross-call cache** — adding a fourth head to an image already run re-runs its pass.
  Deliberate; see "Where the cache lives". It would go behind the same key with doc 17's
  `item_id` plus an mtime, and would surface as `passes: 0`.
- **`engine.py` is 262 lines** with `_build_payload` and its four helpers still in it. The
  next change to payload shaping should split out `payloads.py` rather than push this file
  past the 300-line gate.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
