---
id: dinotraining-wave-15-5
title: "Wave 15.5: Annotating the normal way — saved means complete"
initiative: dinotraining
initiative_version: 13
status: in_progress
depends_on: dinotraining-wave-15
demo_state: "The user annotates m8 and m9 screws without ever pressing a check button, adds 'screw' as an umbrella term for both, and creates class m10 after twenty saved pictures. The app asks whether m10 occurs in those; 'review later' queues them, the review shows each picture's saved annotations, proposes only m10 and adds to them. SAM 3's job note shows 'screw' answered by m8 and m9 outlines, and the unreviewed pictures left out for m10."
created: 2026-09-30
hash: d0a6edcb
---

# Wave 15.5: Annotating the normal way — saved means complete

**Jan's request (2026-09-30), after testing Wave 14's phrase bar:**
- "Wenn annotiert wird, werden auch alle Objekte markiert."
- "Nicht annotierte Bilder kommen nicht in das Datenset."
- So the two buttons (All marked / Not in this picture) are extra clicks.
- A new class below is already a phrase, so "+ phrase" as a class is doubled and confusing.
- What he does want:
  - labels m8 and m9, with the umbrella term "screw" assigned to both;
  - variations as technical vocabulary;
  - look-alikes (a nail for a screw).
- A class added later needs a question: "does it only occur from now on?" Options are
  *does not occur* in the earlier pictures, or *review later*. The review must show the
  existing annotations and add to them.

**Numbering:** "Wave 16" (the website) is referenced in about 30 places in code and docs,
so this wave is 15.5, following the precedent of Wave 7.5.

## What already exists

- **Wave 14 (docs 103–110):**
  - phrases (one class each), variations and look-alikes;
  - outline ↔ phrase links (`mask_phrases`);
  - per-picture checks (`image_phrase_status`);
  - "Mark the rest";
  - SAM 3's query planner (`sam3_queries.py`: positives, absent, cross, rejected, confusable,
    generic).
- **Saving:** a picture enters a dataset only when saved. An empty picture that was
  proposed on is saved as "nothing here".
- **Timestamps:** `images.annotated_at` (last save) and `dataset_classes.created_at` exist.
  "Complete for the classes that existed when it was saved" can therefore be derived from
  existing data, with no migration.
- **Re-running the prompt:** a re-run on a saved picture keeps only hand-drawn boxes. Accepted
  proposals are replaced, which is today's trap for adding to a picture.

## Decisions (from the conversation)

- **Classes are made in one place:** the annotation list's class picker. The phrase bar no
  longer creates classes.
- **Saved = complete** for every class that existed at save time. The check buttons fold
  away, kept only for imported or partly annotated datasets.
- **Phrases must be English** (SAM 3 reads English). The hints keep saying so.

## Demo-State

1. **Annotate without checks.**
   - In the Studio, annotate m8 and m9 on about twenty pictures and save them. Never press
     All marked / Not in this picture.
   - The phrase bar shows no class-creating "+ phrase" and no check buttons (they are folded).
2. **Umbrella term.** Add "screw" as an umbrella term for m8 and m9. The bar shows it with
   the count of all m8 + m9 outlines.
3. **Variations and look-alikes.** Add "m8 bolt" as a variation of m8, and "nail" as a
   look-alike of screw.
4. **A new class.**
   - Create class m10 in the list. The app asks: "m10 is new. 20 pictures are already
     saved: does not occur there / review later."
   - Choose **review later**.
5. **Review.**
   - "Review for m10" opens only those 20 pictures, each with its saved annotations.
   - Running the prompt proposes only m10 and adds to the existing annotations, replacing
     nothing.
   - Saving takes the picture off the review list.
6. **Training.** A SAM 3 job's note shows:
   - "screw" queries answered by m8 and m9 outlines;
   - no "screw" cross negative on a picture with m8;
   - the still-unreviewed pictures left out for m10.

*(This wave is not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | umbrella-terms | docs/115-umbrella-terms.md | complete | — |
| 2 | phrase-bar-slim | docs/116-phrase-bar-slim.md | complete | umbrella-terms |
| 3 | saved-means-complete | docs/117-saved-means-complete.md | complete | — |
| 4 | new-class-question | docs/118-new-class-question.md | complete | saved-means-complete |
| 5 | add-only-review | docs/119-add-only-review.md | complete | saved-means-complete, new-class-question |

### Feature notes

1. **umbrella-terms (115).**
   - **What it is:** a phrase that belongs to several classes (`phrase_classes` table, or a
     phrase with class list). "screw" → {m8, m9}.
   - **Training:** its answers are all outlines of its classes. It is never a cross or
     absent negative on a picture where one of its classes occurs.
   - **Checks:** it is complete on a picture when all its classes are.
   - **Recipe provenance and MCP** carry it. Existing one-class phrases are unchanged.
2. **phrase-bar-slim (116).**
   - **The bar holds three things:**
     - umbrella terms (name + class multi-select);
     - per class: variations and look-alikes;
     - Delete.
   - **Removed:**
     - "+ phrase" with "a class of its own";
     - the per-outline sub-phrase linking (SelectedPhrases).
   - **Existing data:** `mask_phrases` links keep training as before, but the UI no longer
     offers them. The doc decides whether to migrate a linked sub-phrase into a class.
   - **The check buttons** fold into "Only for imported or partly annotated datasets". The
     "Mark the rest" note moves with them.
   - **Help:** "How phrases work" is rewritten around this, with the m8/m9/screw and
     nail examples.
3. **saved-means-complete (117).**
   - **The rule:** a saved picture is complete for every class whose `created_at` is not
     after its `annotated_at`.
     - A class inferred from boxes with no stored row counts as existing from the start.
     - An explicit check (`image_phrase_status`) always wins.
   - **Training:** `sam3_queries` and the phrase table use it in place of doc 108's per-phrase
     "checked mode". A picture saved before a class existed is left out for that class,
     never a negative.
   - **Imports** (COCO etc.) have no Studio save. The doc decides: saved at import, or
     unchecked until reviewed.
   - **The audit** (doc 107) reports "N pictures saved before class X".
4. **new-class-question (118).**
   - **When:** a class is created in the Studio (list picker) or Prepare while the dataset
     has saved pictures.
   - **The question:** "X is new. N pictures are already saved."
     - **Does not occur there:** marks them absent for X.
     - **Review later:** leaves them unchecked for X (feature 117 already does), and puts
       them on a review list.
   - **MCP:** the same choice as a parameter of class creation.
5. **add-only-review (119).**
   - **Opening it:** "Review for X" opens the dataset filtered to the pictures unchecked
     for X, reusing the prescan / second-look filter.
   - **Proposals:** the prompt runs for X only. Its proposals are added beside the saved
     annotations, which stay.
   - **General fix:** a re-run on any saved picture keeps accepted annotations, not only
     hand-drawn ones.
   - **Saving** checks the picture for X, and the list shrinks.
   - **Optional:** a prescan for X first, showing the pictures where the model finds
     anything.

## Open Research

- **Umbrella terms on outlines already linked to sub-phrases (Wave 14 data):** migrate or
  keep reading? Decide in 116 after looking at real datasets. Very few exist so far.
- **Imports:** does an imported COCO dataset count as saved-complete for its categories? Most
  COCO exports are complete per category, but not all. Decide in 117; perhaps ask at import.
- **The timestamp rule needs a class-rename check.** Doc 82's rename must not reset
  `created_at`, or every picture would fall out for the renamed class.

## Build summary (2026-09-30)

All five features are built, tested and checked in the running app. The status stays
`in_progress` until Jan confirms the demo-state.

- **Demo run:** a SAM 3 fine-tune of 1 epoch with umbrella "shape" over blob and ring, and
  class star made after 70 saved pictures.
  - mIoU 0.217 → 0.450.
  - The job notes name the umbrella, and the 70 pictures left out for star.
- **Found and fixed on the way:**
  - A filter that started on the picture already shown hung on "Loading image…" (doc 119).
    The prescan filter had the same trap.
  - `ruff format tests` reformatted about 60 unrelated files; they were restored.
