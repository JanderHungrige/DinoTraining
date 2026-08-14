---
id: dinotraining-wave-3
title: "Wave 3: Inference Viewer"
initiative: dinotraining
initiative_version: 1
status: planned
depends_on: dinotraining-wave-2
demo_state: "User loads an image or webcam/video, selects a backbone + trained head(s), and sees original vs. annotated results side-by-side in real time."
created: 2026-08-14
hash: 7e6b76de
---

# Wave 3: Inference Viewer

## Demo-State

In the **Inference Viewer** tab the user picks a DINO backbone + one or more trained heads
(from the Wave 2 checkpoint registry) and an input source: a single image, an image folder,
or a live webcam/video stream. The original and the annotated result (labels, boxes, or
whatever the head produces) are shown side-by-side, updating in real time for streams.
*(Not complete until this can be manually demonstrated.)*

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | inference-engine | — | planned | — |
| 2 | multi-head-compose | — | planned | inference-engine |
| 3 | video-stream-source | — | planned | — |
| 4 | side-by-side-viewer | — | planned | — |
| 5 | inference-overlay-render | — | planned | side-by-side-viewer |

### Feature notes

- Inference engine reuses the frozen backbone + selected head(s); batched image + realtime
  video paths.
- Compose multiple heads (e.g. several expert detectors) over one backbone pass.
- Video/webcam capture with a target FPS and frame-drop handling.
- Side-by-side original vs. result, overlay renderer shared with the annotation canvas.

## Open Research

- Realtime throughput on MPS/CPU; whether to downscale or run every Nth frame.
- Backbone feature caching so multiple heads share one forward pass.
