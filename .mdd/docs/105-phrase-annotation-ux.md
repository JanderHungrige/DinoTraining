---
id: 105-phrase-annotation-ux
title: Phrase Annotation UX — A Phrase Bar, Comma Variations, Picture Checks, and the Concepts Explained
edition: DinoTraining
depends_on: [103-phrase-data-model, 104-annotation-target]
relates: [106-mask-editing, 108-prompts-and-hard-negatives]
source_files:
  - apps/frontend/src/components/phrases/PhraseBar.tsx
  - apps/frontend/src/components/phrases/SelectedPhrases.tsx
  - apps/frontend/src/components/phrases/PictureChecks.tsx
  - apps/frontend/src/components/phrases/PhraseManager.tsx
  - apps/frontend/src/components/phrases/PhraseHelp.tsx
  - apps/frontend/src/lib/phraseEdit.ts
  - apps/frontend/src/hooks/usePhraseKeys.ts
  - apps/frontend/src/phrases.css
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/hooks/usePicturePhrases.ts
  - apps/frontend/src/api/phrases.ts
routes: []
models: []
test_files:
  - apps/frontend/src/lib/phraseEdit.test.ts
  - apps/frontend/src/components/phrases/PhraseBar.test.tsx
  - apps/frontend/src/components/phrases/PictureChecks.test.tsx
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, phrases, sam3, variants, hard-negatives, keyboard, non-experts]
path: Annotation Studio/Phrases
initiative: dinotraining
wave: dinotraining-wave-14
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Phrases link to outlines only. A selected box without an outline says so and points at 'Masks from my boxes' (doc 106)."
security_read_sites: []
sister_projects: []
---

# 105 — Phrase Annotation UX

## Purpose

Jan (2026-09-30): *"During annotation the user needs to add new phrases, and possibly has
several different phrase masks per task. A dropdown with an option to add new ones? How
does this work best?"*

**Answer: a phrase bar, not a dropdown.**
- **A dropdown hides the vocabulary** behind a click, and for SAM 3 the vocabulary *is* the
  task. Chips keep every phrase in view, with its count.
- **Switching is one key (1–9).**
- **Two jobs happen per picture,** and both need the phrases in view:
  - saying *which* phrases a mask answers to;
  - saying *which* phrases the whole picture was checked for.

## The bar (above the canvas)

1. **Phrase chips:** one per dataset phrase, classes included (doc 103's implicit phrases).
   - Each chip shows the text and its outline count, and its variations on hover.
   - The **active** chip is highlighted.
   - **Keys 1–9** pick the active phrase while focus is not in a text field. The chip shows
     its number.
2. **"+ phrase":**
   - A text field that takes **comma-separated variations**: `signal, railway signal, light
     signal` is one phrase with two variations.
   - A class picker beside it defaults to the selected outline's class, else to the new
     phrase itself.
   - Enter adds it and makes it active.
3. **The selected outline:** its phrases as removable chips (its class name is fixed), and
   **Add "<active phrase>"**.
   - A phrase of another class is not offered; its chip says so on hover.
   - A selected *box* without an outline says: "Phrases go on outlines — make one from this
     box first."
4. **This picture:** one row per phrase, with **All marked** · **Not in this picture** ·
   **clear**.
   - The state shows on the row, and **A** / **N** mark the active phrase.
   - A status is saved at once, on its own request; it is not part of Save.

## Explained where it is used (`PhraseHelp`, a folding card in the bar)

- **Phrase variations:** "Type the phrase the way you would ask for it, plus 2–4 other
  wordings, separated by commas. The model learns them as one concept. You do not need
  every synonym: a few teach it that the wording can vary, and it generalises from there."
- **All marked / Not in this picture:** "SAM 3 learns from every picture you checked. 'All
  marked' says every instance of this phrase here has an outline. 'Not in this picture'
  says there is none, and teaches the model *not* to find it here. A picture you did not
  check is left out for that phrase, never guessed."
- **Hard negatives:** "Pictures marked 'not in this picture' are the strongest lessons,
  especially when something similar *is* there. Add the look-alikes as 'not to be confused
  with' under Manage phrases. Training also adds generic unrelated phrases (`num_negatives`)
  and other phrases of your dataset (`num_cross_negatives`) as negatives — see the SAM 3
  training settings."

## Manage phrases (a folding list in the bar)

- For every phrase:
  - **variations,** as a comma-separated field;
  - **not to be confused with,** also comma-separated;
  - Save for each row.
- Doc 103's rules come back as messages at the row, for example "'crimson car' is already a
  phrase of its own…".

## Business Rules

1. **Phrase edits on outlines are canvas edits.** They mark the picture unsaved and are
   written by Save, like a class change.
2. **Picture checks and phrase definitions are saved at once,** because they are not part
   of the picture's annotations.
3. **Keys never fire while typing.**
4. **For targets that do not need phrases** (classifier, detector, SAM 2), the bar starts
   folded as "Phrases (optional)". It is open for SAM 3 and "keep all options open".

## Found while building: the canvas already owns 1, 2, 3 and N

- **The clash:** a focused box on the canvas uses 1/2/3 (and P/N/U) for its verdict
  (doc 47). The phrase keys would have fired as well.
- **The fix:** the canvas marks those keys handled (`preventDefault`), and the phrase keys
  skip a handled event. With a box focused, the box wins; with nothing focused, the phrase
  bar has them.
- **Implicit class phrases:** under Manage phrases they have no row yet. Saving their
  variations adds them (POST) rather than failing.

## Verified (2026-09-30)

- **Tests:** frontend 1014 green (11 new), tsc clean. The Studio file is back at 300 lines.
- **Running app, "Wave 12 filled-ring convention" as SAM 3:**
  - The bar showed `1 blob 61` and `2 ring 139`.
  - Key **2** made *ring* active, and key **A** marked this picture "all marked" for ring.
    The row turned green, and the check was saved at once.
  - **clear** returned both rows to "not checked", so the dataset was left as it was.

## Amended 2026-09-30 (Jan's test): which class, look-alikes, delete

Jan found three things unclear while annotating flames and their reflections.

- **Which class does "+ phrase" belong to?**
  - It used to be implied by the selected outline, or else the phrase became a class of
    its own. With several classes, nobody could tell.
  - `AddPhraseForm` now has a **belongs to** select: *a class of its own (new)* or an
    existing class. It defaults to the selected outline's class, storing only the user's
    override.
  - The hint says what follows: a new class, or a more specific wording for some of that
    class's outlines, which still train as that class for boxes and heads.
- **"Not to be confused with" read as "make the look-alike a class too".**
  - "How phrases work" has two new entries.
  - *Phrases and classes.*
  - *Look-alikes and wrong proposals:*
    - Two things you both want found (signal and street light) are two classes.
    - A wrong proposal in the same picture (a reflection proposed as a flame) is
      **rejected**, and the picture is marked **All marked**. The flame outlines are then
      the whole answer, so no class is needed.
  - The look-alike field has its own hint: names only, for things that rarely share a
    picture with the phrase.
  - Training changed to match (doc 108, amended).
- **Delete a phrase:**
  - Each stored phrase in Manage phrases has Delete, confirmed once. It removes the phrase,
    its outline links and its checks; the outlines keep their class.
  - A class's own phrase with no row has no Delete, and says it lasts as long as that
    class's outlines.
- **German placeholders were German:** "Straßenlaterne", although SAM 3 reads English.
  They are English again, and the add hint says to write phrases in English.

## Also from Jan's test (2026-09-30): search terms, Back, tabs

- **A comma now separates search terms.** "flame, reflection" used to come back as one
  label.
  - **Grounding DINO** separates phrases only at a full stop. `normalise_prompt` now turns
    commas, semicolons and line breaks into full stops (`app/ml/concepts.py`).
  - Its post-processor still joined the tokens of two terms, giving labels like "tree
    light". Each box is now relabelled with the one term it matched most strongly.
  - **SAM 3** read the whole text as one concept. It now runs one pass per term, and each
    pass labels its own masks.
  - **Checked** with the real grounding-dino-tiny: before, "car light" and "tree car
    light"; after, only the terms asked for.
- **Back to overview:**
  - "Change folder" became "← Back to overview", the one way to end a session.
  - With unsaved changes it asks first: save and go back, go back without saving, or
    stay. A failed save stays.
- **The session survives other tabs.**
  - App keeps the Studio mounted once it has been opened, hidden while another tab shows.
    The picture, unsaved edits and a running prescan are still there on return.
  - The phrase keys are off while the Studio is hidden (`active`), so typing "a" in
    another tab cannot mark a picture.

## Also from Jan's test (2026-09-30, second round)

- **The Studio's action bar is the Generator's (doc 70):**
  - Run and "Save to dataset" sit directly beside Previous and Next.
  - Auto-propose and Auto-save are named in full below them.
  - **Auto-propose** (off by default) runs once per picture that arrives with nothing on
    it, never over existing boxes.
  - **Auto-save** (on by default) is what the Studio always did: moving on saves first.
    - With Auto-save off, moving on from unsaved changes is refused with a note, instead
      of dropping them.
    - The Generator does drop them; in the Studio that would lose the work on a picture's
      outlines.
- **Below "All marked / Not in this picture":** a note that a fully annotated phrase can be
  checked for the whole dataset at the end with "Mark the rest".
- **The prompt hints** now say commas or full stops separate terms:
  - Grounding DINO, the concept field, and the Inference Viewer.
  - SAM 3's hint no longer says "one concept at a time; run them one by one". It says each
    term is searched on its own.

## Bugs

(none yet)
