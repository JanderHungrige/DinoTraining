---
id: 115-umbrella-terms
title: Umbrella Terms — One Phrase over Several Classes ("screw" for m8 and m9)
edition: DinoTraining
depends_on: [103-phrase-data-model, 108-prompts-and-hard-negatives]
relates: [116-phrase-bar-slim, 117-saved-means-complete, 110-annotation-for-agents]
source_files:
  - backend/app/datasets/schema.py
  - backend/app/datasets/phrases.py
  - backend/app/datasets/phrase_links.py
  - backend/app/datasets/umbrella.py
  - backend/app/api/v1/dataset_phrases.py
  - backend/app/finetune/phrase_data.py
  - backend/app/finetune/adapters/sam3_queries.py
  - backend/app/prep/recipe.py
  - backend/app/mcp/annotation_tools.py
  - backend/app/docs/workflows_annotate.py
  - backend/app/i18n/de_errors.py
  - apps/frontend/src/api/phrases.ts
routes:
  - POST /api/v1/datasets/{dataset_id}/phrases
  - PATCH /api/v1/datasets/{dataset_id}/phrases/{phrase_id}
models:
  - phrases
  - phrase_classes
test_files:
  - backend/tests/test_umbrella_terms.py
  - backend/tests/test_sam3_queries.py
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [phrases, sam3, umbrella-terms, hierarchy, hard-negatives]
path: Datasets/Phrases/Umbrella
initiative: dinotraining
wave: dinotraining-wave-15-5
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 115 — Umbrella Terms

## Purpose

- **Jan's example:** labels m8 and m9, "and since both are also a screw, I would assign
  the phrase 'screw' to both labels."
- **Doc 103's limit:** a phrase belongs to exactly one class, so this could not be
  expressed.
- **What SAM 3 gains:**
  - It learns the specific concepts ("m8") and the general one ("screw") from the same
    outlines.
  - "screw" is answered by every m8 and m9 outline.
  - "m8" is answered by the m8 outlines only.

For boxes and heads nothing changes: they learn m8 and m9.

## Data

- **`phrase_classes (phrase_id, class_name)`**, a new table.
- **An umbrella term** is a `phrases` row with `class_name = ''` and two or more
  `phrase_classes` rows. The member names are stored as `phrase_key`s.
- **The umbrella's own row** keeps its variations and look-alikes as before. "screw, bolt"
  is an umbrella with a variation.
- **The members are classes**, not outlines: every outline of m8 or m9 answers to "screw",
  now and in the future. Nothing is linked per outline.

## Rules

1. **An umbrella needs at least two member classes.** With one it would be a variation;
   the refusal says so.
2. **Members must be classes of the dataset.** A name no stored class, mask or box carries
   is refused (422), naming it.
3. **The text must not already be a class, a phrase or a variation** in the dataset. One
   wording, one meaning.
4. **An umbrella is never linked to an outline** (`link_mask`). The refusal says it
   already applies to every outline of its classes.
5. **Deleting a member class** leaves the umbrella with fewer members. Below two it lists
   as it is, and the phrase bar marks it.

## API

- `POST /phrases` takes `classes: [..]` in addition to `text`; `class_name` is then
  ignored.
- `PATCH /phrases/{id}` takes `classes` to replace the members.
- `PhraseInfo` gains:
  - `classes`: the members; for an ordinary phrase, its one class;
  - `umbrella: bool`.
- An umbrella's `instances` are the members' outlines together.

## Training (`sam3_queries`)

Decided from its members' state on the picture, never guessed. A member's state is:
- **known:**
  - (a) the member is in automatic mode and the picture has no unclear outline of it; or
  - (b) the member is checked `complete` or `absent` on the picture;
- **unknown:** anything else, i.e. checked elsewhere but not here, or unclear here.

What the umbrella does on the picture:
- **Every member known and one of them present:** positive query "screw". The answers are
  the outlines of all members.
- **Every member known and none present:** a negative ("none here"), counted as `cross` in
  automatic mode and `absent` when the members were checked.
- **Any member unknown:** the umbrella is skipped on that picture. A partial answer would
  teach that the unoutlined screws are not screws.

Also:
- **An umbrella is never a cross negative** on a picture where one of its members is
  present, which follows from the above.
- **Variations and look-alikes** of the umbrella work as for any phrase.
- **The job note** counts umbrella queries under the existing kinds (positive, cross,
  absent). Their number is visible in the counts.

## Recipes and MCP

- `RecipePhrase` gains `classes`, so the recipe's provenance snapshot records the umbrella
  with its members.
- The MCP `add_phrase` tool takes `classes`. The agent guide's annotation section says
  when to use an umbrella and when a variation.

## Verified (2026-09-30)

- **Tests:**
  - `test_umbrella_terms.py` (14): storage, the counts, the refusals, replacing members,
    no link to a single outline, and the six training rules.
  - Backend: 1833 green; ruff and mypy (228 files) clean.
  - Frontend: 1084 green; the client types carry `classes` and `umbrella`.
- **Live, on the "Wave 12 filled-ring convention" dataset (restarted backend):**
  - Creating "shape, round thing" over blob and ring gave `instances: 200`, i.e. 61 blob
    and 139 ring outlines.
  - With German, one class was refused in German.
  - A dry run of the query planner on its 70 pictures gave 67 positive "shape" queries
    (all blob and ring outlines of each picture) and 3 cross negatives on pictures with
    neither.
  - The test umbrella was deleted again.
- **Dropped while building:** the check for "an umbrella over itself" could never fire.
  That text is always a class, and "already a class" answers first.

## Bugs

(none yet)
