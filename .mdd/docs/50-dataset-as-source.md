---
id: 50-dataset-as-source
title: A Dataset Is a Source — Not Just a Destination
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: in_progress
depends_on: [46-generator-folder-picker, 17-image-source]
relates: [32-studio-session-setup, 22-generator-panel, 31-external-dataset-import]
source_files:
  - backend/app/api/v1/datasets.py
  - apps/frontend/src/components/ImageSourceField.tsx
  - apps/frontend/src/lib/imageSource.ts
  - apps/frontend/src/hooks/useSessionImages.ts
  - apps/frontend/src/hooks/useAnnotationSession.ts
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/hooks/useImageSource.ts
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/components/ImageSourcePicker.tsx
  - apps/frontend/src/api/datasets.ts
  - apps/frontend/src/lib/proposeFor.ts
routes:
  - GET /api/v1/datasets/{dataset_id}/images
models: []
test_files:
  - backend/tests/test_library_routes.py
  - apps/frontend/src/components/ImageSourceField.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [dataset, image-source, annotation-studio, inference-viewer, dataset-generator, react]
path: Annotation Studio/Input
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**The whole listing, including every box, arrives in one response.** For the datasets here (392 images, 932 boxes) that is nothing; for one with 100k boxes it is a large JSON. Paging would mean a request behind every press of Next, which is the thing this avoids."
  - "In the Studio a dataset source **is** the target — its own dataset picker is hidden. Re-annotating one dataset's images into a *different* one is therefore not possible from here; the Dataset Generator does exactly that and keeps the two separate."
  - "The Inference Viewer's dataset choice is a second control rather than a mode, so a path and a dataset are mutually exclusive by construction (choosing one clears the other) but the form does not *say* so — it just changes."
  - "`useAnnotationSession` was split twice to stay under 300 lines (`useSessionImages`, `lib/proposeFor`). The split is clean but the hook is still the largest thing in the frontend."
sister_projects: []
---

# 50 — A Dataset Is a Source

## Purpose

Let every tab that takes a folder of images take **a dataset you already have** instead.

## Why this was missing, and why it matters more than it sounds

The app already *has* the user's images the moment they import or generate a dataset. Making
them find the folder again is asking a question the app can answer — and worse, sometimes
the honest answer is "not where you remember": a dataset created with `copy_images` holds
copies inside the store, so the folder they point at is not what the dataset contains.

It also makes the Studio able to **correct and extend** a dataset, which it could not do at
all before. Doc 31 imported three HuggingFace datasets and doc 49 imported OSDaR23; until
now the only thing that could be done with an imported dataset was train on it.

## Where the annotations go

Jan chose: **back into that same dataset.** Picking a dataset means "carry on working on
this", so its boxes load onto the canvas and edits replace them, and the separate dataset
picker is hidden while a dataset is the source — offering a second choice would let the two
disagree without saying so.

That is why `GET /datasets/{id}/images` returns **the boxes, not a count**. They have to be
on the canvas the moment an image opens, and one request per image would put a round trip
behind every press of the Next key. `image_annotations` has already loaded them to answer
the query.

## Business Rules

1. **A folder path and a dataset id are never one field.** Both are "a string in a field",
   and one input taking either would have to guess. A radio makes the choice explicit.
2. **A dataset with no images is not offered.** Choosing it would start a session with
   nothing in it and no explanation.
3. **The selection falls back to the first usable dataset even when the source already
   claims to be a dataset.** A test found the opposite: reading `value.datasetId` alone when
   the kind was already `dataset` looked right, and left the form pointing at an empty id —
   the state the very first switch produces, before the list has loaded — while rendering a
   select full of choices.
4. **Stored `prompt` becomes canvas `text` on the way in**, the exact mirror of
   `saveImageBoxes`. Skipping it loads a dataset whose boxes all read as unnamed, and the
   next save writes the blanks back — the same rename that cost doc 31 a bug.
5. **The Inference Viewer builds its own listing** rather than calling the backend's source
   route: that route answers "what is at this path", and a dataset is not at a path. Same
   shape out, so nothing downstream learns a second kind of source.

## What is *not* shared

`ImageSourcePicker` (doc 17's viewer) still takes a single image **or** a folder and means
different things by each, so it does not use `FolderField`'s "an image means its folder"
rule. That asymmetry is deliberate and is why the two components stayed separate.

## Verified

**In the running app on 2026-08-21.** The Studio's source picker offers "A folder" and "A
dataset you already have"; choosing the OSDaR23 holdout loaded 80 images, hid the separate
dataset picker, and put the dataset's own 8 boxes — `signal ×5, signal_pole, person ×2` —
onto the canvas with no score, which is correct for imported boxes. The Inference Viewer's
dataset select offered 16 datasets. 9 frontend tests, 5 backend.

## Known Issues

See frontmatter.

## Bugs

### 1 — A failed source left the previous session's images on screen

**Reported by Jan on 2026-08-21**: *"the image in the annotation tab is always the same.
Doesn't matter what model is chosen, it loads the same image also when choosing another."*

**Reproduced**: start a session on a folder, press *Change folder*, point at a path that
cannot be read, start again. The Studio showed `Image 1 / 289` and the **previous** folder's
picture, fully interactive, with only an error line above it.

That is worse than a stale display. The target dataset had already changed, so every box
drawn on those images would have been saved into the newly chosen dataset — annotating one
folder's pictures into another folder's dataset, with nothing on screen saying so.

**Cause**: `useSessionImages` replaced `images` only inside the `try`, on success. A failed
listing left the previous state untouched. The same shape was present in
`useGeneratorSession`.

**Fix**: clear before asking, not after answering. Both hooks now reset `images` (and the
Generator's boxes, masks and size) at the top of the effect, and expose a `loading` flag so
the surface says *"Loading images…"* rather than rendering an empty session that reads as an
empty folder.

**Pinned by** two tests in `useAnnotationSession.test.ts`, both confirmed to fail against the
previous code: one that the previous images are gone after a failed switch, and one that
they are gone *during* the load — because the window between asking and answering is the one
the user annotates in.

**Not a bug**: choosing a different *model* on the same source correctly shows the same
first image. The model decides the boxes, not the picture. That part of the report was the
app working as intended.
