---
id: 109-annotation-quality-aids
title: Annotation Quality Aids — A Written Guideline, a Second Look, Frame Consistency, Unclear Honoured
edition: DinoTraining
depends_on: [104-annotation-target, 107-task-aware-preparation, 108-prompts-and-hard-negatives]
relates: [110-annotation-for-agents, 81-dataset-audit]
source_files:
  - backend/app/datasets/quality.py
  - backend/app/api/v1/dataset_quality.py
  - backend/app/api/v1/router.py
  - backend/app/datasets/coco.py
  - backend/app/api/v1/datasets.py
  - backend/app/prep/findings_task.py
  - backend/app/finetune/adapters/sam3_queries.py
  - apps/frontend/src/api/quality.ts
  - apps/frontend/src/components/GuidelinePanel.tsx
  - apps/frontend/src/components/SecondLook.tsx
  - apps/frontend/src/hooks/useSecondLook.ts
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/quality.css
routes:
  - GET /api/v1/datasets/{dataset_id}/guideline
  - PUT /api/v1/datasets/{dataset_id}/guideline
  - POST /api/v1/datasets/{dataset_id}/second-look
  - GET /api/v1/datasets/{dataset_id}/second-look
  - PUT /api/v1/datasets/{dataset_id}/second-look/verdict
models: []
test_files:
  - backend/tests/test_dataset_quality.py
  - backend/tests/test_sam3_queries.py
  - apps/frontend/src/components/GuidelinePanel.test.tsx
  - apps/frontend/src/components/SecondLook.test.tsx
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [annotation-quality, guideline, review, consistency, video, unclear, non-experts]
path: Annotation Studio/Quality
initiative: dinotraining
wave: dinotraining-wave-14
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 109 — Annotation Quality Aids

## Purpose

Jan (2026-09-30): *"Also think of other important additions that are needed for the
different models to improve the quality of the training sets and later model performance."*

The data's biggest quality problem is **inconsistency**, not noise. The same kind of
object gets outlined two ways, a pole is sometimes included and sometimes not, a frame
calls the object "signal" and the next frame "light". These four aids target exactly
that.

## 1. A written guideline per dataset

- **What:** a short text of conventions — "include the pole?", "occluded more than half →
  unclear", "ring: outline *with* its hole filled".
- **Stored** as `datasets/<id>/guideline.md` via `GET`/`PUT /datasets/{id}/guideline`
  (`{text}`, up to 20 000 characters).
- **In the Studio:** a folding **Annotation guideline** panel beside the canvas, editable,
  saved with its own button. It opens by itself when the guideline has text, so a second
  annotator reads it first.
- **COCO export** carries it in `info.guideline`, and writes `guideline.md` beside the
  export.
- **Assistants** read and write it over MCP (doc 110).

## 2. A second look

- **Drawing the sample:** `POST /datasets/{id}/second-look` `{share=0.05, seed}` draws a
  random sample of the *annotated* pictures: at least 5, at most all of them. It replaces
  any earlier sample and returns it.
- **In the Studio:** **Second look** loads the sample as the session's picture list (the
  prescan filter's mechanism). A bar asks for each picture, **"Looks right"** or **"Needed
  a change"**, with `PUT …/second-look/verdict {path, verdict}`.
- **The figure:** `GET …/second-look` returns `{sample, reviewed, changed, rate}`, and the
  bar shows *"2 of 12 needed a change (17 %)"*. It is a data-quality number, not a model
  number: above ~10 % the conventions are unclear, and the guideline needs work before more
  annotating.

## 3. Frame consistency (audit rule `inconsistent-frames`)

- **What it flags:** in a video (pictures with a `sequence` and consecutive
  `frame_index`), a positive annotation whose box overlaps one in the next frame by IoU ≥
  0.7 while the class differs. That is the same object named two ways.
- **Severity** warn, with the frames as examples. It applies to every target, because
  every model suffers from it.

## 4. "Unclear" honoured by SAM 3 (`sam3_queries`)

- **The rule:** a picture with an *unclear* outline of phrase P is never used as a "none
  here" for P — not cross, not absent, not rejected. The annotator's doubt is not a
  negative.
- **Why not "not in this picture":** the picture check may still say it, but the unclear
  outline wins, because it is the more specific statement.

## Verified (2026-09-30)

- **Tests:** backend 1784 green (3 full runs); frontend 1032 green; tsc, ruff and mypy app
  are clean.
- **Running app, Studio on "Wave 12 filled-ring convention":**
  - The empty guideline showed as "Annotation guideline (none yet)".
  - After typing the dataset's real convention, *"Rings: outline with the hole filled"*,
    and pressing Save, the API returns it.
  - **Second look** drew a sample of 5 and narrowed the session to it (o003.png first).
  - **Needed a change** read "1 of 5 judged · 1 of 1 needed a change (100 %)", and **End
    second look** restored the full list.
- **The frame rule and the unclear rule** are covered by unit tests.
  - Frame rule: one object named "signal", then "light", in consecutive frames.
  - Unclear rule: an unclear outline blocks cross and absent negatives. It lives in
    `sam3_queries.py` and was committed with doc 108.

## Bugs

(none yet)
