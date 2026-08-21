---
id: 44-finetune-rf-detr
title: Fine-tune RF-DETR — The Founding Rule, With a Better Head
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: in_progress
depends_on: [41-rf-detr-detector, 11-training-job-runner, 12-head-instance-registry]
relates: [42-foundation-boxes-everywhere, 43-detection-localisation, 31-external-dataset-import]
source_files:
  - backend/app/ml/foundation/finetune.py
  - backend/app/ml/foundation/finetune_runner.py
  - backend/app/ml/foundation/instances.py
  - backend/app/ml/foundation/detect.py
  - backend/app/ml/foundation/build.py
  - backend/app/ml/foundation/registry.py
  - backend/app/api/v1/foundation.py
  - backend/pyproject.toml
routes:
  - POST /api/v1/foundation/finetune
  - GET /api/v1/foundation/finetune/{job_id}
  - POST /api/v1/foundation/finetune/{job_id}/cancel
models: []
test_files:
  - backend/tests/test_finetune.py
data_flow: greenfield
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [fine-tuning, rf-detr, frozen-backbone, provenance, detr, training]
path: Head Trainer/Fine-tuning
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - backend/app/ml/foundation/instances.py (instance ids build filesystem paths)
known_issues:
  - "**No frontend.** The whole feature is API-only: there is no button to start a fine-tune, watch it, or name the result. A fine-tuned model *does* appear in every picker as soon as it exists, because doc 42 lists foundation models, so the loop is usable once a run has been started by other means."
  - "**115 MB per fine-tune.** `save_pretrained` writes the whole model. Saving only the 6.9M trained parameters would be a quarter the size and would need a bespoke loader that reassembles them onto a base checkpoint; `from_pretrained` on a complete directory is the path transformers supports."
  - "Batch size 1 in practice — the loop feeds one image at a time. `FinetuneConfig.batch_size` exists and is ignored, which is worse than not existing; batching needs the processor's padding path and a collate function."
  - "No early stopping and no learning-rate schedule. The run does exactly `epochs` passes and keeps the best. Fine for six epochs on a few hundred images; wasteful for longer runs."
  - "Validation reuses the *training* split's class vocabulary by construction, but there is no test split — `split_indices` is called with `test_fraction=0`, so the reported mAP is a validation number, not a held-out one."
sister_projects: []
---

# 44 — Fine-tune RF-DETR

## Purpose

Let the user fine-tune a general detector on their own dataset and keep the result as a
named, provenance-tracked model beside the ones they downloaded.

## Why this is the founding rule, not an exception to it

RF-DETR's backbone **is** a DINOv2. So "freeze the backbone, train what sits on top" — the
rule this whole project is built on — applies to it unchanged. Measured on a real run:

```
frozen     23.3M   the DINOv2 backbone
trainable   6.9M   projector + 2-layer deformable decoder + a re-opened classifier
```

The difference from the Head Trainer is only **what sits on top**: a decoder designed for
detection, starting from COCO-pretrained weights, rather than a linear probe starting from
nothing. That is why it needs six epochs and a learning rate an order of magnitude lower.

`freeze_backbone` **returns** the two counts rather than only logging them, and the API
reports them, because "did it actually freeze?" is the question the whole feature rests on
and a silent no-op looks exactly like a slow success.

## Architecture

Two things are deliberately *not* shared with `training/runner.py`:

- **No feature cache.** That runner's payoff is that a frozen backbone yields identical
  features every epoch, so one pass replaces N. Here the trained part consumes multi-level
  features through a projector, so the whole model runs every step.
- **No `HeadTypeSpec`.** A fine-tuned RF-DETR is not a head: it has no backbone id to be
  composed against and cannot join `run_heads`' shared pass.

So it is a **foundation model you trained** — stored in `FoundationInstanceStore`, listed by
`GET /api/v1/foundation` beside the catalogue entries, and resolved by `build_foundation`
like any other id. That last part is what makes it appear in the Inference Viewer, the
Annotation Studio and the Dataset Generator **with no further work**: doc 42 already taught
all three to offer foundation detectors.

Metrics come from `detection_metrics` — the same function the Head Trainer reports — so the
numbers below are directly comparable to a trained head's on the same data.

## Measured: fine-tuned RF-DETR against the trained head

Thermal dataset, 6 epochs, same data and the same metric. The head is the best from doc 43,
after all three of its fixes:

| | trained head (doc 43) | fine-tuned RF-DETR | |
|---|---|---|---|
| mAP | 0.587 | **0.800** | +36% |
| mAP@50 | 0.818 | **0.817** | **identical** |
| mAP@75 | 0.338 | **0.783** | +132% |

**The mAP@50 being identical is the interesting result.** Both find the objects equally
well — a linear-ish head on frozen DINOv2 features is as good at *finding* a person in a
thermal image as a state-of-the-art detection decoder. What the decoder buys is
**placement**: mAP@75 more than doubles.

That is the honest answer to "should I just fine-tune RF-DETR instead?" — if you need tight
boxes, yes. If you need to know *where roughly*, a head trains in 90 seconds instead of six
minutes and produces a 400 KB checkpoint instead of 115 MB.

On a held-out thermal frame with two people:

```
rf-detr-nano (base)   nothing at all          — thermal is far outside COCO
fine-tuned            person 0.94 @ (425,284,50,100)   truth (425,283,52,100)
                      person 0.93 @ (346,274,69,115)   truth (340,273,78,117)
```

## Business Rules

1. **The classifier is re-opened for the user's classes**, through
   `from_pretrained(..., ignore_mismatched_sizes=True)` rather than by swapping the final
   layer by hand. The COCO head is discarded on purpose: keeping it would mean a detector
   that still answers `cake` on a chessboard after being shown chess pieces.
2. **Boxes are converted to normalised cxcywh** once, in `to_detr_labels`. The store speaks
   absolute xywh from the top-left. A missed conversion does not raise — it trains happily
   and predicts nonsense — which is why six tests pin it, including that a box at the origin
   has centre `(w/2, h/2)` and not `(0, 0)`.
3. **The split is by image**, with the configured seed. Boxes from one image in both splits
   is leakage that inflates validation with no symptom — doc 11's rule, same reason.
4. **The best epoch is saved as it happens**, not at the end, so a cancelled or crashed run
   still leaves the best model it reached. Re-saving under the same instance id is what
   stops that leaving a 115 MB directory per epoch.
5. **Gradients are clipped at 0.1.** DETR losses spike on the first steps of a re-opened
   classifier, and one bad batch can undo a COCO-pretrained decoder.
6. **A fine-tune inherits its base model's licence.** It *is* that model's weights, moved;
   training on your own data does not relicense someone else's checkpoint.

## Dependencies

`scipy` was added to the backend. transformers' DETR-family Hungarian matcher needs
`linear_sum_assignment`, and without it the run fails at the first backward pass with a
clear message. Verified against numpy 2.5 and torch 2.13 — unlike the `depth-anything-3`
package Wave 6 rejected for pinning `numpy<2`. Training only; inference never touches it.

## Verified

Against real weights on 2026-08-20, through the real API and the real store. The numbers
above are from that run. The saved model appears in `GET /api/v1/foundation` as
*"Thermal RF-DETR — fine-tuned from rf-detr-nano · 2 classes · map 0.800"*, is 115 MB on
disk, and runs through `POST /foundation/predict` like any catalogue entry.

**One real bug, found by looking rather than by a test.** The first comparison showed the
*base* `rf-detr-nano` returning the fine-tune's classes at its exact scores.
`prepared_model` had retargeted and then rewritten the **cached** instance, so every later
request for the base detector got the fine-tune — a result that reads as plausible rather
than as a bug. `build_foundation` grew a `fresh` flag that neither reads nor writes the
cache, and two tests pin it.

## Known Issues

See frontmatter — in particular that there is no UI for this yet.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
