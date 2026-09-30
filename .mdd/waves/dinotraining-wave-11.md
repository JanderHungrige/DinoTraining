---
id: dinotraining-wave-11
title: "Wave 11: Guided Data Preparation"
initiative: dinotraining
initiative_version: 10
status: complete
depends_on: dinotraining-wave-10
demo_state: "A user with no data-science background imports an external dataset and follows a guided flow. The app audits it and explains in plain language what is wrong, fixes what can safely be fixed, splits it without leakage, shows exactly what the chosen model will see, sets how class imbalance is handled, and hands a saved, reproducible preparation recipe to training. An AI assistant over MCP can run the same steps and gets the same explanations."
created: 2026-09-29
hash: 54f8b819
---

# Wave 11: Guided Data Preparation

**Jan's words (2026-09-29):** the most important and most complex wave. The tool is for users
with no data-science experience, and preprocessing is extremely important for training and
fine-tuning. For each available model there should be a pipeline that does the preprocessing
automatically as far as possible:
- the right train/test/val split;
- the input size;
- class imbalance;
- cropping;
- masking.

Where it helps, a guided process works out the right settings with the user. Anything that
cannot be generalised is explained, for example checking that image quality is good enough.
Data from the app's own Generator is easier, because the pipeline knows its output
parameters; external data is where this matters most.

## What already exists, and what this wave must not redo

- **Doc 10, the geometry.** Preprocessing is derived from backbone + head and returns the
  transform that moves boxes and masks with the image: letterbox, no silent centre-crop,
  nearest-neighbour for masks. This wave *decides* the settings, and doc 10 keeps *applying*
  them.
- **Doc 11, the split.** `split_indices` shuffles by image, which is right for photos and
  **leaks on video**. Doc 49 measured a 42% inflated mAP on 10 Hz OSDaR23, and the backlog
  has the gap open. Doc 73 now stores `sequence` + `frame_index`, so a group-aware split is
  finally possible.
- **Docs 49 and 62, tiling.** Tiling on the way in and on the way out already exist. What is
  missing is *deciding* that a dataset needs it. Doc 49's arithmetic (a 10.7 px median object
  arrives as 1.9 px at 448 px) is exactly the check that belongs in the audit.
- **Doc 48, format guidance.** A dataset format guide exists in the Training tab, and it
  becomes one part of the intake.
- **Docs 63 and 64, agents.** The agent guide and the MCP server are where every step here
  must also be reachable.

## Demo-State

1. **Import.** The user imports an external COCO dataset they have never looked at closely.
2. **Audit.** In plain language and with pictures, the app reports:
   - 38 near-duplicate images;
   - one class with 6 examples;
   - boxes stored as x1,y1,x2,y2 in a file that claims x,y,w,h;
   - the median object arriving at 2 px at the chosen model's input.

   Each finding says why it matters and what to do.
3. **One-click fixes** for what is safe: drop corrupt images, collapse duplicates, fix the
   box convention and merge two spellings of a class. The rest is explained: "look at
   these 12 images, they are motion-blurred".
4. **Leakage-free split.** Frames of one video, or near-duplicates, never land on both sides.
   Classes are stratified, and the per-split class counts are shown.
5. **"What the model sees".** Real images are rendered through the actual preprocessing plan
   with their boxes and masks, including tiles when tiling is recommended.
6. **Imbalance.** A strategy is recommended (weighted loss, balanced sampling or
   oversampling with augmentation), with the reason stated.
7. **Recipe.** A named, versioned preparation recipe is saved. The Training tab and Wave
   12's fine-tuning consume it, and the same run reproduces the same split.
8. **MCP.** An assistant over MCP runs the audit, reads the same findings and gets the same
   recipe.

*(Not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | dataset-audit | docs/81-dataset-audit.md | complete | — |
| 2 | external-data-intake | docs/82-external-data-intake.md | complete | dataset-audit |
| 3 | safe-fixes | docs/83-safe-fixes.md | complete | dataset-audit |
| 4 | leakage-safe-split | docs/84-leakage-safe-split.md | complete | dataset-audit |
| 5 | model-input-planning | docs/85-model-input-planning.md | complete | dataset-audit |
| 6 | imbalance-strategy | docs/86-imbalance-strategy.md | complete | leakage-safe-split |
| 7 | augmentation-presets | docs/87-augmentation-presets.md | complete | model-input-planning |
| 8 | preparation-recipe | docs/88-preparation-recipe.md | complete | leakage-safe-split, model-input-planning, imbalance-strategy, augmentation-presets |
| 9 | guided-preparation-flow | docs/89-guided-preparation-flow.md | complete | safe-fixes, preparation-recipe |
| 10 | training-consumes-recipe | docs/90-training-consumes-recipe.md | complete | preparation-recipe |
| 11 | preparation-for-agents | docs/91-preparation-for-agents.md | complete | preparation-recipe |

### Feature notes

1. **dataset-audit.** One report per dataset, computed server-side as a job for large sets.
   - **What it counts:**
     - images, boxes and masks per class, and per-image annotation counts;
     - box sizes, in absolute pixels and **at the target model's input**, and aspect ratios;
     - image resolutions and colour modes;
     - unreadable or corrupt files;
     - images with no annotations;
     - the verdict mix, where a high `unclear` share means labelling doubt;
     - boxes at or over the image edges;
     - the share of each image a mask covers.
   - **Near-duplicates and outliers use DINO embeddings**, which the app already computes.
     Cosine similarity finds duplicates that differ by a resize or a JPEG pass, which a
     perceptual hash misses. The same embeddings flag images far from the rest.
   - **Findings** are traffic-light rated, each with *what*, *why it matters for training*,
     *what to do*, and example thumbnails.
   - **Written for non-experts:** no jargon without a one-line explanation.
2. **external-data-intake.** Validation at import (COCO, OpenLABEL, folders + COCO):
   - **Coordinates:** a heuristic check of the coordinate convention: xywh vs xyxy, pixels
     vs normalised, and whether 1-based. It shows the evidence and asks, rather than
     guessing silently.
   - **Class names:** normalised (case, plural, synonyms), with a proposed mapping to
     confirm.
   - **Images:** every referenced image must exist and match the size the file declares.
   - **Provenance and licence:** recorded as text.
   - **Generator datasets take a fast path**, because their conventions are known by
     construction. Their audit still runs.
3. **safe-fixes.** One-click, previewed, reversible actions: exclude from training, never
   delete files.
   - drop unreadable images;
   - collapse near-duplicate clusters to one;
   - fix a detected box convention;
   - merge or rename classes;
   - drop or merge a class below a minimum count;
   - clip edge boxes.

   **Anything judgement-based is explained, not automated:** blur, lighting, wrong labels
   and domain mismatch come with a "look at these" review sheet.
4. **leakage-safe-split.**
   - **Groups** are what must stay on one side of the split: a sequence (doc 73), a
     near-duplicate cluster, or a source folder.
   - **Stratified** by class within the group constraint.
   - **Seeded and stored.** An `images.split` assignment (a migration, and **bump
     `LATEST_VERSION`**, bug class 6) means evaluation never reshuffles.
   - **Shown before use:** per-split class counts, with a warning where a class is absent
     from val or test.
   - This closes the backlog's video-split entry and doc 49's known issue.
5. **model-input-planning.** For each model family, derive what doc 10 will do:
   - the families are DINOv2/v3 heads, RF-DETR, SAM 2/3 and Grounding DINO;
   - the plan covers input size and patch multiple, letterbox or resize, normalisation,
     mask handling, and whether to tile. **Tiling is decided from the audit's object-size
     statistics** against the model's stride, and handed to docs 49 and 62 rather than
     recomputed.
   - **"What the model sees"** renders sampled images through the real plan, with their
     targets transformed. The user checks it visually, and it is the most important picture
     in the wave.
6. **imbalance-strategy.** It detects the imbalance ratio and a per-class support floor.
   - **Options:** class-weighted loss, a balanced sampler, oversampling rare classes with
     augmentation, or merging or dropping classes.
   - A recommended default is chosen from the numbers, and the reason is stated.
   - It is wired into the loss and sampler in `training/`. Doc 11 already reports per-class
     metrics so the effect is visible.
7. **augmentation-presets.**
   - **Geometry-safe:** targets always go through doc 10's transform.
   - **Presets by domain:** outdoor/rail, indoor, microscopy and documents, with a live
     preview.
   - **Nothing that changes meaning by default:** no flips for a text or sign class.
8. **preparation-recipe.** A versioned, named object saved with the dataset. It holds:
   - the split and fixes applied;
   - the input plan;
   - the imbalance strategy and augmentation;
   - the audit snapshot hash.

   It is reproducible: the same recipe gives the same split. Training runs record which
   recipe they used, for provenance (doc 12).
9. **guided-preparation-flow.** A "Prepare data" flow, probably its own tab or a mode in
   Training:
   - **Steps:** pick the dataset(s) and the model to train → audit → fix → split → "what
     the model sees" → imbalance → augmentation → review → save the recipe.
   - **Every step has a recommended default** and a one-paragraph *why*, and experts can
     skip ahead.
   - **Manual checks are part of the flow** (the "look at these images" sheets), because
     some quality problems only a human can see.
10. **training-consumes-recipe.** The Training tab and fine-tuning accept a recipe.
    - Training without one still works, with a clear "unprepared data" warning.
    - The Generator's datasets get a pre-filled recipe.
11. **preparation-for-agents.** Audit, fixes, split, plan and recipe become API endpoints
    and MCP tools (doc 64), whose docstrings carry the same explanations the UI shows.
    Doc 63's guide gains a "prepare before you train" recipe.

## Open Research

- **Near-duplicate threshold and cost:** DINO-embedding similarity on 10k images, and whether
  to reuse the feature cache.
- **Label-noise detection:** use disagreement between a trained head and the labels to flag
  likely mislabels. It may be valuable, and it may be its own wave.
- **Box convention detection:** how reliable can the heuristic be? Which evidence
  (out-of-frame counts, w/h vs x2/y2 distributions) is strong enough to *propose* a fix?
- **Where the flow lives:** a new tab, or a mode of Training? And how does it relate to
  Library (doc 51) and Inspect (doc 74), which already browse datasets?
- **Existing datasets have no stored split.** Assign on first recipe, and never
  retroactively for trained heads, whose provenance names the old random split.
