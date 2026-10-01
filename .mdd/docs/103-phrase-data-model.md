---
id: 103-phrase-data-model
title: Phrase Data Model — Phrases with Variants, Masks Linked to Them, and a Status per Picture
edition: DinoTraining
depends_on: [22-mask-dataset-store, 60-dataset-classes, 96-sam3-finetune]
relates: [105-phrase-annotation-ux, 107-task-aware-preparation, 108-prompts-and-hard-negatives, 110-annotation-for-agents]
source_files:
  - backend/app/datasets/schema.py
  - backend/app/datasets/phrases.py
  - backend/app/datasets/phrase_links.py
  - backend/app/datasets/phrase_status.py
  - backend/app/datasets/masks.py
  - backend/app/datasets/models.py
  - backend/app/datasets/coco.py
  - backend/app/api/v1/dataset_phrases.py
  - backend/app/api/v1/dataset_image_masks.py
  - backend/app/api/v1/router.py
routes:
  - GET /api/v1/datasets/{dataset_id}/phrases
  - POST /api/v1/datasets/{dataset_id}/phrases
  - PATCH /api/v1/datasets/{dataset_id}/phrases/{phrase_id}
  - DELETE /api/v1/datasets/{dataset_id}/phrases/{phrase_id}
  - GET /api/v1/datasets/{dataset_id}/images/phrase-status
  - PUT /api/v1/datasets/{dataset_id}/images/phrase-status
models:
  - phrases
  - mask_phrases
  - image_phrase_status
test_files:
  - backend/tests/test_phrases.py
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [phrases, sam3, concept-segmentation, variants, hard-negatives, dataset-store, sqlite]
path: Datasets/Phrases
initiative: dinotraining
wave: dinotraining-wave-14
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Boxes do not link to phrases. SAM 3 trains on masks, and a box becomes a mask through 'Masks from my boxes' (doc 106), which carries its class as the default phrase."
security_read_sites: []
sister_projects: []
---

# 103 — Phrase Data Model

## Purpose

SAM 3 finds "every *X*" for a noun phrase *X*. Until now a mask had one `prompt`, its class
name, and that was its phrase. Three things Jan asked for (2026-09-30) cannot be said with
that alone:

1. **Variations.** "railway signal", "light signal" and "signal" are one concept, and
   training on 2–4 wordings helps SAM 3 answer the ones nobody typed.
2. **Several phrases per mask.** One mask can answer to "car" and to "red car" (nested
   concepts).
3. **Whether a picture was checked.** For a phrase, a picture is either *all marked* (every
   instance has a mask) or *not in this picture* (a confirmed negative), or nobody looked.
   SAM 3 training so far treated "no mask" as "none here", which is a false negative
   whenever the annotator simply had not got to it.

## Decision (confirmed by Jan): variants stored once, expanded at training

`red car, crimson car, car in red` typed in one field is saved as **one phrase** with text
"red car" and variants `["crimson car", "car in red"]`.
- **Training** expands the variants into separate queries (doc 108).
- **Why not copies:**
  - a corrected mask is corrected once;
  - instance counts stay true for the "50 per class" rule;
  - the audit can tell a variant from a different concept.

## Data Model (new tables; `CREATE TABLE IF NOT EXISTS` reaches every install)

```sql
phrases (id, dataset_id → datasets CASCADE, text, class_name,
         variants TEXT JSON '[]', confusable TEXT JSON '[]', created_at,
         UNIQUE(dataset_id, text))
mask_phrases (mask_id → masks CASCADE, phrase_id → phrases CASCADE, PK(mask_id, phrase_id))
image_phrase_status (image_id → images CASCADE, phrase_id → phrases CASCADE,
                     status CHECK IN ('complete','absent'), PK(image_id, phrase_id))
```

- **Text:** a phrase's text is normalised like a class name (lower case, spaces collapsed, a
  trailing full stop dropped), so "Red Car." and "red car" are one phrase.
- **Not checked** is no row: nothing to migrate, and a new phrase starts unchecked
  everywhere.
- **Class names are phrases:** a class's own name is its default phrase. `GET /phrases`
  lists every class as a phrase even without a row, and a row is created on first use.
  Existing datasets need no migration.
- **Implicit links:** a mask with no links answers to its class name. The read path reports
  it that way.

## Write path

`PUT /datasets/{id}/images` replaces an image's masks (and so, by cascade, their links).
Links travel with the masks:
- **Each mask's `phrases`** (optional, a list of texts) is linked after the insert, creating
  missing phrases under the mask's class.
- **An empty `phrases`** means "just its class", and nothing is stored for it.

Picture statuses do **not** travel with the image write. They are a separate `PUT`, so a
re-save of masks never clears "I checked this for *signal*".

## API

| Route | Does |
|---|---|
| `GET /datasets/{id}/phrases` | Every phrase with `id` (null for an implicit class phrase), `text`, `class_name`, `variants`, `confusable`, `instances` (masks answering to it, implicit links included), `complete` and `absent` (picture counts) |
| `POST /datasets/{id}/phrases` `{text, class_name?}` | Comma input → text + variants. An existing phrase gains the new variants (merge, not 409). `class_name` defaults to the first text. |
| `PATCH /datasets/{id}/phrases/{pid}` `{variants?, confusable?, class_name?}` | Replace the lists or re-home the phrase |
| `DELETE /datasets/{id}/phrases/{pid}` | Removes the phrase, its links and statuses; masks keep their class |
| `GET /datasets/{id}/images/phrase-status?path=` | `[{phrase_id, text, status}]` for one picture |
| `PUT /datasets/{id}/images/phrase-status` `{path, phrase, status}` | `status`: `complete`, `absent`, or null to clear. `phrase` is text, so an implicit class phrase can be checked before it has a row. |

**Stored masks** (`GET …/images/masks`) carry `phrases` (texts, implicit ones included).

**COCO export:** each mask annotation carries `phrase` (its first phrase) and `phrases` (all
of them, variants expanded under `variants`). That is the per-segment field SAM 3
fine-tuning tools read first.

## Business Rules

1. **A phrase belongs to one class.** Linking a mask of class *A* to a phrase of class *B*
   is refused with a 422, because that is a labelling mistake.
2. **A variant is never also another phrase's text** in the same dataset. It would
   train one wording as two concepts; refused with a 422 naming both.
3. **The empty phrase is refused** (422).
4. **Deleting a class's own phrase row only resets it** to the implicit phrase (no variants).
   The class still exists and still answers to its name.

## Verified (2026-09-30)

- **Tests:** backend 1738 green (13 new); ruff and mypy app are clean.
- **Live, on "Wave 12 filled-ring convention" (masks saved before phrases existed):**
  - `GET /phrases` listed `blob` (61 instances) and `ring` (139) as implicit class phrases,
    with no migration.
  - Stored masks carried `phrases: ["ring"]`.
  - Marking a picture *complete* for "ring" created the phrase row and counted
    `complete: 1`. Clearing it again left the dataset as it was.

## Bugs

(none yet)
