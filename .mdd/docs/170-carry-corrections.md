---
id: 170-carry-corrections
title: Carry My Corrections to the Next Picture (Studio, for video frames)
edition: DinoTraining
depends_on: [119-add-only-review]
relates: [169-umbrella-box-classes-and-studio-scroll]
source_files:
  - apps/frontend/src/lib/carryCorrections.ts
  - apps/frontend/src/hooks/useCarryCorrections.ts
  - apps/frontend/src/hooks/useConcealed.ts
  - apps/frontend/src/components/CarryCorrections.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
routes: []
models: []
test_files:
  - apps/frontend/src/lib/carryCorrections.test.ts
  - apps/frontend/src/hooks/useCarryCorrections.test.ts
data_flow: reads-existing
last_synced: 2026-10-21
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, video, proposals, corrections, matching, iou]
path: Studio/CarryCorrections
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 170 — Carry My Corrections to the Next Picture

## Jan (2026-10-21)

- "Get the annotation of a model, compare the annotations; if they are located at the
  same point and we changed something before, choose the different class or make the
  annotation also rejected as previous. The difficulty is making sure that we are talking
  about the same object. This would only work with very similar images."
- The use: annotating video frames, where neighbouring pictures barely change.

## What it does

- A checkbox in the Studio, **"Carry my corrections to the next picture"**, off by
  default and remembered (`studio.carryCorrections`).
- **Recorded:** for every model proposal on the picture you leave, what the model said
  (class, verdict) and what you made of it:
  - **renamed** to another class;
  - **verdict changed** (rejected = negative, or unclear);
  - **removed**.
  Untouched proposals record nothing. Saved and hand-drawn annotations record nothing:
  there is no model answer to compare them with.
- **Applied:** when the next model proposals arrive on the new picture, each is matched to
  a recorded correction. A match applies the same decision: the class, the verdict, or
  removal. Matched boxes stay editable. A note says what was carried
  ("Carried from the previous picture: 2 renamed, 1 rejected, 1 removed").
- **It chains:** picture 6's carried decisions are recorded again when you leave it, so a
  correction follows the object through the clip until you change it.

## "The same object"

- Same **model class** (what the model said, not what you renamed it to; compared like
  `phraseKey`), and **IoU ≥ 0.6** between the old and the new box.
- **One to one:** the pairs are taken best IoU first; each correction and each proposal is
  used once. Two people side by side stay two people.
- **Same picture size** only: a correction from a 1920×1080 picture never applies to a
  640×480 one.
- Anything unmatched stays an ordinary proposal. A missed match costs a click; a wrong
  match would cost a wrong label, so the threshold is on the strict side.
- Only from the picture you just left (next or previous), never from older ones.

## Not done

- No tracking (SAM 2 propagation). The boxes come from the model on each picture.
- No carry-over of hand-drawn boxes.

## Also: `useConcealed`

`AnnotationStudioTab` was at 299 lines. The concealment state (what the threshold and
"hide all" keep off screen) moves into its own hook to make room.

## Built (2026-10-21)

- `lib/carryCorrections.ts`: `recordCorrections`, `applyCorrections` (IoU ≥ 0.6, same
  model class, one to one best first); `mergeProposal.iou` exported for it.
- `hooks/useCarryCorrections.ts`: remembers proposals as they arrive, records on picture
  change, applies to the next proposals when the size matches.
- `components/CarryCorrections.tsx`: the checkbox and the note, EN/DE.
- `hooks/useConcealed.ts`: concealment out of the Studio (283 lines now).
- **Tests:** 6 for the matching (rename, rejection, removal, moved too far, other class,
  one-to-one), 4 for the hook in the session's real order (carry, chain, off / other
  size, saved and hand-drawn untouched). Frontend 1234.
- **In the running app** (a throwaway dataset, deleted after): 10 OSDaR23 fire-site
  frames with RF-DETR. Picture 1: the 92% train rejected, a traffic light renamed to
  train, a box removed. Picture 2: the 89% train arrived rejected, the traffic light as
  train, the removed one gone; the note said one of each.
