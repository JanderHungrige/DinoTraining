---
id: dinotraining-wave-6
title: "Wave 6: Foundation Model Breadth (Depth Anything 3)"
initiative: dinotraining
initiative_version: 7
status: planned
depends_on: dinotraining-wave-5
demo_state: "The user downloads Depth Anything 3 from the admin panel and runs it in the Inference Viewer beside the DINOv2 heads, comparing a foundation depth model against a trained one on the same image — with every catalogue entry stating its licence."
created: 2026-08-19
hash: 04cd602e
---

# Wave 6: Foundation Model Breadth (Depth Anything 3)

## Demo-State

The admin panel offers **Depth Anything 3** (small by default) alongside the DINOv2
backbones and the head catalogue, with its size and **licence** stated before download. In
the **Inference Viewer** the user runs it beside a trained depth head and compares them
N-up, using the comparison mechanism Wave 3 already built.
*(Not complete until this can be manually demonstrated.)*

## Why the Inference Viewer first

Because it needs **no new labelling tools**. A depth map can be looked at; it cannot yet be
*corrected* in this app, and building a depth-annotation surface to justify a depth model
would be the tail wagging the dog. SAM 3 arrives in Wave 4 for the Dataset Generator, where
mask review is the point; Depth Anything 3 arrives here, where looking is the point.

Adding it to the Annotation Studio is deliberately **not** in this wave — see Open Research.

## Model — confirmed to exist, 2026-08-19

| Model | Repos | Licence |
|---|---|---|
| Depth Anything 3 | `depth-anything/DA3-SMALL`, `DA3-BASE`, `DA3-LARGE` | ⚠️ **verify per variant** — the nested giant/large is **CC BY-NC 4.0, non-commercial** |

DA3 predicts spatially consistent geometry from one or more views using a plain transformer
backbone, and reports large gains over prior state of the art. **Small is the default
download**, per the standing rule that the app never bundles weights and never assumes a
big machine.

**The licence is a Wave 8 problem, decided here.** This app is meant to be installable and
shareable. A CC BY-NC variant cannot ship inside something distributed commercially. Weights
download on demand rather than being bundled, which softens it — but the catalogue entry
must carry the licence and the admin panel must show it, and that work belongs in this wave
rather than being discovered during packaging.

## Features (draft — refined in plan-wave)

| # | Feature | Depends on |
|---|---------|------------|
| 1 | depth-anything-backbone | — |
| 2 | model-licence-surfacing | — |
| 3 | foundation-model-in-viewer | depth-anything-backbone |

- **depth-anything-backbone** — DA3 as an installable entry in the model catalogue, using
  doc 02's download/verify path and doc 15's digest-pinning. It is a *depth estimator*, not
  a backbone-plus-head, so it does not fit the head-instance model cleanly; deciding how it
  enters the registry is the wave's main design question.
- **model-licence-surfacing** — every catalogue entry states its licence, and the admin
  panel shows it before download. Retro-fits the existing entries too.
- **foundation-model-in-viewer** — DA3 appears in the Inference Viewer's picker and renders
  through the existing `depth-map` render hint. If it needs a *new* hint, that is the
  registry working as designed: add the entry, add the renderer, touch nothing else.

## Open Research

- **How a foundation model joins a registry built around backbone + head.** DA3 is one
  model producing depth directly. It may want a third registry, or a head-type whose
  "backbone" is itself. Getting this wrong makes every later foundation model awkward.
- **SAM 3 in the Annotation Studio.** Wave 4 brings SAM 3 for the Dataset Generator. Using
  it in the Studio needs a mask-drawing/refining tool that does not exist — the same gap
  Wave 5 hits for segmentation heads. Candidate for this wave or a later one; not assumed.
- **Whether DA3's multi-view capability is reachable** from a single-image viewer, or
  whether this app only ever uses its monocular path.

## Explicitly not in scope

- **SigLIP 2** — dropped 2026-08-19. It is an image–text embedding model: it scores how
  well an image matches text and does **not** localise, so it produces no boxes and is not
  a Grounding DINO alternative.
- **Gemini Flash Vision** — dropped 2026-08-19. API-only, no local weights, and it would
  send the user's own image folders off their machine, contradicting the premise the app is
  built on. If a cloud VLM is ever wanted it belongs in Wave 9, where the user has already
  accepted cloud compute, clearly labelled and never a default.
