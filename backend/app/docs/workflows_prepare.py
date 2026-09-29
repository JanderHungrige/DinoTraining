"""The guide's "prepare before you train" recipe (doc 91), apart from `workflows.py` for
the 300-line rule. Same voice: numbered steps, real calls, the trap beside its step."""

from __future__ import annotations

PREPARE = """## 2c. Prepare the data before you train — do not skip this

Most training runs that disappoint fail here, not in training: frames of one video on both
sides of the split (the score measures memory), objects shrunk to two pixels at the model's
input (it cannot learn them), a class with three examples. The app checks all of this; an
assistant that trains straight away skips it. The MCP tools for this are `audit_dataset`,
`fix_dataset`, `split_dataset`, `plan_preparation`, `save_recipe` and `list_recipes`.

0. **Importing a published dataset? Check it first.** `POST /datasets/import/coco/inspect`
   with `{"directory": ...}` writes nothing and says how the boxes are written
   (`convention`), which class names look like one class spelled twice, and whether it ships
   a split. Pass `box_convention`, `class_map` (after asking) and `keep_source_split` to
   `POST /datasets/import/coco`. Measured here: an xyxy export imported unchecked lost 162
   of 273 boxes without an error.
1. **Audit, for the model you will train.** `POST /datasets/{id}/audit` with
   `{"target": "rf-detr-nano"}` (targets: `GET /prep/targets`). It is a job: poll
   `GET /prep/audits/{job_id}`. Tell the user every finding of severity `problem` in its
   own words — `what`, `why`, `action` — and show the `examples` paths for anything a person
   must judge (blur, lighting, wrong labels). **Do not judge those yourself.**
2. **Fix only what is safe, and ask first for anything else.** `POST /datasets/{id}/fixes`:
   `exclude-copies` and `exclude-unreadable` are safe. Merging or dropping classes
   (`set-class-map`) is the user's knowledge — ask. Nothing is deleted; everything can be
   undone. **After any fix, audit again**: a recipe refuses data that changed since its audit.
3. **Split.** `POST /datasets/{id}/split` with `{}`. Scenes and stretches of video stay on
   one side; frames at a boundary are set aside. **Never split video frames at random
   yourself** — measured here, that inflated mAP by 42%. Report the `warnings`: a class
   missing from `test` cannot be scored.
4. **See what the model will see.** `GET /datasets/{id}/input-plan?target=...`. If
   `tiling.recommended` is true, the objects are too small at the whole picture's scale;
   the recipe will train on tiles, and the trained head must then be run with `tiles`
   (section 5).
5. **Save a recipe.** `POST /datasets/{id}/recipes` with `name`, `target`, and optionally
   `imbalance` and `augmentation` (`GET .../balance` and `GET .../augmentation` give the
   recommendations and the reasons). A 409 names the missing step.
6. **Train with it.** Pass `recipe_id` to `POST /training/jobs` or
   `POST /foundation/finetune` (one dataset per run). The job then reports `test_metrics`:
   the best weights scored on pictures that neither trained the model nor chose the best
   round. **Report that number** — it is the honest one, and usually lower than
   `best_metric`. A 409 means the recipe is out of date: the reason says what changed.
"""
