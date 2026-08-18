---
id: dinotraining-wave-3
title: "Wave 3: Inference Viewer"
initiative: dinotraining
initiative_version: 5
status: planned
depends_on: dinotraining-wave-2
demo_state: "User loads an image or webcam/video, selects a backbone + one or more head instances (default, community or self-trained), and sees original vs. annotated results side-by-side in real time — including comparing several heads on the same task."
created: 2026-08-14
hash: 4d171514
---

# Wave 3: Inference Viewer

## Demo-State

In the **Inference Viewer** tab the user picks a DINO backbone + one or more heads (any
instance from the Wave 2 head-instance registry — pretrained default, community import, or
one they trained) and an input source: a single image, an image folder, or a live
webcam/video stream. The original and the annotated result (labels, boxes, masks, depth, or
whatever the head produces) are shown side-by-side, updating in real time for streams. Several
heads on the *same* task can be run against one input and compared.
*(Not complete until this can be manually demonstrated.)*

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | inference-engine | — | planned | — |
| 2 | multi-head-compose | — | planned | inference-engine |
| 3 | video-stream-source | — | planned | — |
| 4 | side-by-side-viewer | — | planned | — |
| 5 | inference-overlay-render | — | planned | side-by-side-viewer |
| 6 | same-task-head-compare | — | planned | multi-head-compose, side-by-side-viewer |

### Feature notes

- Inference engine reuses the frozen backbone + selected head(s); batched image + realtime
  video paths.
- Compose multiple heads (e.g. several expert detectors) over one backbone pass.
- Video/webcam capture with a target FPS and frame-drop handling.
- Side-by-side original vs. result, overlay renderer shared with the annotation canvas.
- **Head selection consumes the Wave 2 head-instance descriptor**: heads are listed by task,
  provenance kind (`pretrained-default` / `community` / `trained-here`), training datasets,
  class list and metrics — never by bare filename. The overlay renderer dispatches off the
  head's registry render hint (boxes / labels / masks / depth map / …), so a head type added
  to the registry later renders here without changing this wave's code.
- **same-task-head-compare:** run several instances of the *same* task over one input and show
  them against each other — e.g. the pretrained default segmentation head vs. a fine-tuned
  one, or two community detectors. This is the payoff of the instance model: it is just the
  instance list filtered by task, not a separate mechanism.
- Depth and segmentation are demonstrable here **with no training at all**, using the Wave 2
  default heads. Worth using as the wave's smoke test — it exercises the full backbone → head
  → render path without depending on the trainer.

## Open Research

- Realtime throughput on MPS/CPU; whether to downscale or run every Nth frame.
- Backbone feature caching so multiple heads share one forward pass.
