---
id: dinotraining-wave-13
title: "Wave 13: Every Training Knob, Explained, and Default Recipes"
initiative: dinotraining
initiative_version: 12
status: planned
depends_on: dinotraining-wave-12
demo_state: "In Training, every model shows all the parameters the backend honours, each as 'Plain name (technical term)' with a ? giving a short explanation and a good default, grouped Basic/Advanced with a reset. A user who starts without a recipe is told what a recipe is and where it is made, and creates the model's default recipe in one click. An assistant gets the same parameters and creates the same default recipe over MCP."
created: 2026-09-30
hash: 1e5a0615
---

# Wave 13: Every Training Knob, Explained, and Default Recipes

**Jan's request (2026-09-30), after testing Waves 10–12.** He wants:
- **Parameters:** every training and fine-tuning parameter of each model, named like
  "Rounds (epochs)" and each with a **?** that gives a short explanation and a good
  default;
- **Default recipes:** a default recipe per model, with an explanation of what a recipe is
  and where it is made, so that people who "just start" are led back to the right place.

**The plan became three waves, at Jan's request (2026-09-30):**
- **13:** this wave, training;
- **14:** annotating for the model (phrases, hard negatives, mask editing);
- **15:** the language switch, last because it touches every text.

The website moves to Wave 16 (29 files retargeted, grep clean).

## What already exists (and what is missing)

- **The head form** shows only epochs, learning rate and patience. The backend's
  `TrainingRequest` already takes more: batch size, weight decay, split fractions, save best
  only, augmentation and imbalance.
- **The fine-tune panel** shows only rounds, plus blocks for DINO backbones. Learning rate
  and seed are fixed in the panel.
- **Every adapter hardcodes** its optimiser settings and loss weights:
  - RF-DETR: weight decay 1e-4 and gradient clip 0.1;
  - SAM 2: focal ×20 + dice + IoU, box jitter 0.1 and at most 16 objects;
  - SAM 3: `2, 5, 2, 5, 5` and a score threshold of 0.5;
  - backbone: weight decay 0.01.
- **"Rounds (epochs)" is the only label** written in the plain-term style. There is no **?**
  component; `FieldHint` is a line of text under a field.
- **Recipes** are tied to model profiles (`prep/profiles.py`). SAM 3, the larger RF-DETR
  sizes and the DINO backbones as fine-tune targets have no profile.
- **Fine-tuning SAM 2, SAM 3 or a backbone requires a recipe** (preflight). A user without
  one is refused, with no way to get one from where they stand.

## Decisions

1. **Only parameters the backend honours are shown.** Hardcoded values become settings
   first. A knob that is displayed and then ignored is worse than none.
2. **A default recipe is per model *and* dataset.** A recipe holds the split, so it cannot
   exist without data. "Default" means the model profile's defaults applied with no
   questions asked, named "Default for <model>". It can be edited in Prepare data like any
   recipe.
3. **One catalogue, three readers:** the form, the API validation and MCP. The explanation
   text is written once.

## Demo-State

1. **Training → Fine-tune a model → SAM 2.1:**
   - Rounds (epochs), Learning rate (learning rate) and the rest are shown as "Plain name
     (technical term)".
   - Each has a **?** that opens a short explanation with the default and why.
   - *Advanced* opens the loss weights, box jitter and the rest.
   - A changed value is marked, and **Reset to defaults** restores all.
2. **The same for a DINO head,** with batch size, weight decay, early stop, keep only the
   best round, and learning-rate schedule and warm-up.
3. **Without a recipe:**
   - A card explains what a recipe is (split, classes, input size, class balance, changed
     copies), why a model trains better with one, and that recipes are made in Prepare data.
   - **Create the default recipe** makes one in a click, and the form uses it.
   - **Open Prepare data** goes there with this dataset and model preselected.
4. **The run's provenance** records every parameter, including the defaults, so a result
   can be reproduced.
5. **MCP:** `get_training_parameters("sam2.1-hiera-small")` returns the same catalogue.
   `create_default_recipe` returns a recipe id that `start_finetune` accepts.

*(Not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | parameter-catalogue | docs/99-parameter-catalogue.md | complete | — |
| 2 | parameter-form | docs/100-parameter-form.md | complete | parameter-catalogue |
| 3 | default-recipes | docs/101-default-recipes.md | planned | — |
| 4 | training-knobs-for-agents | docs/102-training-knobs-for-agents.md | planned | parameter-catalogue, default-recipes |

### Feature notes

1. **parameter-catalogue.** Each trainable model declares its parameters once:
   - key, plain name, technical term, a 1–2 sentence explanation, the default **and why**,
     the range or choices, and the level (*basic* / *advanced*);
   - served as `GET /api/v1/training/parameters/{model}` and used to validate requests
     (422 with the parameter named, never a 500).

   Adapter constants become settings, read from `FinetuneSettings.options`. Proposed per
   model:

   | Model | Basic | Advanced |
   |---|---|---|
   | DINO head | rounds (epochs), learning rate, batch size, early stop (patience) | weight decay, keep only the best round (save best only), seed, learning-rate schedule (cosine) with warm-up |
   | RF-DETR | rounds, learning rate, pictures per step (gradient accumulation) | weight decay, gradient clipping, backbone blocks to train, seed |
   | SAM 2.1 | rounds, learning rate | weight decay, loss weights (focal / dice / IoU), box jitter, max objects per picture, cache share, seed |
   | SAM 3 | rounds, learning rate | weight decay, loss weights (class / L1 / GIoU / mask / dice), evaluation score threshold, cache share, seed |
   | DINO backbone | rounds, learning rate, backbone blocks to train (unfreeze) | backbone learning-rate factor, weight decay, pictures per step, seed |

   SAM 3's negatives and SAM 2's point prompts come with Wave 14, which gives them data to
   work on.
2. **parameter-form.** One component renders a catalogue:
   - "Plain name (technical term)", followed by a **?** button;
   - the popover holds the explanation and "Default: … — because …", is keyboard-reachable,
     closes on Esc and is linked by `aria-describedby`;
   - *Advanced* is collapsed and says how many values in it are changed;
   - changed values are marked, with a reset per field and for all;
   - out-of-range input is explained at the field.

   It replaces the fields of the head form and the fine-tune panel. Its values are
   remembered per model (doc 69's store).
3. **default-recipes.**
   - `POST /api/v1/prep/recipes/default` with a model and a dataset builds a recipe from the
     profile's defaults:
     - split by the doc 84 rules;
     - fit and input size from the profile;
     - imbalance and augmentation as recommended.
   - It is idempotent: an up-to-date default for the same model and data is returned rather
     than duplicated.
   - Profiles are added for SAM 3, RF-DETR small/base and the DINO backbones, so every
     trainable model has one.
   - The **"What is a recipe?"** card appears in Training whenever no recipe is chosen (head
     and fine-tune), and in the preflight's refusal. It offers **Create the default recipe**
     and **Open Prepare data**.
4. **training-knobs-for-agents.**
   - MCP gets `get_training_parameters(model)` and `create_default_recipe(model, dataset)`.
   - `start_training` and `start_finetune` accept the catalogue's parameters.
   - The agent guide explains the defaults and says to report non-default values.

## Open Research

- **Learning-rate schedule:** cosine with warm-up is new for heads. Measure on Blood cells
  whether it helps before making it the default; it may stay off by default.
- **Gradient accumulation** for RF-DETR, which today makes one picture per step: check that
  the effective batch changes the result, and not only the speed.
