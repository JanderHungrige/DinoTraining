---
id: dinotraining-wave-14
title: "Wave 14: Annotate for the Model — Phrases, Hard Negatives, Mask Editing"
initiative: dinotraining
initiative_version: 12
status: planned
depends_on: dinotraining-wave-13
demo_state: "A user picks SAM 3 as the target in the Annotation Studio, adds phrases with comma-separated variations from a phrase bar, marks each picture 'all marked' or 'not in this picture' per phrase, and refines a mask with two SAM clicks and a brush stroke. Prepare data checks the phrase masks and saves a recipe with a Prompts section (variants, hard negatives, confusable phrases); the SAM 3 fine-tune trains only on checked pairs and reports the negatives it used."
created: 2026-09-30
hash: bb94ea67
---

# Wave 14: Annotate for the Model — Phrases, Hard Negatives, Mask Editing

**Jan's request (2026-09-30):**
- **Prepare data** has to work for boxes, instance masks and SAM 3's phrase masks, and not
  only for classification.
- **Annotation Studio:** choose what you are annotating *for*.
  - The layers a model needs become required. Other layers stay optional and are explained,
    so a box dataset can later still feed SAM.
- **Phrases:** they need an annotation practice. Variations are typed comma-separated.
- **Concepts to explain to the user:** phrase variation (2–4 help, and all synonyms are not
  needed) and hard negatives (`num_negatives`, `num_cross_negatives`).
- **Anything else** that improves training data and model quality.

**Decisions confirmed by Jan (2026-09-30):**
1. **Variations are stored once and expanded at training time.**
   - "red car, crimson car, car in red" is saved as one phrase with three variants.
   - Training expands it into three queries.
   - A corrected mask is corrected once, and instance counts stay true.
   - Export can still write separate entries.
2. **Only a checked picture/phrase pair teaches.** The states are *all marked*, *not in this
   picture* and *not checked*. Today every picture without a mask counts as a negative even
   when nobody looked, which teaches the model to miss objects.
3. **Hard negatives come in four kinds, each explained in the UI:**
   - confirmed-absent phrases (`num_cross_negatives`, default 2);
   - generic out-of-domain phrases (`num_negatives`, default 3), from a pool filtered
     against the dataset's own words;
   - confusable phrases;
   - rejected proposals.
4. **"Keep all options open" is the recommended annotation target.**

## What already exists (and what is missing)

- **Annotations:** a box or mask has one `prompt`, which is the class name and its phrase.
  There are no variants, and no picture/phrase status.
- **SAM 3 training** (`adapters/sam3.py`) uses the class names as phrases and treats every
  picture without a positive mask as "none here".
- **Prepare data:** the audit knows boxes, masks and labels (`findings._kind`), and nothing
  about phrases.
- **Studio:** masks come only from models. There is no brush, polygon or click refinement,
  and no "annotating for".

## Demo-State

1. **Studio setup → "What will this dataset train?" → Concept segmentation (SAM 3).**
   - The layers are shown as required (phrase masks, per-picture phrase status),
     recommended (boxes) and optional (picture class), one sentence each.
2. **Phrase bar:**
   - `signal, railway signal, light signal` becomes one phrase with three variants.
   - Keys 1–9 switch the active phrase.
   - One mask can carry "signal" and "red signal".
   - Per picture: "all marked" or "not in this picture".
3. **Mask editing:** a mask is refined with a positive and a negative SAM click, then a
   brush stroke, and undone once. "Masks from my boxes" turns a picture's boxes into masks
   to review.
4. **Prepare data (target SAM 3)** checks:
   - instances per phrase;
   - pictures never checked;
   - phrases without variants;
   - fragmented or leaking masks.

   The recipe's **Prompts** section holds the variants, `num_negatives`,
   `num_cross_negatives`, confusable phrases and rejected-as-negatives.
5. **Fine-tuning SAM 3 on it** reports positives and negatives per kind. Unchecked pairs are
   not used.
6. **MCP:** an assistant adds a phrase with variants and sets picture statuses.

*(Not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | phrase-data-model | docs/103-phrase-data-model.md | planned | — |
| 2 | annotation-target | docs/104-annotation-target.md | planned | phrase-data-model |
| 3 | phrase-annotation-ux | docs/105-phrase-annotation-ux.md | planned | phrase-data-model, annotation-target |
| 4 | mask-editing | docs/106-mask-editing.md | planned | annotation-target |
| 5 | task-aware-preparation | docs/107-task-aware-preparation.md | planned | phrase-data-model |
| 6 | prompts-and-hard-negatives | docs/108-prompts-and-hard-negatives.md | planned | phrase-data-model, task-aware-preparation |
| 7 | annotation-quality-aids | docs/109-annotation-quality-aids.md | planned | annotation-target |
| 8 | annotation-for-agents | docs/110-annotation-for-agents.md | planned | phrase-data-model, prompts-and-hard-negatives |

### Feature notes

1. **phrase-data-model.**
   - **Phrases:** each has an id, a text, variants, a class, and optional confusable phrases.
   - **Links:** boxes and masks link to one or more phrases, and the class name is the
     default phrase.
   - **Picture status:** each (picture, phrase) pair is *all marked* / *not in this
     picture* / *not checked*.
   - **Migration:** every class becomes a phrase, and every picture starts *not checked*.
     SAM 3 keeps its old behaviour until a dataset uses statuses, and the audit flags the
     old silent negatives.
   - **Export:** COCO writes `phrase`/`caption` per annotation; ODVG export is added.
2. **annotation-target.**
   - At setup the user picks one of: picture classifier, detector, instance segmentation
     (SAM 2), concept segmentation (SAM 3), keep all options open (recommended).
   - Each layer shows as required, recommended or optional, with a sentence.
   - A per-picture checklist shows what is missing.
   - The choice is stored with the dataset and preselects Prepare data's target.
3. **phrase-annotation-ux.**
   - **The phrase bar** shows chips with counts and variants on hover, plus "+ phrase" with
     comma variants. Keys 1–9 switch phrases.
   - **The selected mask** shows its phrases as chips that can be added or removed.
   - **Picture status** is set per phrase, and a key moves on to the next picture.
   - **Info cards** explain phrase variation and hard negatives.
4. **mask-editing.**
   - SAM 2 click refinement: the mask's box plus positive and negative points.
   - A brush and an eraser, and undo.
   - "Masks from my boxes" for a picture or a dataset, whose results are proposals to review.
   - Must be verified in the desktop app (WebKit canvas dithering, memory
     `dinotraining-webkit-canvas-data`).
5. **task-aware-preparation.** The checklist follows the target:
   - **labels:** one class per picture;
   - **boxes:** size against the input, which exists already;
   - **instance masks:** fragments, holes, leaks outside the box, overlaps, masks per class;
   - **phrase masks:** instances per phrase, unchecked pictures, phrases without variants,
     negatives coverage, phrases too generic.

   Steps that do not apply are hidden, and each says why.
6. **prompts-and-hard-negatives.**
   - **The recipe's Prompts section:** variants, variant sampling, `num_negatives` and its
     pool, `num_cross_negatives`, confusable phrases, rejected-as-negatives.
   - **SAM 3 adapter:** trains on these, uses only checked pairs, and reports counts per
     kind.
   - **SAM 2 learns point prompts beside box prompts**, so a fine-tuned SAM 2 still answers
     clicks.
   - **Wave 13's parameter catalogue** gains these parameters.
7. **annotation-quality-aids.**
   - **A written guideline per dataset:** a convention per class or phrase, shown beside the
     canvas, exported, and read over MCP.
   - **A second-look review** of a random 5 % sample, reporting the disagreement rate.
   - **Video consistency:** the same object labelled differently in adjacent frames is
     flagged.
   - **"Unclear"** is honoured by the phrase status and the SAM 3 loss.
8. **annotation-for-agents.**
   - Tools: `add_phrase`, `set_phrase_status`, `get_annotation_guideline` and
     `set_annotation_guideline`.
   - A guide section on annotating for SAM 3, with the negatives explained.

## Open Research

- **Negatives in our loss:** what `num_negatives` / `num_cross_negatives` do in DETR-decoder
  training, measured on the filled-ring set with the defaults and with 0/0.
- **Phrase variation:** does training on 2–4 variants help when the prompt is an unseen
  synonym? This needs a held-out synonym test.

**Sources:**
- SAM3_LoRA's `num_negatives` / `num_cross_negatives` (github.com/Sompote/sam3_lora);
- the SAM 3 paper's SA-Co hard negatives (arXiv 2511.16719).
