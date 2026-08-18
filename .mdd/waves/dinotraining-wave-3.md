---
id: dinotraining-wave-3
title: "Wave 3: Inference Viewer"
initiative: dinotraining
initiative_version: 6
status: planned
depends_on: dinotraining-wave-2
demo_state: "User loads a single image or a folder, selects a backbone plus one or more head instances (default, community or self-trained), and sees original vs. annotated results side-by-side — including several heads on the same task compared against one input. Still images only; live video is deferred."
created: 2026-08-14
hash: 309fcf80
---

# Wave 3: Inference Viewer

## Demo-State

In the **Inference Viewer** tab the user picks a DINO backbone and one or more heads — any
instance from the Wave 2 head-instance registry, whether a pretrained default, a community
import, or one they trained — and an input source: a single image or an image folder. The
original and the annotated result (labels, boxes, masks or depth, whichever the head
produces) are shown side-by-side. Several heads on the **same task** can be run over one
input and compared against each other.

**Still images only.** Live webcam/video is deliberately out of scope — see the deferral
note below.
*(Not complete until this can be manually demonstrated.)*

## Planning decisions (2026-08-18)

- **Live video/webcam deferred out of this wave.** Capture permissions in Tauri, frame
  pacing and drop handling are the largest and least-certain chunk of the original draft,
  and none of it is needed to prove the wave's real payoff — the backbone → head → render
  path and same-task comparison. Its natural home is **Wave 4**, where the Dataset
  Generator already ingests new imagery and video frames are simply another source; that
  placement is a proposal, to be confirmed when Wave 4 is planned.
- **`video-stream-source` is replaced by `image-input-source`**, not simply removed. The
  wave still needs an input-source feature; it just loads files rather than frames.
- **Open Product Questions gate waived.** Two questions remain unchecked in the initiative
  — code-signing/notarization (Wave 5) and first hyperscaler (Wave 6). Both are explicitly
  scoped to later waves and cannot influence an inference viewer's architecture. Waived
  deliberately on 2026-08-18 rather than skipped; recorded here so the next `plan-wave`
  does not rediscover it as an open question.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | inference-engine | [16](../docs/16-inference-engine.md) | complete | — |
| 2 | image-input-source | — | planned | — |
| 3 | multi-head-compose | — | planned | inference-engine |
| 4 | side-by-side-viewer | — | planned | — |
| 5 | inference-overlay-render | — | planned | side-by-side-viewer |
| 6 | same-task-head-compare | — | planned | multi-head-compose, inference-overlay-render |

### Feature notes

- **inference-engine** — loads a frozen backbone plus a head instance and runs a forward
  pass over one or more images. It must reuse `07-backbone-feature-extractor`'s `extract`
  rather than reimplementing the token split; the register-token bug that function guards
  against is exactly the kind of thing a second implementation reintroduces. Heads are
  constructed through `build_head` (doc 09) and loaded from `HeadInstanceStore.load_weights`
  (doc 12) — never by reading a weights path directly.
  - The head must be moved to the backbone's device by the caller (`runner.py:135` sets the
    precedent). Found during Wave 2 verification: a head built on CPU against an MPS
    backbone raises at the first matmul.
- **image-input-source** — a single image or a folder, reusing Wave 1's folder-picker and
  image-listing rather than a second implementation. Establishes the input contract that
  a future video source can satisfy without the viewer changing.
- **multi-head-compose** — run N heads over **one** backbone forward pass. This is the
  feature that makes comparison cheap, and it is the reason the engine and the compose
  step are separate: the engine owns "features from an image", compose owns "many heads
  from one set of features". The backbone-feature-cache research below lands here.
- **side-by-side-viewer** — original vs. result panes, synchronised zoom/pan. Layout only;
  it must not know what a head produces.
- **inference-overlay-render** — draws a head's output, **dispatching off the head type's
  `render_hint`** (`labels` / `boxes` / `masks` / `depth-map`) from doc 08. Adding a head
  type to the registry later must render here without touching this wave's code — the same
  registry-not-enum discipline the whole of Wave 2 was built on. The box path shares
  geometry with `05-annotation-canvas`; `decode_ltrb_to_boxes` (doc 09) is the single
  ltrb→xywh conversion and must not be duplicated.
- **same-task-head-compare** — the payoff of the instance model. It is
  `list_all(task=…)` filtered, rendered N-up; not a separate mechanism. Heads are presented
  via `HeadInstance.summary` — task, provenance, training data, metrics — **never a
  filename**. That is doc 12's cross-tab contract and Wave 2 already had one bug from
  breaking it.

### Smoke test for the wave

The three Wave 2 default heads (classification, segmentation, depth on `dinov2-small`) are
already installed and require no training. They exercise the full backbone → head → render
path — including two dense render hints — without depending on the trainer at all, so they
are the fastest end-to-end check that this wave works.

## Open Research

- **Backbone feature caching across heads.** One forward pass feeding N heads is the point
  of `multi-head-compose`. The cache key is:

  ```
  (backbone_id, geometry, size)
  ```

  Nothing else. In particular **`consumes` is not part of the key** — `cls` and `patches`
  both come out of the same `BackboneFeatures`, so a `cls`-reading head shares a pass with
  a `patch-grid`-reading one whenever the framing matches. Today's seven head types
  therefore collapse to just **two passes**, not one per task:

  | Pass | Head types | Tasks |
  |---|---|---|
  | `aspect-preserve` @ 448 (32x32 grid) | 5 | detection, segmentation, depth |
  | `center-crop` @ 224 (16x16 grid) | 2 | classification |

  **What you cannot do is synthesise one pass from another** — e.g. serve the 224
  center-crop head by slicing the middle 16x16 out of the 448 letterboxed grid. Two
  reasons: the CLS token is produced by attention over *every* patch in that pass, so it
  describes the whole letterboxed frame (padding included) and no amount of slicing
  changes it; and a 14px patch at 448 covers half the real-world extent it does at 224,
  with interpolated position embeddings to match, so even the patch tokens differ. Run the
  two passes; do not try to derive one from the other.

  Open question is therefore only *where* the cache lives and when it is invalidated, not
  what keys it.
- **Throughput on MPS/CPU for folder runs.** Batch size and whether to show results
  progressively as they complete rather than after the whole folder.
- **Depth and segmentation rendering.** Colour-mapping depth to something readable, and
  mask opacity/palette for 150 ADE20k classes — the default heads produce both, so this is
  immediately real rather than hypothetical.
- **Install/remove affordance for heads** (carried from doc 15 `known_issues`): heads are
  installed in the Admin tab but removed in the Head Trainer tab, while backbones do both
  on one card. This wave adds the third consumer of the head list, which is when the
  affordance should be settled.
