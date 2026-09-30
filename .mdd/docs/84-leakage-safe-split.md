---
id: 84-leakage-safe-split
title: Leakage-Safe Split — Groups That Never Straddle Train and Test
edition: DinoTraining
depends_on: [81-dataset-audit, 82-external-data-intake, 83-safe-fixes]
relates: [11-training-job, 49-rfdetr-rail-evaluation, 73-generator-video-source, 88-preparation-recipe, 90-training-consumes-recipe]
source_files:
  - backend/app/prep/split.py
  - backend/app/prep/split_service.py
  - backend/app/prep/stats.py
  - backend/app/api/v1/prep_split.py
  - backend/app/api/v1/router.py
routes:
  - POST /api/v1/datasets/{dataset_id}/split
  - GET /api/v1/datasets/{dataset_id}/split
models:
  - images.split (schema v9)
test_files:
  - backend/tests/test_prep_split.py
  - backend/tests/test_prep_split_api.py
data_flow: writes-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, split, leakage, video, scenes, stratification, non-experts]
path: Prepare Data/Split
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts:
  - function: "training uses images.split instead of shuffling (train / val; test for the final score; buffer never)"
    when: "whenever a stored split exists for the dataset"
    satisfied_by: 90-training-consumes-recipe
satisfies_contracts: []
known_issues:
  - "Scene groups come from the last stored audit. A split made without an audit warns that scenes could not be grouped; a split made after images were added but before a new audit uses stale scene groups without saying so. Doc 89's flow runs the audit first, which closes the common path."
  - "Stored splits are not used by training until doc 90. Until then a run still shuffles images (doc 11)."
  - "Stratification is greedy by group. With very few groups (one video, a handful of scenes) a side can end up small or empty; the report says so rather than hiding it."
security_read_sites: []
sister_projects: []
---

# 84 — Leakage-Safe Split

## Purpose

Doc 11 shuffled single images into train and validation. For independent photos that is
right. For what this app mostly produces it is wrong: consecutive video frames (doc 73)
and several photos of one scene (doc 81) put near-copies on both sides, and the
validation score then measures memory. On 10 Hz rail video that inflated mAP by 42 %
(doc 49). A non-expert cannot see that, so the split has to make it impossible.

## Groups

The unit of splitting is a **group**, and a group never straddles two sides:

1. **Scene groups** from the last audit: the same picture (256-bit dHash), whatever it is
   annotated with.
2. **Segments of a sequence.** A sequence (a video or a frame folder) is first cut into
   **stretches** wherever the step between annotated frames jumps to more than 3× the
   usual step (`GAP_FACTOR`). Each stretch is then cut into segments of
   `max(5, length / 10)` frames. A trailing piece under 5 frames joins its neighbour.
3. Otherwise an image on its own.

Groups are joined transitively (union-find), so a scene that spans two segments pulls
them together.

## Assignment

Groups go largest first (ties broken by a seeded shuffle) to whichever side is furthest
below its target share. The measure is the image share plus the share *of each class the
group contains*, so rare classes reach validation and test where possible. The defaults
are 70/20/10 with seed 42. The same data and seed always give the same split.

## Buffer

Where an evaluation segment meets a segment on another side **inside one stretch**, the
frames nearest the boundary become `buffer`, used by no side. The width is 1 % of the
sequence, at least 1 frame. Two limits apply:

- **Never across a gap.** Frames either side of a gap are not near-copies.
- **Never the whole run.** An evaluation run keeps at least one frame per boundary it
  touches.

## Modes

| Mode | What it does |
|---|---|
| `auto` | the grouping above; stored in `images.split` |
| `keep-source` | keeps the split an import brought (doc 82); refused with a reason if any image has none |

Refusals (shares outside 0–1, nothing to split, missing source splits) are 422 with the
reason, never 500.

## Report

The report gives images and class counts per side, the buffer size, the number of groups
and the largest one, plus plain-language warnings:

- no audit yet, so scenes were not grouped;
- a class that never appears in val or test;
- fewer than 5 images on an evaluation side;
- an evaluation side left empty (`auto` only);
- one group holding most of the images.

`GET` returns the stored split's report.

## Verified live (2026-09-29, over HTTP)

| Dataset | Mode | train / val / test | buffer | groups |
|---|---|---|---|---|
| Wave 11 intake check (20) | keep-source | 10 / 10 / 0 | 0 | — |
| Wave 11 intake check (20) | auto | 16 / 3 / 1 | 0 | 12 |
| Wave 9 video check (6 frames: 0–4 and 16–20) | auto, first version | 4 / 0 / 0 | 2 | 6 |
| Wave 9 video check | auto, fixed | 3 / 3 / 0 (warned) | 0 | 2 |
| Wave 9 autoplay check (50), stale audit | auto | 34 / 10 / 6 | 0 | 50 |
| Wave 9 autoplay check (50), re-audited | auto | 39 / 7 / 4 | 0 | 21 |

**Two things the running app showed that the unit tests had not:**

- **The buffer ate every evaluation frame.** The first version made one-frame segments
  of a six-frame clip and treated frames 4 and 16 as neighbours. The buffer then
  consumed validation and test entirely. The fix is three rules, each pinned by a test:
  gaps split stretches, segments have a minimum length, and a buffer never empties a run.
- **A split is only as good as the audit behind it.** With a stored audit that had no
  scene groups, the autoplay dataset split into 50 singletons. Re-audited, its 27-frame
  scene stayed whole in train. Hence the no-audit warning, and the known issue about
  stale audits.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
