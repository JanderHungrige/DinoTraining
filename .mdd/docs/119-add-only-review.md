---
id: 119-add-only-review
title: Add-only Review — "Review for m10" Shows the Older Pictures, Keeps What Is Saved, Proposes Only m10
edition: DinoTraining
depends_on: [117-saved-means-complete, 118-new-class-question]
relates: [60-annotation-studio-round, 53-prescan]
source_files:
  - apps/frontend/src/lib/mergeProposal.ts
  - apps/frontend/src/hooks/useAnnotationSession.ts
  - apps/frontend/src/hooks/useReview.ts
  - apps/frontend/src/components/ReviewBanner.tsx
  - apps/frontend/src/components/StudioActions.tsx
  - apps/frontend/src/components/NewClassQuestion.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/types/annotation.ts
  - apps/frontend/src/api/datasets.ts
  - apps/frontend/src/api/datasetMasks.ts
  - apps/frontend/src/i18n/en/studio2.ts
  - apps/frontend/src/i18n/de/studio2.ts
routes: []
models: []
test_files:
  - apps/frontend/src/lib/mergeProposal.test.ts
  - apps/frontend/src/components/ReviewBanner.test.tsx
  - apps/frontend/src/components/StudioActions.test.tsx
  - apps/frontend/src/hooks/useAnnotationSession.masks.test.ts
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, review, completeness, proposals, sam3]
path: Studio/Review
initiative: dinotraining
wave: dinotraining-wave-15-5
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 119 — Add-only Review

## Purpose

- **Jan:** "Here one would not only generate new annotations, but must be able to show
  existing ones. Mixing them with newly generated ones is tricky."
- **This doc:**
  - It shows the pictures saved before class m10 (doc 117), each with its saved
    annotations.
  - The model proposes **only m10**, and its proposals are **added**.
- **A trap today:** re-running the prompt on a saved picture replaced every annotation that
  was not hand-drawn, so accepted proposals were lost too. The general fix below closes it
  everywhere, not only in the review.

## The general fix: a re-run adds, it does not replace what is saved

- **`CanvasBox.saved`:** true for an annotation loaded from the dataset (boxes and masks),
  and for every annotation once its picture was saved successfully.
- **`mergeProposal(current, proposed, only?)`:**
  - **Keeps:** saved annotations and hand-drawn ones.
  - **Replaces:** only the previous unsaved proposals.
  - **Adds:** the new proposals, except one that overlaps a kept annotation of the same
    class by box IoU ≥ 0.5. The object is already there, and a second copy is what doc 107
    flags as "twice".
  - **With `only`:** it keeps only the proposals of that class.

## Review for a class

- **Opening it:** from doc 118's reminder, "Review for m10". The Studio loads the pictures
  unknown for m10 (`/completeness/unknown`) as its picture filter (the prescan's
  mechanism, doc 53), and shows a banner:

  > **Reviewing for m10 — picture 3 of 20.** Only m10 is proposed; your saved annotations
  > stay. [No m10 here →] [End review]

- **Run:**
  - For a prompt source, it asks for "m10" only.
  - For a head or foundation source, it runs as set up and keeps only m10's proposals.
  - Auto-propose works in the review even though the pictures have annotations, because
    the result is add-only.
- **Saving:** Save (or moving on with Auto-save) refreshes the picture's `annotated_at`, so
  it is known for m10 from then on (doc 117).
- **"No m10 here →":**
  - It marks the picture `absent` for m10 (an explicit check) and moves on, with no save
    needed.
  - It is disabled while the picture has an m10 annotation.
- **End review:** clears the filter. The reminder of doc 118 shows how many are left, and
  disappears at zero.

## Rules

1. **Nothing saved is dropped by a proposal,** in the review or anywhere in the Studio.
2. **The review never marks a picture it did not show:** only Save or "No m10 here" on that
   picture.
3. **A picture skipped** with Next and nothing changed stays unknown. Skipping is not
   reviewing.

## Found while verifying: a filter that starts on the picture already shown

- **What happened:**
  - "Review for star" started on o000, the picture already on screen.
  - `setFilter` reset the annotations and the image size. The image source did not
    change, so the picture never loaded again to report its size, and its stored masks
    were not fetched again.
  - The Studio hung on "Loading image…" with no annotations.
- **Scope:** the prescan filter (doc 53) had the same trap whenever its first hit was the
  current picture.
- **Fix:** when the new list starts on the current picture, only the filter and index
  change.
- **Test:** `useAnnotationSession.masks.test.ts`, "a filter that starts on the picture
  already shown". It fails without the fix.

## Verified (2026-09-30)

- **Tests:**
  - `mergeProposal.test.ts` (3):
    - saved and hand-drawn annotations are kept, unsaved proposals replaced;
    - the same object is not added twice;
    - a review keeps only its class.
  - `ReviewBanner.test.tsx` (3).
  - `StudioActions` in a review proposes only that class, even over annotations.
  - The regression test above.
  - Frontend: 1089 green; tsc clean; `useAnnotationSession.ts` is back to 300 lines.
- **Running app, German**, on "Wave 12 filled-ring convention", with class star made after
  its 70 saved pictures:
  - "Später durchsehen" left the line "star: 70 Bilder noch nicht durchgesehen.
    Durchsehen für star".
  - "Durchsehen für star" showed "Durchsehen für star — Bild 1 von 70.", with the 4 saved
    annotations of o000 on screen.
  - "Prompt ausführen" asked Grounding DINO for "star" only. The list went from 4 to 7:
    three new "star" proposals (one on the star shape), with blob and ring untouched.
  - After a reload, "Kein star hier →" on o000 moved to o001, and the reminder dropped to
    69. "Durchsehen beenden" cleared the filter.
  - The phrase star, its check and the class were deleted again. Nothing was saved to the
    dataset.

## Bugs

(none yet)
