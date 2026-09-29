---
id: 70-generator-action-bar
title: Generator Action Bar — Auto-Propose and Auto-Save
edition: DinoTraining
depends_on: [69-remembered-entries]
relates: [26-generator-review-ui, 28-mask-review-ui, 29-generated-dataset-writer]
source_files:
  - apps/frontend/src/components/GeneratorActionBar.tsx
  - apps/frontend/src/hooks/useAutoPropose.ts
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/lib/generatorSave.ts
  - apps/frontend/src/types/generatorConfig.ts
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/components/GeneratorActionBar.test.tsx
  - apps/frontend/src/hooks/useAutoPropose.test.ts
  - apps/frontend/src/hooks/useGeneratorSession.review.test.ts
  - apps/frontend/src/tabs/DatasetGeneratorTab.test.tsx
data_flow: writes-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [dataset-generator, review, automation, usability, keyboard-free, react]
path: Dataset Generator/Action Bar
initiative: dinotraining
wave: dinotraining-wave-9
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "useGeneratorSession.ts is at exactly 300 lines after this doc. Doc 71 (autoplay) must not add to it; the orchestration belongs in its own hook." 
security_read_sites: []
sister_projects: []
---

# 70 — Generator Action Bar: Auto-Propose and Auto-Save

## Purpose

Requested: *"Have a checkbox next to the propose bounding box and save button to auto
trigger and/or save. Default of the checkboxes true. Shift the buttons right next to the
prev./next button, to minimise mouse movements."*

Reviewing a folder in the Generator today takes four clicks per image, across the full
width of the toolbar: **Propose** on the left, then **Save** on the left, then **Next** on
the far right, because a spacer pushes Previous and Next to the opposite edge. With both
auto boxes ticked, it takes one click: **Next**.

## Architecture

```
GeneratorActionBar            [Propose][☑ auto] [Save to dataset][☑ auto] [← Previous][Next →]
   │                           one cluster; the spacer is gone
   ├── autoPropose ─► useAutoPropose(session, enabled)   proposes when an image arrives
   └── autoSave ───► session.next({ autoSave }) / previous({ autoSave })
                                    saves a dirty image before leaving it
useGeneratorSession
   propose(): Promise<ImageReview | null>        now returns what it proposed
   save(review?): Promise<boolean>               explicit review, or the one on screen
   next/previous({ autoSave }): Promise<boolean> false when a save failed and it stayed
   saved(path): ImageReview | undefined          what this session wrote for an image
lib/generatorSave.ts   saveReview(config, review) — the one branch on boxes vs masks
```

`propose` returning its result and `save` accepting an explicit review are here for doc 71:
autoplay has to save *what was just proposed* without waiting for React to re-render the
state that `save()` would otherwise read.

## Business Rules

1. **Both boxes default to ticked** and are remembered (doc 69's hook,
   `generator.autoPropose` / `generator.autoSave`).
2. **Auto-propose fires once per arrival at an image.**
   - It does not fire if the session has already saved that image. Going back to a saved
     image shows what was saved, and a fresh proposal would silently replace the user's
     corrections, which auto-save would then write.
   - It does not fire again for the same image after a failure. A proposer that errors must
     not be retried in a loop.
   - StrictMode's double effect must not propose twice. A ref records the path that was
     asked for.
3. **Auto-save fires on leaving, never on proposing.** Leaving an image by *Previous* or
   *Next* is the only moment a save cannot catch a correction halfway through: the reviewer
   has said they are done with it. Saving on propose would write the model's opinion
   before the human has seen it.
4. **Auto-save saves only a dirty image**, which is exactly what the *Save* button allows.
   An image where nothing was proposed and nothing was drawn is not written. That matches
   the manual flow, where *Save* is disabled.
5. **A failed auto-save stays on the image.** The error is shown and the move does not
   happen. Moving on would discard the review the save was supposed to keep.
6. **The session remembers what it saved, per image**, and restores it on return:
   boxes, masks, the mask proposal needed to re-save, and the image size. Returning is
   no longer a blank canvas. It is the saved review, not dirty, and editing it makes it
   dirty again.
7. **Nothing new is stored on disk.** The per-image memory lives in the session only.
   Reloading stored annotations from the dataset is doc 74's job (Inspect datasets).

## Data Flow

Unchanged transport: `PUT /datasets/{id}/images` (boxes) and
`PUT /datasets/{id}/images/masks` (masks), both through `saveReview`. The only new state is
the session's `Map<path, ImageReview>` of what it saved.

## Dependencies

- 69-remembered-entries — `usePersistentState` for the two preferences.
- 26/28/29 — the review canvases and the dataset writer this drives.

## Verified in the running app (2026-09-29)

RF-DETR nano, running over the Chess pieces image folder into a new dataset:

- **Start proposed on its own.** "Proposing…" appeared with no click. RF-DETR found
  nothing on a chessboard (no COCO class), so Save stayed disabled, which is rule 4.
- **Drew a box by hand, then pressed Next.** `PUT /datasets/{id}/images → 200`, and the
  counter went to 1 saved, 1 positive.
- **Image 2 was proposed on arrival.** Previous saved it on leaving (2 saved). Back on
  image 1, the hand-drawn box was shown again, Save was disabled (clean), and **no new
  proposal** was requested. Only the image itself was fetched.

## Known Issues

## Bugs

- **2026-09-29 — a hand edit in the Generator never made the image saveable.** This was
  pre-existing, and found while verifying this doc. `setBoxes`/`setMasks` were React's raw
  setters, and only a proposal with results set `dirty`. So a box drawn on an image where
  the model found nothing could not be saved, which is exactly the "correct a false
  prediction" case this wave is about. The session now exports `editBoxes`/`editMasks`,
  which mark the image dirty. Only real edits reach them: the canvases call back on
  create, delete and relabel, never on selection. There is a regression test in
  `useGeneratorSession.review.test.ts`.
