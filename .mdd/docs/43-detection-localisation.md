---
id: 43-detection-localisation
title: Detection Localisation — Teaching the Head Where, Not Just What
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: in_progress
depends_on: [09-head-implementations, 11-training-job-runner]
relates: [16-inference-engine, 31-external-dataset-import, 41-rf-detr-detector]
source_files:
  - backend/app/ml/training/losses.py
routes: []
models: []
test_files:
  - backend/tests/test_detection_quality.py
data_flow: reads-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [object-detection, fcos, centerness, giou, loss, metrics]
path: Head Trainer/Detection
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**The multi-scale half of this feature is not built.** A ViTDet-style feature pyramid is the third fix and the only one that changes `DetectionHead`'s parameter shapes — which invalidates every saved detection head. That is a decision about Jan's data, not a technical choice, so it was raised rather than taken. See \"What is deliberately not here\"."
  - "Single training runs, and training is not reproducible (`.mdd/BACKLOG.md`). Two identical configs measured 4% apart on mAP earlier, so the thermal and blood mAP@75 gains (+20%, +12%) carry that noise. Chess (+174%) is far outside it."
  - "`box_ltrb` is still scaled by `patch_size` in `DetectionHead.forward`. Harmless while there is one scale; it becomes the stride and must move with it the moment a pyramid lands."
sister_projects: []
---

# 43 — Detection Localisation

## Purpose

Make the trained detector's **placement** as good as its **finding**. It was already finding
objects; it was ranking badly-placed boxes as highly as well-placed ones.

## The measurement this started from

The three detectors trained in doc 31:

| dataset | mAP@50 | mAP@75 | gap |
|---|---|---|---|
| thermal | 0.590 | 0.203 | −0.39 |
| blood | 0.610 | 0.154 | −0.46 |
| chess | 0.748 | **0.065** | **−0.68** |

mAP@50 respectable, mAP@75 collapsing. That is the signature of a detector that finds
objects and localises them badly — and it is not a capacity problem a bigger head fixes.

## Two defects, both in the loss

**1. Centerness was trained as a binary mask.**

```python
centerness_target = positive_flat.float()   # 1 inside a box, 0 outside
```

That is the same information the class head already carries. Since `decode.py` ranks by
`sigmoid(class) × sigmoid(centerness)`, the score had **no term reflecting how well a box
was placed** — a badly-centred prediction outranked nothing. Real FCOS centerness is
continuous, `sqrt(min(l,r)/max(l,r) · min(t,b)/max(t,b))`: 1 at a box's centre, 0 at its
edges. `decode.py`'s docstring already claimed it "suppresses cells near a box edge"; the
training target never taught that.

**2. Box regression used L1 on pixel distances.**

`0.05 * l1_loss` optimises something other than the metric being reported. A 5 px error
counts the same on a 20 px object as on a 200 px one, and the `0.05` was a hand-tuned fudge
to stop pixel-scale numbers dominating two logit-scale terms. **GIoU** is scale-invariant,
bounded in [−1, 1], and is the thing mAP@75 actually measures — so it needs no fudge, and
the three loss terms now sit on comparable footing without one.

Both boxes share their cell centre, so GIoU needs no absolute coordinates: widths are
`l + r`, overlaps are `min(l₁,l₂) + min(r₁,r₂)`.

The regression is also **weighted by centerness**, as FCOS does. A cell near a box's edge
sees that box at a glancing angle; letting it pull the regression as hard as a central cell
is what blurs the extents everything else then has to rank.

## Measured result

Same data, same splits, same 30-epoch budget, same backbone. Only the loss changed:

| dataset | mAP | mAP@50 | mAP@75 |
|---|---|---|---|
| thermal | 0.404 → **0.447** (+11%) | 0.590 → 0.605 (+3%) | 0.203 → **0.243** (+20%) |
| blood | 0.387 → **0.411** (+6%) | 0.610 → 0.627 (+3%) | 0.154 → **0.172** (+12%) |
| chess | 0.525 → 0.525 (+0%) | 0.748 → **0.837** (+12%) | 0.065 → **0.178** (+174%) |

**The gain lands where the diagnosis said it would.** mAP@50 barely moves on two of three —
finding objects was never the problem — while mAP@75 rises everywhere, most on chess, which
had the widest gap. Chess is also the case with many small same-class objects, where
ranking by placement matters most.

Training is not reproducible run-to-run (`.mdd/BACKLOG.md`), and two identical configs
measured ~4% apart earlier. The thermal and blood mAP@75 gains carry that noise; chess's
+174% does not.

## What is deliberately not here

**The multi-scale feature pyramid.** It is the third cause — every box is regressed from a
single 32×32 grid of 14 px cells, at every object size — and it is the only one of the
three that changes `DetectionHead`'s parameter shapes. That **invalidates every saved
detection head**, including the seven in Jan's store.

Two ways to avoid breaking them were considered and both are worse:

- *Parameter-free upsampling* (bilinear ×2 before the existing 1×1 convs) keeps checkpoints
  loadable but changes what their weights mean, because `box_ltrb` is scaled by
  `patch_size` and the stride would halve. A checkpoint that loads and quietly predicts
  differently is worse than one that refuses.
- *A second head type* (`dense-detector-v2`) keeps both working at the cost of maintaining
  two detection heads forever.

Breaking saved heads is a decision about Jan's data, so it was raised rather than taken.

## Business Rules

1. **Centerness is the continuous FCOS formula**, computed from the ground-truth ltrb.
2. **Box regression is GIoU, centerness-weighted**, with no scale factor.
3. **Centerness is supervised over positives only**, as FCOS does. Background cells get an
   untrained centerness, which costs nothing because the class term already suppresses them.
4. **A pure-background batch still returns a loss.** Legitimate supervision for a detector,
   and returning only the classification term keeps the graph connected.

## Verified

Twelve unit tests pin both signals from the directions that matter — centerness falls off
monotonically and is *not* the positive mask; GIoU is scale-invariant, bounded, and ranks a
worse box lower — plus the end-to-end retraining above, on real data through the real job
runner.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
