---
id: 47-box-review-list
title: Box Review — A List Beside the Image, Not Just Clicks On It
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: complete
depends_on: [05-annotation-canvas, 42-foundation-boxes-everywhere]
relates: [32-studio-session-setup, 45-concept-segmentation-everywhere, 24-mask-review-canvas]
source_files:
  - apps/frontend/src/lib/boxReview.ts
  - apps/frontend/src/components/BoxReviewList.tsx
  - apps/frontend/src/components/AnnotationCanvas.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/lib/boxReview.test.ts
  - apps/frontend/src/components/BoxReviewList.test.tsx
  - apps/frontend/src/components/AnnotationCanvas.overlap.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, object-detection, review, accessibility, overlap, threshold, react]
path: Annotation Studio/Review
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**Renaming is per box, not per class.** Thirty boxes proposed as `person` need thirty edits to become `pedestrian`. A bulk 'rename every «person»' control is the obvious next step and was left out to keep this change one surface rather than two."
  - "**Partial overlap is still ambiguous on the canvas.** Paint order fixes containment completely — a box that fully covers another can no longer hide it — but where two boxes merely cross, whichever is on top takes the click in the crossing region. No paint order fixes that in general; the list is the unambiguous route to any box."
  - "The Dataset Generator's box review gets the numbered canvas but **not** the list. Its review surface is a different component with its own mask/box switch, and adding a second panel there is a separate change."
  - "The list caps at `26rem` and scrolls. With a hundred boxes that is a long scroll and there is no grouping by class or sorting by score."
  - "The threshold is **not** persisted across images or sessions. Navigating to the next image keeps it (it lives in the tab), but reopening the Studio resets it to 0."
sister_projects: []
---

# 47 — Box Review

## Purpose

Make the Studio usable for reviewing **detector output**, not just for hand-drawing a few
boxes.

## Two problems, reported together

> "First, having two boxes over each other, the box below cannot be clicked if covered.
> Second, if we have object detection, the annotation style does not work."

They have the same cause. The canvas was built for a handful of boxes you drew yourself,
where click-to-cycle is a good interaction: one gesture, no menu, hundreds of times. A
detector proposing thirty boxes breaks all of it at once — the verdict is behind however
many clicks the cycle needs, the class is nowhere on screen, and a large box swallows every
click meant for the small one inside it.

## The overlap fix, and its honest limit

Every box is an absolutely-positioned `<button>` filling its own rect, so **whichever is
painted last takes the click**. `inPaintOrder` sorts by **descending area**, which means a
box that *entirely contains* another can never hide it — the contained box is by definition
smaller and is therefore painted later.

That is a complete fix for containment, which is the case Jan hit and the case a detector
produces constantly (a scene box around object boxes). It is **not** a fix for partial
overlap: where two boxes merely cross, one of them is still on top in the crossing region,
and no paint order resolves that in general. The list is the answer there, and that is the
better reason for it to exist than any of the others.

## The list

Each box gets a row: **number, class, probability, four buttons.**

| | why |
|---|---|
| number | how a person says "that one" — and it is drawn on the box, so the image and the list agree |
| class | for detection output this is the thing being checked; it was previously nowhere on screen |
| probability | the reviewer's main prior for where to spend attention |
| ✓ ✗ ? 🗑 | **one click**, not a cycle. Reaching "unclear" on thirty boxes used to be sixty clicks |

The number comes from the box's position in the **unfiltered** list, so it never moves when
the slider moves, when a box is relabelled, or when the paint order changes. A number that
renumbers is worse than no number.

The class is an `<input>` rather than text plus an edit button, because a proposal run
produces one class name repeated many times and the common correction is retyping it. It
only *looks* like a field on hover or focus — thirty bordered inputs in a column read as a
form to fill in rather than a list to skim.

## Business Rules

1. **A box with no score is never hidden by the threshold.** Hand-drawn boxes carry no
   score, and so do imported ones. Treating a missing score as 0 would make the user's own
   work vanish as they dragged the slider — silently, and the next save would drop it.
2. **Hiding and removing are two actions.** The slider is reversible and costs nothing to
   explore; discarding is neither. So the slider filters, and a separate button says
   *"Remove 2 below"* and discards exactly what is currently hidden.
3. **The threshold starts at 0.** A review surface that opens with boxes already filtered
   out looks like a model that found fewer than it did.
4. **The slider is hidden when nothing has a score.** A control that does nothing reads as
   broken.
5. **The chosen verdict is filled, not merely tinted.** Hue alone leaves the state invisible
   to a colour-blind reviewer, and `aria-pressed` only reaches a screen reader.
6. **Remove carries no `aria-pressed`.** It is not one of the three labels, and marking it
   pressed would claim it is a state the box holds.
7. **Click-to-cycle stays.** It is still the right interaction for a box you just drew.

## Verified

**In the running app on 2026-08-21**, Grounded SAM over a chessboard photo — the containment
case exactly:

```
list order   1 chess board 65%   2 pawn 56%   3 chess piece king 33%
             4 chess chess 30%   5 piece 24%

paint areas  265946  265946  2662  2662  1450      <- descending
canvas tags  1 chess board | 4 chess chess | 2 pawn | 3 chess piece king | 5 piece
```

Box 1 is the whole board and contains all four others; they are painted after it and are
clickable. Their **numbers** stay 1–5 in list order while their **paint** order is by area —
which is the distinction the whole design rests on.

Then, live: the slider at 0.32 gave *"3 boxes · 2 below cutoff"*, dropped the canvas to
three boxes and offered *"Remove 2 below"*; one click on ✗ for box 2 flipped it to negative;
renaming row 1 to `board` changed the tag on the image to `1 board` immediately.

33 tests across the three files, including that paint order is by **area** rather than width
alone, that it does not mutate its input, and that a hand-drawn box survives a threshold of
0.9.

## Later additions

**2026-08-25 — hiding everything that is already there.** Asked for as: *"add a button for
annotation, to hide all existing boxes (and labels in the list at the side) — this makes
drawing new boxes, adding new labels more easy."* Exactly right: thirty proposals cover the
thing you wanted to add, and the score slider cannot help because what is in the way is
usually the confident boxes.

`Hide the N boxes already here` takes a **snapshot of the ids on screen** rather than
applying a live predicate. A box drawn afterwards is the entire point of pressing it, so it
must stay visible; a rule like "hide everything not hand-drawn" would hide the new one the
moment it was saved and reloaded.

The one thing that had to change underneath: hidden-by-slider and hidden-by-hand are now
**two sets, not one**. `Remove N below` acts on the slider's set alone. Folding them
together would have made that button discard work the reviewer had merely got out of the
way — silently, and with no undo. The header counts them separately for the same reason:
"below cutoff" is a claim about a score, and a concealed box has said nothing about its
score.

Concealment does not survive moving to the next image. It is about the picture in front of
you, and the ids would be stale anyway.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
