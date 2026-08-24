---
id: 55-unfreezing
title: Training the Backbone — Where It Works, and Where It Cannot
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-8
wave_status: complete
depends_on: [44-finetune-rf-detr, 43-detection-localisation, 49-osdar23-rail]
relates: [11-training-job-runner, 41-rf-detr-detector, 18-shared-backbone-pass]
source_files:
  - backend/app/ml/backbone.py
  - backend/app/ml/training/unfreeze.py
  - backend/app/ml/training/live_loop.py
  - backend/app/ml/training/config.py
  - backend/app/ml/training/runner.py
  - backend/app/ml/training/job.py
  - backend/app/ml/foundation/finetune.py
  - backend/app/ml/foundation/finetune_runner.py
  - backend/app/api/v1/foundation_finetune.py
  - apps/frontend/src/api/foundation.ts
  - apps/frontend/src/components/FinetunePanel.tsx
routes: []
models: []
test_files:
  - backend/tests/test_unfreeze.py
  - backend/tests/test_finetune.py
  - apps/frontend/src/components/FinetunePanel.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [training, unfreezing, backbone, fine-tuning, architecture, measurement]
path: Head Trainer/Fine-tuning
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**`unfreeze_blocks` on the head path is refused by `TrainingConfig` but not *offered* by `TrainingRequest`**, so an API caller who sends it gets silence rather than an error — pydantic drops unknown fields, which is this app's behaviour everywhere. No broken head can be produced either way; the door is absent rather than locked."
  - "**`live_loop.py` and `unfreeze.py` are written, tested and unused by the head runner.** They exist because they are the working half of a feature whose other half (saving a backbone with a head) is a design decision nobody has taken. Dead-ish code, kept deliberately and explained here rather than deleted and rediscovered."
  - "Partial unfreezing addresses `encoder.layer`, which is `Dinov2Model`'s shape and RF-DETR's inner backbone's shape. A backbone built differently raises `BackboneNotUnfreezableError` rather than training nothing."
  - "**One run each.** Training is not reproducible here (`.mdd/BACKLOG.md` — two identical configs measured ~4% apart), so the 8% mAP gain below is above the noise floor but not by a large margin. The mAP@75 gain of 20% is."
  - "No learning-rate schedule for the backbone group. A warmup would probably help more than the 0.1 scale factor does, and is the obvious next thing to try."
sister_projects: []
---

# 55 — Unfreezing

## The question

Jan asked why RF-DETR is not a head, whether its DINOv2 is unfrozen, and whether the project
should offer heavier training now that quality matters more than minutes.

The first answer given was incomplete. Measuring it produced a better one.

## Why RF-DETR is not a head — the version measurement forced

The original answer was architectural: a `HeadInstance` is `backbone_id` + head weights
composed through `run_heads`' shared backbone pass (doc 18), and RF-DETR's decoder consumes
multi-scale features through a projector, so it cannot eat that pass's output. True, and not
the deepest reason.

**The deeper reason is that a head has nowhere to put a backbone.** Doc 44 froze RF-DETR's
DINOv2 by choice — 23.3M frozen, 6.9M trained — so the 0.857 mAP on rail was achieved
*with the backbone frozen*. Unfreezing looked like a free lever. It is not, on the head
path, and the reason is the thing that defines what a head is.

## What happened when it was built anyway

The whole path was built: a gradient-carrying backbone forward (`extract_trainable`, kept
separate from `extract` so no inference caller can lose its `no_grad` guarantee), block
selection, discriminative learning rates, and an uncached epoch loop. It ran. Then:

```
                       time   trainable   val mAP    holdout mAP
frozen, 15 epochs        78s      0.0M      0.390        0.150
unfreeze=4, 15 epochs   648s      7.1M      0.327        0.000
```

**0.000.** Not degraded — nothing. And the run reported a plausible validation number the
whole way.

The cause, confirmed directly: `load_backbone` returns a process-wide cached instance, and
training mutates its weights **in place**. The head is fitted against a backbone that no
longer exists once the process ends, because a `HeadInstance` stores head weights beside a
`backbone_id` and there is nowhere to write the modified backbone. A fresh process loads the
pristine one, and the head is meaningless against it.

There is a second, worse consequence in the same measurement: **the mutated backbone leaks
to every other caller in the process** — inference, other heads, the annotators — until
restart. That is doc 44's cache-poisoning bug in a new place.

So the answer to "why isn't RF-DETR a head" is now: **a head that carries its own backbone
has stopped being a head.** It cannot share `run_heads`' pass, it is ~88 MB rather than
400 KB, and it is a self-contained predictor — which is the definition of a foundation
model, and exactly what RF-DETR is. The category is not a label; it is load-bearing.

`TrainingConfig` therefore refuses `unfreeze_blocks != 0`, with an error that says why and
where to go instead.

## Where it does work, and by how much

The fine-tune path saves the **whole model** with `save_pretrained`, so a modified backbone
travels with the decoder fitted against it. Same experiment, same data, same temporal
holdout (doc 49 — a random split on 10 Hz video is a training number):

| | time | trainable | val mAP | **holdout mAP** | mAP@50 | **mAP@75** |
|---|---|---|---|---|---|---|
| frozen | 238s | 6.9M | 0.934 | 0.781 | 0.981 | 0.582 |
| **unfreeze 4 blocks** | 283s | 14.0M | 0.946 | **0.843** | 0.988 | **0.698** |

Three things worth reading rather than celebrating.

**It costs 19%, not 8×.** On the head path unfreezing was 8.3× slower because it gives up
the feature cache. Here there was never a cache to give up — the whole model already ran
every step — so the extra cost is only the backward pass through four more blocks. Whether
unfreezing is expensive depends entirely on which path you are on.

**The gain is placement, not finding.** mAP@50 moved 0.981 → 0.988, which is nothing.
mAP@75 moved 0.582 → 0.698, which is 20%. The frozen features already separate a signal from
vegetation well enough to *find* it; adapting them makes the box tighter. That is the
opposite of doc 49's head-versus-detector result, where the gap was entirely in finding.

**Validation barely moved** (0.934 → 0.946) while the holdout moved 8%. The internal split
is still random over 10 Hz frames, so it is close to a training number and cannot see this.
The holdout can. This is the second time in two docs that a random split hid a real effect.

## Business Rules

1. **`extract_trainable` is a separate function, not a `grad=True` flag on `extract`.** Every
   other caller wants the `no_grad` guarantee and none of them should be able to lose it by
   passing the wrong argument.
2. **`caching_is_valid` gates the two loops**, and is the single most important line in
   `unfreeze.py`. A cached run holds features computed once; if the backbone also trains,
   they are stale from epoch two *and the backbone is not in the graph at all*.
3. **The backbone trains at 0.1× the head's rate**, in its own param group. One shared rate
   is the setting that makes unfreezing look like a bad idea — at 1e-3 a pretrained ViT is
   destroyed by a few hundred images and the run reports a worse number than the frozen one.
4. **`apply_unfreeze` runs even on the frozen path**, because a backbone left trainable by a
   previous run in the same process would otherwise train silently.
5. **The last blocks, never the first.** A ViT's later blocks carry the task-specific
   representation; the early ones carry general structure a few hundred images cannot
   improve and can easily damage.
6. **Counts are returned, not just logged** — doc 44's rule. "Did it actually unfreeze?" is
   the question the feature rests on, and a silent no-op looks exactly like a slow success.
7. **The panel gives the measured trade**, not "may improve accuracy". Numbers are a reason
   to spend 19% more time; a vague promise is not.

## What was *not* built

**Saving a backbone with a head.** It would make the head path work, and it costs: ~88 MB
per head instead of 400 KB, and a head with its own backbone cannot join the shared pass, so
`run_heads`' entire reason for existing goes away for that head. That is a wave-sized
decision about what this app's core abstraction is, not a flag. `unfreeze.py` and
`live_loop.py` are left in place, tested, for whoever takes it.

## Verified

22 tests in `test_unfreeze.py` including the decisive pair — `extract` produces no
`grad_fn` and `extract_trainable` does — plus that a step moves an unfrozen block and does
not move a frozen one. 6 more in `test_finetune.py` (three skipped without real weights, and
skipped rather than faked). 5 in the panel. Both experiments above were run end to end
through the real runners on real data.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
