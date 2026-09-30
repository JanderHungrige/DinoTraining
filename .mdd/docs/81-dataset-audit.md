---
id: 81-dataset-audit
title: Dataset Audit — Plain-Language Findings Before Training
edition: DinoTraining
depends_on: [03-dataset-store, 10-preprocessing-pipeline, 73-generator-video-source]
relates: [82-external-data-intake, 83-safe-fixes, 84-leakage-safe-split, 85-model-input-planning]
source_files:
  - backend/app/prep/__init__.py
  - backend/app/prep/profiles.py
  - backend/app/prep/stats.py
  - backend/app/prep/duplicates.py
  - backend/app/prep/finding_types.py
  - backend/app/prep/findings.py
  - backend/app/prep/findings_quality.py
  - backend/app/datasets/class_names.py
  - backend/app/ml/training/samples.py
  - backend/app/prep/audit.py
  - backend/app/prep/jobs.py
  - backend/app/api/v1/prep_audit.py
  - backend/app/api/v1/router.py
routes:
  - GET /api/v1/prep/targets
  - POST /api/v1/datasets/{dataset_id}/audit
  - GET /api/v1/prep/audits/{job_id}
  - GET /api/v1/datasets/{dataset_id}/audit
models: []
test_files:
  - backend/tests/test_prep_profiles.py
  - backend/tests/test_prep_findings.py
  - backend/tests/test_prep_duplicates.py
  - backend/tests/test_prep_audit_api.py
data_flow: reads-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, audit, dataset-quality, duplicates, class-imbalance, non-experts]
path: Prepare Data/Audit
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Scene grouping is by perceptual hash only. Two photos of the same scene from clearly different viewpoints are not grouped. DINO-embedding similarity, as planned in the wave, would catch those; it is left for the split's grouping (doc 84) or later, because the hash already found every real copy in the datasets measured."
  - "The class-support and imbalance rules count annotations (instances), not images. For classification targets, images per class would be the more natural unit." 
security_read_sites:
  - backend/app/prep/audit.py:_check_files (opens every stored image path of the dataset)
sister_projects: []
---

# 81 — Dataset Audit

## Purpose

Wave 11 exists because the tool is for people without data-science experience, and
preprocessing decides whether training works. The audit is where that starts. It reads a
dataset once and says, in plain language, what is wrong with it **for the model the user
wants to train**, why it matters, and what to do. It changes nothing: fixing is doc 83,
splitting is doc 84.

## Architecture

```
POST /datasets/{id}/audit {target}        a job (files are opened, hashes computed)
  prep/stats.py       one SQL pass: images, positive boxes and masks, verdict mix
  prep/profiles.py    what the target model does to an image (input size, resize rule,
                      the smallest object it can still see), read from the installed
                      model's preprocessor_config.json when there is one
  prep/duplicates.py  perceptual dHash per image → near-duplicate clusters
  prep/audit.py       file checks + findings.py's rules → DatasetAudit
GET  /prep/audits/{job}                   progress, then the report
GET  /datasets/{id}/audit                 the last report, persisted as audit.json
```

## Findings

Each finding has a severity (`ok`, `warn` or `problem`), a **title**, **what** was found,
**why it matters for training**, **what to do**, example image paths, and the numbers behind
it. The copy is written for someone who has never trained a model, with no term left
unexplained.

| Rule | problem | warn |
|---|---|---|
| Dataset size | < 20 images | < 100 images |
| Class support (instances) | a class < 10 | a class < 30 |
| Imbalance (largest ÷ smallest class) | > 50× | > 10× |
| Objects at the model's input | median < min visible px | 10th percentile < min visible px (→ tiling) |
| Unreadable or missing files | any | — |
| Copies: same picture (256-bit dHash ≤ 8 bits) **and** same annotations | — | any group |
| Shared scenes: same picture, different annotations | — | info: the split keeps each group together |
| Doubt (`unclear` share of annotations) | — | > 10 % |
| Class names that differ only in case, plural or spacing | — | any |
| Annotation kind vs target (e.g. segmentation without masks) | yes | — |
| Images with nothing annotated | — | > 60 % |
| Sequences (video or folder frames) | — | info: the split must keep them together (doc 84) |

## Business Rules

1. **Read-only.** An audit never modifies a dataset.
2. **Target-aware.** Object sizes are judged at the target model's input, not in source
   pixels: a 10.7 px object in a 2464 px frame is 1.7 px at 384 px (doc 49's arithmetic).
   With no target, size rules that need one are skipped and say so.
3. **Classes are counted as the trainer will see them**, through the same normalisation as
   `samples._class_name` (lower case, trailing full stop stripped). Otherwise the audit
   and training would disagree about how many classes there are.
4. **The last report is persisted** in the dataset directory (`audit.json`) with a content
   hash, which doc 88's recipe records.
5. **A missing image is a finding, not a crash.** Unreadable files are listed, and the
   rest of the audit completes.

## Verified on real datasets (2026-09-29)

| Dataset | Target | Findings |
|---|---|---|
| Chess pieces (289) | RF-DETR nano | **problem:** class `bishop` has **1** example, next to `black-bishop` and `white-bishop`, which is almost certainly a mislabel in the source data. **problem:** 659× imbalance, from the same cause. **warn:** 13 real copies, one checked by eye (same white knight, same square, same box). **info:** 271 images in 25 shared scenes. |
| Blood cells (364) | DINOv2 detection head | **warn:** 12× imbalance (RBC 4,153 vs platelets 361) |
| Wave 9 autoplay check (50) | RF-DETR nano | **warn:** only 50 images. **info:** 33 frames in 4 shared scenes (re-audited 19:25; an earlier stored report had none, see doc 84) |

The same chess audit over HTTP ran as a job through 289 of 289 images, with identical
findings.

**The first version was wrong about duplicates, and the real data showed it.**
- **What happened:** 8×8 dHash with transitive grouping called 284 of 289 chess photos
  duplicates.
- **What was really there:** the closest pair was at distance 0 with a mean pixel
  difference of 1.5/255, *but with a different piece in the corner*. The photos were the
  same scene, not the same example.
- **The consequence avoided:** "keep one" would have deleted correct, different
  annotations.
- **The fix:** a 16×16 hash (256 bits), and two findings instead of one. **Copies** need
  the same picture *and* the same annotations (a coarse signature on a 50-step grid), and
  "keep one" applies only to them. **Shared scenes** are informational and are exactly
  what the split must keep together.

## Bugs

- **2026-09-29: RF-DETR and SAM 2 were sized as letterboxed; their processors stretch to a
  square.** The object-size finding for those targets was computed with the long-edge
  scale; it now uses the stretch (doc 85, Bugs). The RF-DETR figures in the table above
  predate the fix. Its grid suggestion now comes from doc 85's planner, and says so
  honestly when even the largest grid leaves objects too small.
