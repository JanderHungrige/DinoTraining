---
id: dinotraining-wave-13
title: "Wave 13: Annotate for the Model, Train with Every Knob, in Your Language"
initiative: dinotraining
initiative_version: 11
status: planned
depends_on: dinotraining-wave-12
demo_state: "A user picks SAM 3 as the target in the Annotation Studio, adds phrases with comma-separated variations, marks each picture complete or absent per phrase and refines a mask with two clicks. Prepare data checks the phrase masks and saves a recipe with phrases and hard negatives. Training explains every SAM 3 parameter (plain name, technical term, a ? with explanation and default), creates a default recipe in one click where none exists, and fine-tunes. The whole app switches between English and German."
created: 2026-09-30
hash: b4652dc7
---

# Wave 13: Annotate for the Model, Train with Every Knob, in Your Language

**Jan's request (2026-09-30), after testing Waves 10–12:**
- **Training:**
  - a default recipe per model, plus an explanation of what a recipe is and where it is
    made, so that people who "just start" are led back to the right place;
  - every training and fine-tuning parameter of each model, named like "Rounds (epochs)",
    each with a **?** giving a short explanation and a good default.
- **Prepare data:** it has to work for boxes, instance masks and SAM 3's phrase masks, and
  not only for classification. Do text-prompted models need text in the recipe?
- **Annotation Studio:** choose what you are annotating *for*.
  - The layers a model needs become required.
  - Other layers stay optional and are explained, so a box dataset can later still feed SAM.
  - Phrases need an annotation practice: adding new ones, several per task, and variations
    typed comma-separated.
  - The user needs the concepts of phrase variation and hard negatives
    (`num_negatives`, `num_cross_negatives`) explained.
  - Anything else that improves training data and model quality.
- **Language:** a language option. English stays the base language, and German is added.

Inserted **before the website**, which moves 13 → 14 (29 files retargeted, grep clean).

## What already exists (and what is missing)

- **Parameters:**
  - The head form shows epochs, learning rate and patience.
  - The backend already takes batch size, weight decay, split fractions, augmentation and
    imbalance.
  - The fine-tune panel shows only rounds (and blocks for DINO backbones); learning rate and
    seed are fixed.
  - Every adapter hardcodes its optimiser settings and loss weights (e.g. SAM 3's
    `2, 5, 2, 5, 5`, `adapters/sam3.py:54`).
  - "Rounds (epochs)" is the only label written in the plain-term-plus-technical-term style.
  - There is no **?** component; `FieldHint` is a line of text under a field.
- **Recipes:**
  - A recipe is tied to a model profile (`prep/profiles.py`), but there is **no SAM 3
    profile**.
  - The audit knows boxes, masks and labels (`findings._kind`), and nothing about phrases.
- **Data model:**
  - A box or mask has one `prompt` (the class name), which is its phrase.
  - There are no variants, and no record of whether a picture was *checked* for a phrase.
  - SAM 3 training treats every picture without a positive mask of a phrase as "none here",
    even when nobody looked. **Such a false negative teaches the model to miss objects.**
- **Studio:**
  - Masks come only from models. There is no brush, polygon or click refinement.
  - There is no "annotating for" concept; that exists only in Prepare data.
- **Language:** every text is hardcoded English. That is about 64 of 91 components, plus
  the backend's plain-language audit, requirements and preflight texts.

## Decisions taken in planning (Jan may overrule)

1. **Phrase variations are stored once and expanded at training time.** Jan suggested
   splitting them into separate annotation entries in the backend. The recommendation is
   different:
   - **Stored:** the user types `red car, crimson car, car in red`, and that is saved as
     **one phrase with three variants**.
   - **Training:** the phrase is expanded into three queries, so each variation is its own
     training example, as Jan intends.
   - **Why not copies:**
     - a corrected mask would otherwise have to be corrected three times;
     - instance counts would be inflated threefold, which fools the "50 instances" rule;
     - the audit could no longer tell a variation from a separate concept.
   - **Export:** COCO/ODVG can still write separate entries.
2. **Only a checked picture/phrase pair teaches.** Each pair has one of three states:
   - *all marked:* the phrase is present and every instance is marked;
   - *not in this picture:* a confirmed negative;
   - *not checked:* ignored.

   This replaces today's silent "absent = negative".
3. **Hard negatives come in four kinds, all explained in the UI:**
   - absent phrases confirmed per picture, sampled by `num_cross_negatives` once there are
     many phrases;
   - generic out-of-domain phrases, set by `num_negatives`, from a pool filtered against the
     dataset's own words;
   - **confusable phrases** per phrase ("not to be confused with": *street lamp* for
     *signal*);
   - rejected proposals ("the model said *signal*, it is not").

   Defaults follow the published SAM 3 fine-tuning practice: 3 generic, 2 cross.
4. **"Keep all options open" is the recommended annotation target.** It is cheap because:
   - phrases default to the class name;
   - masks come from boxes in one click (SAM 2);
   - the picture class is derived from the boxes.
5. **Only parameters that the backend honours are shown.** Hardcoded values become settings
   first; nothing is shown as a knob that is then ignored.
6. **English is the source language.** German is the first translation. Backend texts that
   reach the UI are translated by `Accept-Language`. MCP and the agent guide stay English.

## Demo-State

1. **Annotation Studio → "What will this dataset train?" → SAM 3.**
   - The layers are shown as *required* (phrase masks, per-picture phrase status),
     *recommended* (boxes) and *optional* (picture class), each with one sentence on why.
   - The phrase bar lets the user add `signal, railway signal, light signal`, switch phrases
     with keys 1–9, and give one mask two phrases.
   - Per picture, the user marks "all marked" or "not in this picture".
   - A mask is refined with two SAM clicks (one positive, one negative) and a brush stroke.
2. **Prepare data** shows the SAM 3 checklist:
   - phrases with too few instances;
   - pictures never checked for a phrase;
   - variation counts;
   - fragmented or leaking masks.

   The recipe gains a **Prompts** section: phrases, variants, negatives and confusable
   phrases.
3. **Training → SAM 3:**
   - Every parameter is shown as "Plain name (technical term)" with a **?** giving a short
     explanation and the default.
   - The parameters are grouped *Basic* and *Advanced*, with a reset to defaults.
   - Without a recipe, a card explains what a recipe is and offers **Create the default
     recipe** or **Open Prepare data**.
4. **The header's language switch** sets the whole UI to German, including the audit's
   findings, and back.
5. **MCP:** an assistant lists the parameters of a model with their defaults and meaning,
   creates a default recipe, and adds phrases with variants to a dataset.

*(Not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | parameter-catalogue | docs/99-parameter-catalogue.md | planned | — |
| 2 | parameter-form | docs/100-parameter-form.md | planned | parameter-catalogue |
| 3 | default-recipes | docs/101-default-recipes.md | planned | — |
| 4 | phrase-data-model | docs/102-phrase-data-model.md | planned | — |
| 5 | task-aware-preparation | docs/103-task-aware-preparation.md | planned | phrase-data-model, default-recipes |
| 6 | annotation-target | docs/104-annotation-target.md | planned | phrase-data-model |
| 7 | phrase-annotation-ux | docs/105-phrase-annotation-ux.md | planned | phrase-data-model, annotation-target |
| 8 | mask-editing | docs/106-mask-editing.md | planned | annotation-target |
| 9 | prompts-and-hard-negatives | docs/107-prompts-and-hard-negatives.md | planned | phrase-data-model, task-aware-preparation, parameter-catalogue |
| 10 | annotation-quality-aids | docs/108-annotation-quality-aids.md | planned | annotation-target |
| 11 | language-switch | docs/109-language-switch.md | planned | all UI features above |
| 12 | wave-13-for-agents | docs/110-wave-13-for-agents.md | planned | 1, 3, 4, 9 |

**Build order:** 1–3 (training, quick to test), then 4–10 (annotation), then 11 last,
because it touches every text written before it.

### Feature notes

1. **parameter-catalogue.** Each trainable model declares its parameters once:
   - key, plain name, technical term, a 1–2 sentence explanation, the default **and why**,
     the range, and *basic* or *advanced*.
   - It is served as `GET /api/v1/training/parameters/{model}`, and it validates requests.
   - **Adapter constants become settings.** Proposed per model:

   | Model | Basic | Advanced |
   |---|---|---|
   | DINO head | rounds (epochs), learning rate, batch size, early stop (patience) | weight decay, keep only the best round (save best only), seed, learning-rate schedule + warm-up |
   | RF-DETR | rounds, learning rate, batch via gradient accumulation | weight decay, gradient clipping, backbone blocks to train, seed |
   | SAM 2.1 | rounds, learning rate | weight decay, loss weights (focal / dice / IoU), box jitter, point prompts per object, max objects per picture, train prompt encoder, cache share |
   | SAM 3 | rounds, learning rate, generic negatives (`num_negatives`), cross negatives (`num_cross_negatives`) | weight decay, loss weights (class / L1 / GIoU / mask / dice), parts to train, variant sampling, evaluation score threshold, cache share |
   | DINO backbone | rounds, learning rate, backbone blocks to train (unfreeze) | backbone learning-rate factor, weight decay, batch size, seed |
2. **parameter-form.**
   - One component renders a catalogue: "Plain name (technical term)", then a **?** button
     that opens a popover with the explanation and the default.
   - The popover is keyboard-reachable and uses `aria-describedby`.
   - *Advanced* is collapsed. Changed values are marked, and one click resets them to
     defaults.
   - It replaces the fields in the head form and in the fine-tune panel.
3. **default-recipes.**
   - **One click, per model and dataset.** A recipe needs a dataset (it holds the split), so
     "a default recipe per model" means: the model profile's defaults applied to the chosen
     dataset, with no questions asked. It is named "Default for <model>" and can be edited
     later in Prepare data.
   - A **"What is a recipe?"** card explains that a recipe is the saved preparation: split,
     classes, input size, class balance and changed copies. It also says why a model trains
     better with one, and that recipes are made in Prepare data.
   - The card shows in Training whenever no recipe is chosen, and in the Studio's "done"
     state.
   - Profiles are added for SAM 3, the RF-DETR sizes and the DINO backbones, so every
     fine-tunable model has one.
4. **phrase-data-model.**
   - **Phrases:** a phrase has an id, a text, variants and a class, and it can have
     confusable phrases.
   - **Links:** masks and boxes link to one or more phrases, and a class name is the default
     phrase.
   - **Picture status:** each (picture, phrase) pair has a status: all marked / not in this
     picture / not checked.
   - Migrations keep existing datasets valid: every class becomes a phrase and every
     picture starts as *not checked*. **Existing SAM 3 behaviour is kept until a dataset
     uses statuses**, and the old silent-negative behaviour is flagged by the audit.
   - COCO export writes `phrase`/`caption` per annotation; ODVG export is added.
5. **task-aware-preparation.** The checklist adapts to the recipe's target:
   - **labels:** one class per picture;
   - **boxes:** size against the input size, which exists already;
   - **instance masks:**
     - fragments, holes, a mask leaking outside its box;
     - overlapping instances;
     - masks per class;
   - **phrase masks:**
     - instances per phrase;
     - pictures never checked;
     - phrases without variants;
     - negatives coverage;
     - phrases too generic, i.e. a single word that is also another class's word.

   Steps that do not apply are hidden, and each hidden step says why.
6. **annotation-target.**
   - At session setup the user answers "What will this dataset train?":
     - picture classifier;
     - detector;
     - instance segmentation (SAM 2);
     - concept segmentation (SAM 3);
     - keep all options open (recommended).
   - Each layer is shown as required / recommended / optional, with one sentence each.
   - A per-picture checklist shows what is still missing for the chosen target.
   - The target is stored with the dataset and preselects Prepare data's target.
7. **phrase-annotation-ux.**
   - **Phrase bar** above the canvas: chips for the dataset's phrases, with the active one
     highlighted.
     - Keys 1–9 switch the active phrase.
     - A "+ phrase" field takes comma-separated variations.
     - Each chip shows its instance count and its variants on hover.
   - **Masks:** a new mask takes the active phrase. The selected mask's phrases are chips
     that can be added or removed, which allows nested concepts ("car" and "red car").
   - **Picture status per phrase:** "all marked" or "not in this picture". A key moves on to
     the next picture.
   - **Explanations:** info cards on phrase variation (2–4 variations help and all synonyms
     are not needed) and on hard negatives.
8. **mask-editing.**
   - **SAM click refinement:** a positive or negative point re-runs SAM 2 with the mask's box
     plus the points.
   - A brush and an eraser, for the last pixels.
   - "Masks from my boxes" runs SAM 2 over every box of the picture or dataset. The results
     are proposals, to be reviewed like any other.
   - Undo.
9. **prompts-and-hard-negatives.**
   - **The recipe gains a Prompts section:**
     - phrases and variants;
     - the variant sampling (all variants each round, or one at random);
     - `num_negatives` and the generic pool;
     - `num_cross_negatives`;
     - confusable phrases;
     - rejected proposals as hard negatives (on/off).
   - **The SAM 3 adapter:**
     - trains on these settings;
     - learns only from checked pairs;
     - reports how many positives and how many negatives of each kind it used.
   - **SAM 2:** point prompts join box prompts, so a fine-tuned SAM 2 still answers clicks.
10. **annotation-quality-aids.** Jan asked for other additions that improve the data:
    - **A written guideline per dataset:** a short convention per class or phrase, e.g.
      "include the pole?", "occluded > 50 % → unclear".
      - It is shown beside the canvas and exported with the dataset.
      - It is read by the assistant over MCP.
    - **A second-look review:** a random 5 % sample is shown again, and the disagreement rate
      is reported as a data-quality figure.
    - **Video consistency:** the same object with different classes or phrases in adjacent
      frames is flagged.
    - **"Unclear" everywhere:** crowds, heavy occlusion or doubt become ignore regions and
      not guesses. The Studio already has it; the phrase status and the SAM 3 loss honour it
      too.
11. **language-switch.**
    - **Frontend:** a typed string catalogue, with keys checked by TypeScript so a missing
      German key fails the build. Candidates are react-i18next or a small own module; this is
      decided in the doc.
    - **Switch and default:** in the header and in Admin. It is remembered, and it defaults
      to the OS language.
    - **Backend:** user-facing texts (audit, requirements, preflight, parameter help) come
      from catalogues and are chosen by `Accept-Language`.
    - The intro content is translated in full.
    - A test fails when a German key is missing or left in English.
12. **wave-13-for-agents.**
    - **New tools:**
      - `get_training_parameters(model)`;
      - `create_default_recipe(model, dataset)`;
      - `add_phrase(dataset, text_with_variants, class)`;
      - `set_phrase_status(image, phrase, status)`;
      - `get_annotation_guideline` / `set_annotation_guideline`.
    - The guide gains a "annotating for SAM 3" section with the negatives explained.

## Open Research

- **SAM 3 negatives in our loss:** how the published `num_negatives` / `num_cross_negatives`
  practice maps onto our DETR-decoder-only training, measured on the filled-ring set: with
  the defaults, and with 0/0.
- **Phrase variation:** does training on 2–4 variants measurably help when prompting with
  an unseen synonym? This needs a small held-out synonym test.
- **Brush on WebKit canvas:** the packaged app dithers PNG-transported data (memory
  `dinotraining-webkit-canvas-data`), so mask edits must be verified in the desktop app and
  not only in the browser.
- **i18n library:** react-i18next (mature, plural rules) against a typed own dictionary (no
  dependency, compile-time key checks).
- **Scale:** this is the largest wave so far (12 features). It can be split into 13a
  (features 1–3, 11) and 13b (4–10, 12) if Jan wants to test the training part sooner.

**Sources for the negatives practice:** SAM3_LoRA's `num_negatives` / `num_cross_negatives`
(github.com/Sompote/sam3_lora); SAM 3 paper, SA-Co hard negatives (arXiv 2511.16719).
