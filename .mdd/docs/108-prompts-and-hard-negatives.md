---
id: 108-prompts-and-hard-negatives
title: Prompts and Hard Negatives — SAM 3 Trains on Checked Pairs, Variations and Four Kinds of Negatives
edition: DinoTraining
depends_on: [96-sam3-finetune, 103-phrase-data-model, 99-parameter-catalogue, 107-task-aware-preparation]
relates: [105-phrase-annotation-ux, 110-annotation-for-agents, 94-sam2-finetune]
source_files:
  - backend/app/finetune/phrase_data.py
  - backend/app/finetune/adapters/sam3_queries.py
  - backend/app/finetune/adapters/sam3.py
  - backend/app/finetune/adapters/sam2.py
  - backend/app/finetune/adapter.py
  - backend/app/finetune/data.py
  - backend/app/finetune/runner.py
  - backend/app/params/sam.py
  - backend/app/prep/recipe.py
routes: []
models: []
test_files:
  - backend/tests/test_sam3_queries.py
  - backend/tests/test_finetune_sam2.py
  - backend/tests/test_parameter_catalogue.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [sam3, fine-tuning, hard-negatives, phrases, variants, num_negatives, num_cross_negatives, sam2, point-prompts]
path: Training/Fine-tuning/SAM 3 prompts
initiative: dinotraining
wave: dinotraining-wave-14
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "SAM 3 fine-tuning has not yet improved a model: the first runs ever to complete (2026-09-30, filled-ring set, one round) fell from 0.508 to 0.193 validation mIoU at the default learning rate 1e-4, and to 0.160 without generic negatives. The base-kept guard saved nothing, correctly. The learning rate is under test (see Verified)."
  - "A class renamed by a recipe's class map keeps its picture checks under the old name; checks are matched by phrase text."
  - "Generic and confusable negatives assume the concept is not in the picture. A street lamp listed as 'not to be confused with' a signal is wrongly a negative on a picture that also shows a street lamp; the help text says to list look-alikes that rarely share a picture."
security_read_sites: []
sister_projects: []
---

# 108 — Prompts and Hard Negatives

## Purpose

Wave 14's training half:
- SAM 3 learns from the phrases, variations, picture checks and look-alikes of docs
  103–105;
- the negatives Jan named (`num_negatives`, `num_cross_negatives`) become settings with a
  **?**, next to the other SAM 3 settings (doc 99).

## Two modes, decided per dataset

**Legacy (no picture has any check):**
- The behaviour before this doc: every class phrase is asked on every picture, and one
  without outlines teaches "none here".
- The audit says so (doc 107's `unchecked-pictures`).

**Checked (at least one check exists):** only checked pairs teach.

| Pair (picture, phrase) | Query |
|---|---|
| marked *all marked* | positive: the outlines answering to the phrase |
| marked *not in this picture* | negative (explicit) |
| not checked, but ≥ 1 **rejected** outline of that phrase and no accepted one | negative (rejected), when `rejected_as_negatives` is on |
| not checked otherwise | **skipped**: an unannotated instance is not "none here" |

An outline answers to its class name and to its linked phrases (doc 103). Nested concepts
work: a "red car" outline is also a "car".

## Wordings

A pair's query text is its phrase, or one of its variations, picked at random each round.
- **`all_variations` on:** every wording becomes its own query each round. That is more
  steps, and closer to SAM3_LoRA's per-segment captions.
- **Evaluation** always uses the phrase itself, so base and fine-tuned models are compared
  on the same words.

## Negatives

- **Cross negatives (`num_cross_negatives`, default 2):**
  - **Where they come from:** in legacy mode, the absent class phrases; in checked mode,
    the explicit *not in this picture* pairs.
  - **How many:** SAM3_LoRA's rule — all of them while the dataset has ≤ 50 phrases, else
    `num_cross_negatives` sampled per picture and round.
- **Generic negatives (`num_negatives`, default 3):**
  - Unrelated everyday phrases (car, person, dog, …), each a "none here" query, sampled per
    picture and round.
  - The pool drops any concept sharing a word with a phrase, variation or look-alike of the
    dataset. The pool has 40 phrases; 0 disables generic negatives.
- **Confusable (from Manage phrases):** on a picture *all marked* for phrase P, each of P's
  look-alikes is a "none here" query. It teaches that the outlines found here are not a
  street lamp.
- **Rejected:** see the table above.

**The job reports** what it trained on, e.g. *"SAM 3 trained on 70 positive queries and 212
negatives per round: 140 generic, 0 cross, 0 confusable, 2 rejected."*

## SAM 2: point prompts

- **What:** SAM 2 fine-tuning also learns clicks, so a fine-tuned SAM 2 still answers the
  Studio's ⊕/⊖ (doc 106).
- **How:** in half the steps each object's box comes with `point_prompts` positive points,
  sampled inside its outline (default 1; 0 is the old box-only training).
- **Evaluation** stays box-only, to compare with before.

## Settings (added to doc 99's catalogue, all with a ?)

| Family | Setting | Default |
|---|---|---|
| SAM 3 | Generic negatives (`num_negatives`) | 3 |
| SAM 3 | Cross negatives (`num_cross_negatives`) | 2 |
| SAM 3 | Every wording each round (all variations) | off |
| SAM 3 | Rejected outlines as negatives | on |
| SAM 2.1 | Click prompts per object (point prompts) | 1 |

**Why settings and not recipe fields:** they say how training *uses* the data, beside the
loss weights with their explanations. The recipe keeps the data definition: `prompts`, a
snapshot of the phrases with their variations and look-alikes when saved, as provenance.

## Found while verifying: two replacements that never landed

- **Catalogue keys:** the SAM 3 settings were added with a text replacement that no longer
  matched, because ruff had reformatted the line. The first live job failed after 21 s with
  a bare `KeyError: 'num_negatives'`.
  - A test now builds every adapter's settings from an empty `FinetuneSettings`, so a key
    read but not declared fails in the suite, not in a job.
- **The frame rule** (doc 109) had the same cause, and its unit test caught it.

## Verified (2026-09-30)

- **Tests:** backend 1784 green; 15 on the query plan cover legacy and checked mode,
  each negative kind, wordings, the cap above 50 phrases, SAM 2 clicks, and unclear.
- **SAM 2.1 with click prompts**, one round on "Wave 12 filled-ring convention": 0.804 →
  **0.955** held-out mIoU. Wave 12's box-only training took six rounds to reach 0.957.
  The test model was deleted.
- **SAM 3 end to end** (legacy mode, the dataset has no checks), one round each:

  | Run | Queries per round | Validation mIoU, base 0.508 | Time |
  |---|---|---|---|
  | defaults (3 generic, 2 cross) | 76 positive, 169 negative (22 cross, 147 generic) | 0.193 | 651 s |
  | `num_negatives` 0 | 76 positive, 22 negative | 0.160 | 565 s |

  - Both kept the base model and saved nothing. The job note reported the queries as
    specified.
  - **Conclusion:** the negatives are not what hurts. Fine-tuning SAM 3's decoders at 1e-4
    does, in one round, on 49 pictures. This is the first SAM 3 run ever to complete (doc
    96 had none).

## Bugs

(none yet)
