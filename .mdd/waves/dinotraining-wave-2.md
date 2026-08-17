---
id: dinotraining-wave-2
title: "Wave 2: Head Trainer"
initiative: dinotraining
initiative_version: 5
status: in_progress
depends_on: dinotraining-wave-1
demo_state: "User selects datasets, a head type (classification / detection / segmentation, plus any default or community head compatible with their backbone) and a training config with good defaults, starts training on the local device against a frozen backbone, watches live loss/metrics, and gets a saved head instance recording what task and datasets it was trained on. Pretrained default heads for classification, segmentation and depth are downloadable and usable without any training."
created: 2026-08-14
hash: e3edfe03
---

# Wave 2: Head Trainer

## Demo-State

In the **Head Trainer** tab the user selects one or more datasets built in Wave 1, chooses
a head type — **classification, object detection or segmentation** built in, plus any
**default or community head** compatible with their backbone — and a training
setup with sensible defaults (save-best-only, train/val/test split, epochs, batch size, lr,
early stopping). Preprocessing is chosen internally from the backbone + head. The backbone
stays frozen; only the head trains. Training runs on the local device via a pluggable job
runner, streaming live loss/metric charts, and produces a saved head instance registered
with full provenance — task, backbone version, datasets, classes and metrics — so Waves 3
and 4 can present it by what it does rather than by filename.

Separately and without any training, the user can download **pretrained default heads** for
classification, segmentation and depth and use them straight away — which is what makes
segmentation and depth useful before the app can train them.
*(Not complete until this can be manually demonstrated.)*

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | backbone-feature-extractor | [07](../docs/07-backbone-feature-extractor.md) | complete | — |
| 2 | head-registry | — | planned | backbone-feature-extractor |
| 3 | head-implementations | — | planned | head-registry |
| 4 | preprocessing-pipeline | — | planned | head-registry |
| 5 | training-job-runner | — | planned | head-implementations, preprocessing-pipeline |
| 6 | head-instance-registry | — | planned | training-job-runner, head-registry |
| 7 | training-metrics-stream | — | planned | training-job-runner |
| 8 | trainer-config-ui | — | planned | head-registry, training-job-runner |
| 9 | head-catalog-import | — | planned | head-registry, head-instance-registry |

### Feature notes

- **Frozen DINOv2/v3 backbone** as a feature extractor; only heads are trained. The
  extractor publishes a *backbone capability descriptor* (model version, patch size, embed
  dim, output stride, available layers) — this is what head compatibility is checked against.
- **head-registry is the central abstraction of this wave.** A head type is a registry entry,
  never an enum branch in the trainer. Each entry declares:
  - `task` (classification / detection / segmentation / depth / …)
  - output tensor schema and the target format it trains against
  - loss function and metric set
  - preprocessing requirements (resize/crop/normalisation, target resampling)
  - backbone compatibility constraints (which versions, patch sizes, embed dims)
  - a render hint so Wave 3/4 know how to draw its output
  Everything downstream — trainer, metrics stream, checkpoint format, inference viewer,
  generator — dispatches off this contract. Adding a head type must never require touching
  the training loop.
- **Usable and trainable are two independent axes.** A head type declares both. *Usable*
  means it can run for inference right now; *trainable* means this app can fine-tune it,
  which requires targets the Annotation Studio can actually produce. Conflating the two is
  what wrongly deferred depth. The registry must not assume a training loop exists for every
  head type — depth is the deliberate proof of that.

| Head type | Usable (inference) | Trainable in-app | Targets come from |
|---|---|---|---|
| classification | ✅ default head | ✅ | Wave 1 labels |
| object detection | train your own | ✅ | Wave 1 boxes |
| segmentation | ✅ default head | ✅ once masks exist | user-brought masks now; SAM in Wave 4 |
| depth | ✅ default head | ❌ for now | — (inference-only) |

- **Head *types* vs head *instances*.** The registry holds types; what the user picks anywhere
  in the app is an *instance*, carrying a provenance `kind`:
  `pretrained-default` | `community` | `trained-here`. One descriptor, one picker contract,
  every tab. "Compare several heads on the same task" is then just listing instances filtered
  by task — no separate mechanism.
- Detection uses an **anchor-free dense head** (FCOS/CenterNet-style, per-patch classification
  + box regression on the ViT patch grid, NMS at inference). Segmentation is included
  deliberately as the first *dense per-pixel* task, to prove the registry contract against a
  genuinely different output shape rather than two near-identical box/label tasks.
- **Default heads make segmentation and depth useful before they are trainable.** DINOv2
  publishes linear evaluation heads for classification, segmentation (ADE20k) and depth
  (NYUd) under Apache-2.0, plus a Mask2Former segmentation model. Those are the defaults.
  **Detection has no official DINOv2 head** — which is fine, since detection is the one task
  Wave 1 already produces targets for, so it is train-your-own from the start.
- **head-catalog-import** covers *both* first-party defaults and community heads — one code
  path, since both are "fetch a head, validate it against the backbone, register an instance".
  - **⚠ The official DINOv2 heads are distributed as `.pth` (mmcv/mmsegmentation) — pickles.**
    That collides head-on with the safetensors-only rule. Resolution: the rule governs
    *untrusted user-supplied* imports. First-party defaults live in a **curated catalog with
    pinned SHA-256 digests**, are verified against the digest, and are converted to
    safetensors once on download. The pickle path is never reachable from user input.
  - **Community imports: safetensors from a HuggingFace repo id only. `.pt`/`.pth` refused
    outright**, since `torch.load` on a pickle is arbitrary code execution and this app is
    installed by strangers.
  - Every head requires a manifest declaring backbone version, patch size, embed dim and task,
    validated against the backbone capability descriptor. When incompatible, explain *why*
    rather than just greying it out, and show which of the user's downloaded backbones the
    head would work with.
- **preprocessing-pipeline must be task-aware, and this is not optional.** Found while
  verifying feature 1 against real weights: the stock DINOv2 `AutoImageProcessor` does
  `resize(shortest_edge=256)` + `center_crop(224)`, so a 200×900 image is reduced to its
  middle square. Fine for classification, silently destructive for detection and
  segmentation — annotations outside the crop disappear and training loss still looks
  healthy. Dense tasks need aspect-preserving resize/pad, and **targets must be
  transformed alongside the image**, not independently.
- Training config with good defaults: split method, save-best-only, epochs, lr, batch,
  early stopping, augmentation on/off.
- Job runner interface (local now) designed so a remote/hyperscaler runner drops in later
  (Wave 6).
- Live metrics streamed to the UI (WebSocket/SSE) with loss + the metric set the head's
  registry entry declares (acc / mAP / mIoU / …) — the stream must not hardcode metric names.
- **Head-instance provenance is a hard requirement, not a nice-to-have.** Every registered
  instance records: `kind`, head type/task, backbone version it targets, and — for
  `trained-here` — the datasets and class list used, the training config and its best
  metrics. For `pretrained-default` and `community`, it records the source repo, digest and
  whatever the upstream manifest declares it was trained on (e.g. "ADE20k, 150 classes").
  Waves 3 and 4 present heads by *what they do and what they were trained on* — never by
  filename. This descriptor is the cross-tab contract for the whole rest of the initiative.

## Open Research

- ~~Detection-head design on a frozen backbone~~ → **resolved 2026-08-17: anchor-free dense
  head** (FCOS/CenterNet-style, per-patch classification + box regression on the ViT patch
  grid, NMS at inference). DETR-style set prediction was rejected for slow convergence on
  the small datasets Wave 1 produces.
- Metric set + charts per head type; best-model selection criterion (declared by the head's
  registry entry, not hardcoded in the trainer or the chart component).
- Reproducibility: seeds, config snapshot saved alongside each checkpoint.
- ~~Segmentation targets from Wave 1 data~~ → **resolved 2026-08-17**: segmentation is
  *usable* immediately via the pretrained default head, and *trainable* from a user-brought
  mask dataset. **SAM lands in Wave 4** to generate masks in-app, at which point segmentation
  becomes trainable end-to-end from the Annotation Studio. Same shape for depth: default head
  now, trainable later or never. No box-derived weak masks.
- Exact default-head weights + digests to pin per backbone version (DINOv2 sizes; DINOv3 may
  have no published heads at all — check before promising defaults for it).
- Whether DINOv3 default heads exist under a licence compatible with redistribution, given
  the model itself is gated.
- Which community heads actually exist as safetensors for DINOv2/v3 today — needed to make
  the import guidance concrete rather than theoretical.
