---
id: 43-detection-localisation
title: Detection Localisation — Teaching the Head Where, Not Just What
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: complete
depends_on: [09-head-implementations, 11-training-job-runner]
relates: [16-inference-engine, 31-external-dataset-import, 41-rf-detr-detector]
source_files:
  - backend/app/ml/training/losses.py
  - backend/app/ml/heads/modules.py
  - backend/app/ml/heads/decode.py
routes: []
models: []
test_files:
  - backend/tests/test_detection_quality.py
  - backend/tests/test_head_modules.py
  - backend/tests/test_head_decode.py
  - backend/tests/test_training_losses.py
data_flow: reads-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [object-detection, fcos, centerness, giou, vitdet, resolution, metrics]
path: Head Trainer/Detection
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**Saved detection heads from before this doc cannot be loaded.** `DetectionHead` gained a projection, a learned upsample and a GroupNorm, so `load_state_dict` refuses old checkpoints rather than silently mismatching. Jan chose this over the alternatives on 2026-08-20; a detector retrains in under two minutes."
  - "**This is ViTDet's up-branch, not its full feature pyramid.** One finer level, not several. Extra levels solve scale *variation* and these datasets do not have it — their objects run 35-80 px. Full multi-level would rewrite the assigner, the loss and the decoder for a benefit this data cannot demonstrate. Revisit if a dataset arrives with objects spanning an order of magnitude."
  - "**Chess mAP@50 regressed** — 0.837 after the loss fixes, 0.734 with the finer grid. Its mAP@75 more than doubled over the same step (0.178 -> 0.479) and its overall mAP rose, so the head is placing boxes far better and finding slightly fewer at loose IoU. Thirteen classes on 202 images is also the most overfit-prone case here, and the head grew from ~4k parameters to ~115k."
  - "**Blood and chess both ran the full 30 epochs without early stopping**, so neither had converged. The numbers below are a floor, not a ceiling."
  - "Single training runs, and training is not reproducible (`.mdd/BACKLOG.md`). Two identical configs measured ~4% apart on mAP, so single-digit percentages in the table are noise; the 40%+ moves are not."
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

Same data, same splits, same 30-epoch budget, same backbone, measured at each step.
**base** = doc 31, **loss** = centerness + GIoU, **fine** = the finer grid on top.

| dataset | mAP base → loss → fine | mAP@50 | mAP@75 |
|---|---|---|---|
| thermal | 0.404 → 0.447 → **0.587** (+45%) | 0.590 → 0.605 → **0.818** (+39%) | 0.203 → 0.243 → **0.338** (+67%) |
| blood | 0.387 → 0.411 → **0.550** (+42%) | 0.610 → 0.627 → **0.775** (+27%) | 0.154 → 0.172 → **0.325** (+111%) |
| chess | 0.525 → 0.525 → **0.606** (+15%) | 0.748 → 0.837 → 0.734 (−2%) | 0.065 → 0.178 → **0.479** (+637%) |

Two things are worth reading carefully rather than celebrating.

**The loss fixes and the resolution fix helped different things.** The loss step moved
mAP@75 and left mAP@50 alone, exactly as the diagnosis predicted: finding was never the
problem. The resolution step moved *both*, because a finer grid gives more places for an
object to be found as well as more precision about where it is.

**Chess mAP@50 regressed** — 0.837 → 0.734 — while its mAP@75 nearly tripled over the same
step. The head is placing boxes far better and finding slightly fewer at loose IoU. Thirteen
classes on 202 images is the most overfit-prone case here and the head grew from ~4k
parameters to ~115k, which is the likely cause. Reported rather than buried.

**Blood and chess both ran all 30 epochs without early stopping**, so neither had converged.
These are a floor.

Training is not reproducible run to run (`.mdd/BACKLOG.md`) — two identical configs measured
~4% apart — so single-digit percentages here are noise. The 40%+ moves are not.

## Three: one coarse scale

Every box was regressed from a single **32×32 grid of 14 px cells**, whatever the object's
size — chess pieces are ~35×62 px at the model's 448 px input. There is a floor on
placement precision that no loss can get under.

`DetectionHead` now **projects to 128 channels, upsamples ×2 with a learned transposed
convolution, and predicts on the resulting 64×64 grid of 7 px cells.** `box_ltrb` is scaled
by the *stride* rather than the patch size, and `assign_detection_targets` and
`detection_decode` scale with it — all three read one `DETECTION_UPSAMPLE` constant, because
if they disagree the targets land on different cells than the predictions and nothing
crashes; the head simply learns nothing while every loss looks plausible.

This is **ViTDet's up-branch, not its full feature pyramid.** A pyramid's extra levels solve
scale *variation*, and these datasets do not have that problem — their objects run 35–80 px.
Full multi-level would rewrite the assigner, the loss and the decoder for a benefit this
data cannot demonstrate.

### It breaks saved heads, deliberately

The parameter shapes changed, so `load_state_dict` refuses pre-doc-43 checkpoints. Jan chose
that over the two alternatives, both worse: *parameter-free upsampling* keeps checkpoints
loadable while silently changing what their weights mean, and *a second head type* means
maintaining two detection heads forever. A detector retrains in under two minutes.

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
