---
id: 116-phrase-bar-slim
title: Phrase Bar, Slim — Umbrella Terms, Variations and Look-alikes; Classes Only in the List
edition: DinoTraining
depends_on: [105-phrase-annotation-ux, 115-umbrella-terms]
relates: [117-saved-means-complete, 103-phrase-data-model]
source_files:
  - apps/frontend/src/components/phrases/PhraseBar.tsx
  - apps/frontend/src/components/phrases/UmbrellaForm.tsx
  - apps/frontend/src/components/phrases/PhraseManager.tsx
  - apps/frontend/src/components/phrases/PartialChecks.tsx
  - apps/frontend/src/components/phrases/PhraseHelp.tsx
  - apps/frontend/src/components/phrases/PictureChecks.tsx
  - apps/frontend/src/lib/phraseEdit.ts
  - apps/frontend/src/phrases.css
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/i18n/en/phrases.ts
  - apps/frontend/src/i18n/de/phrases.ts
routes: []
models: []
test_files:
  - apps/frontend/src/components/phrases/PhraseBar.test.tsx
  - apps/frontend/src/i18n/phrases.german.test.tsx
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [phrases, sam3, umbrella-terms, annotation-studio, ux]
path: Studio/Phrases/Bar
initiative: dinotraining
wave: dinotraining-wave-15-5
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 116 — Phrase Bar, Slim

## Purpose

Jan, after using doc 105's bar:
- Every class below is already a phrase, so "+ phrase" as a class was doubled and
  confusing.
- The checks are extra clicks when every picture is annotated completely.
- What he does need:
  - umbrella terms (doc 115);
  - variations as technical vocabulary;
  - look-alikes.

## The bar, top to bottom

1. **Chips:** every class and umbrella with its outline count. An umbrella chip shows its
   members, e.g. "screw · m8, m9". They are an overview; nothing is created from here.
2. **"+ Umbrella term":**
   - A name, and the classes as checkboxes, two or more.
   - The hint: "A general name over several classes, e.g. screw for m8 and m9. Write it in
     English."
   - Refusals come back from doc 115 in the user's language.
3. **Manage phrases:**
   - **Each class:** Variations, Not to be confused with, Save, Mark the rest (in the
     folded section, see 5).
   - **Each umbrella:** its members, variations, look-alikes and Delete.
   - **Sub-phrases from Wave 14** (a phrase of one class under another name, linked to
     single outlines) are listed as "older sub-phrase", with Delete. They keep training as
     before; nothing new of that kind can be made.
4. **How phrases work,** rewritten in four entries:
   - **Classes are phrases:** a class name is what SAM 3 is asked; classes are made in the
     annotation list.
   - **Umbrella terms:** m8, m9 and screw.
   - **Variations:** technical vocabulary, 2–4, in English.
   - **Look-alikes:** a nail for a screw, for things that rarely share a picture. A
     reflection in the same picture is rejected (✗) instead.
5. **Folded, "Only for imported or partly annotated datasets":**
   - the picture checks (All marked / Not in this picture), their keys, and "Mark the rest";
   - the sentence: "A picture you save counts as complete for the classes it has then
     (doc 117). Check by hand only where that is not true."
   - Keys 1–9, A and N work only while this is open. Folded, "a" or "n" in the Studio does
     nothing phrase-related.

## Removed

- **`AddPhraseForm`** ("+ phrase" with "belongs to"). Classes are made in the list's picker
  (doc 60). Variations are added per class in Manage phrases.
- **`SelectedPhrases`** (a selected outline's phrases). An umbrella needs no per-outline
  link, and a sub-kind is a class.
- **The comma rule** survives in Manage phrases: "red car, crimson car" typed as variations
  is split there.

## Business rules

1. **Nothing in the bar creates a class.** A test asserts that no control calls
   `addPhrase` with a new class.
2. **The folded checks keep their behaviour** from docs 105 and 108; only where they are
   shown changes.
3. **Existing data stays valid:** sub-phrase links and picture checks from Wave 14 are
   read and trained on as before.

## Verified (2026-09-30)

- **Tests:**
  - `PhraseBar.test.tsx` (9):
    - no class-creating control;
    - an umbrella over ticked classes (and "tick two");
    - no umbrella with a single class;
    - keys dead while folded and working once open;
    - Mark the rest with the checks;
    - the help;
    - umbrella and older sub-phrase rows with Delete;
    - saving a look-alike.
  - The German smoke test was updated. Frontend: 1076 green; tsc clean.
- **Running app, German:**
  - The chips read "blob 61 · ring 139 · shape 200". The umbrella chip is dashed, titled
    "Oberbegriff über blob, ring".
  - The umbrella was added through the form. The class ticks at first sat far from their
    names, because they inherited the name field's 16 rem width; fixed in `phrases.css`.
  - Manage phrases lists blob (the class's own phrase, no Delete), ring, and shape (with
    its members). The test umbrella was deleted afterwards.
- **Removed:** `AddPhraseForm`, `SelectedPhrases`, and doc 105's per-outline helpers in
  `phraseEdit` (only `phraseKey` remains), together with their catalogue keys.

## Bugs

(none yet)
