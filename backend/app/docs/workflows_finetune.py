"""The guide's fine-tuning recipe (docs 92–98), apart from `workflows.py` for its size."""

from __future__ import annotations

FINETUNE = """## 4. Fine-tune a foundation model — RF-DETR, SAM 2, SAM 3 or a DINO backbone

This adapts a whole model to the user's data rather than fitting a head on frozen
features. Slower, and often much stronger: on Blood cells with a leak-free split, RF-DETR
reached **0.62 test mAP** after 2 rounds against **0.41** for a DINO detector head.

**1. Read what the model needs, and tell the user.** Each model needs its data in a
particular form, and this is the part people get wrong:

```
GET /finetune/requirements              # every model
GET /finetune/requirements/{finetune_id}
```

Relay `data_format` as it is. In short:
- RF-DETR wants boxes;
- SAM 2 wants one outline per object;
- SAM 3 wants outlines named by a noun phrase (name classes the way you would ask for
  them);
- DINO backbones want one class per image, or outlines.

**2. Check the dataset before starting.** A recipe (section 2c) is required for SAM and
DINO models.

```
POST /finetune/check {"finetune_id": "sam2.1-hiera-small", "dataset_id": "...", "recipe_id": "..."}
```

Every failed rule comes with its `fix`. Do not start until `ready` is true.

**3. Start, and poll.**

```
POST /finetune/jobs
{"finetune_id": "sam2.1-hiera-small", "dataset_ids": ["..."], "name": "My SAM",
 "recipe_id": "...", "epochs": 6, "learning_rate": 0.0001}
GET  /finetune/jobs/{job_id}             # poll until state != "running"
```

For DINO backbones add `"options": {"unfreeze_blocks": 4}` and use a learning rate of
0.001.

**4. Report both numbers.** A finished job has `baseline_metrics` (the model before) and
`final_metrics` (after), on the same held-out pictures. **If no round beat the base
model, nothing is saved** and `notes` says so. That is a result, not an error.

Measured here:
- SAM 2 on shapes it already outlined well got *worse* (0.957 → 0.936), so nothing would
  be saved now;
- on a convention it could not know, outlining rings *with* their hole, it went 0.804 →
  **0.957**.

Fine-tuning teaches a model the user's outlines, not what it already does.

**Where the result appears** (`GET /foundation`), runnable like any model:
- a fine-tuned SAM 2 as "Grounded SAM · <name>";
- a fine-tuned SAM 3 as "SAM 3 · <name>";
- a DINO backbone variant as a segmentation or classification model with its own head.
"""
