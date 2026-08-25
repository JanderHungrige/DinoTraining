"""The recipes an agent needs, which the OpenAPI schema cannot express (doc 63).

A schema describes *shapes*. It says `POST /foundation/finetune` exists and what its body
looks like. It cannot say that the model must be installed first, that installing is a job
you poll, that `image_path` is a path on the **backend's** filesystem, or that the class of
a box is called `prompt` on the wire and `text` in the UI.

That is why this half is prose and the reference half is generated. Prose for order,
generation for surface — and the moment someone transcribes an endpoint list into here by
hand, this file has started lying.

Written for a reader that follows instructions literally, which is the whole audience:
numbered steps, real calls, and the trap named beside the step that springs it.
"""

from __future__ import annotations

BASE_URL = "http://127.0.0.1:8756/api/v1"

INTRO = f"""# DinoTraining API — a guide for an AI assistant

This app annotates images, trains models on them, and generates more annotated data with
what it trained. Everything the desktop app does, it does through this API, so anything a
person can do here you can do too.

## Before anything else

**The API is at `{BASE_URL}` and only there.** It is a local sidecar bound to loopback on
the machine the app runs on. There is no public host, no API key and no authentication —
the security model is that only this machine can reach it. If a call fails to connect, the
app is not running; start it and try again.

**Paths are the backend's paths.** Every route that takes an image or a folder takes an
**absolute path on the machine running this API**, and opens the file itself. There is no
upload. If you downloaded a dataset to `/tmp/rail`, that is what you send.

**Long work is a job, not a wait.** Downloads, training and fine-tuning return a job id
immediately. Poll the matching `GET` until `state` is no longer `running`. Nothing streams
except head training, which also offers polling.

**Errors say why.** `404` unknown id, `409` the app is in the wrong state for a coherent
request (usually: a model is not installed), `422` the request itself is malformed. Read
`error.message` — it is written for a person and it names the fix.
"""

INSTALL = """## 1. Install a model

Nothing is bundled. Weights download on demand and are cached, so this is once per model.

```
GET  /models                          # what exists, and `installed` for each
POST /models/rf-detr-nano/download    # returns { job_id }
GET  /models/jobs/{job_id}            # poll until state != "running"
```

**Which model:** `rf-detr-nano` is the general detector and the one to fine-tune. Concept
segmentation needs `grounding-dino-tiny` **and** `sam2.1-hiera-small` — both, because the
pipeline chains them. `dinov2-small` is the backbone every trained head runs on.

**Gated models refuse rather than fail.** `sam3` and the DINOv3 backbones need a HuggingFace
token and, for SAM 3, a manual access request Meta approves by hand. A download without one
comes back `409` saying so. Do not retry it; it will not become approved.
"""

DATASET_IN = """## 2. Get a dataset in

Two ways in, and they are not alternatives — they answer different situations.

### 2a. You already have annotations (COCO, Roboflow export)

```
POST /datasets/import/coco
{ "name": "Rail", "directory": "/abs/path/to/export", "copy_images": false }
```

The folder needs an annotations JSON and the images it references. A Roboflow COCO export
works as downloaded. `copy_images: true` copies them into the app's own store, which is
slower and makes the dataset self-contained; `false` references them where they are.

The response reports `skipped_images` and `skipped_boxes`. **Read them.** A silent import
that dropped half its boxes looks identical to a clean one.

### 2b. You have images and no annotations

Use a model to propose them, then save what you keep. See workflow 5 — that is the same
loop, and it is what this app is for.
"""

TRAIN_HEAD = """## 3. Train a DINO head

A *head* is a small model on top of a frozen DINOv2 backbone. It trains in minutes and
shares its backbone pass with every other head, which is what makes comparing several
cheap. It is strong at classification and segmentation and **weaker at detection** than a
fine-tuned detector — see workflow 4 if boxes are what you need.

```
GET  /head-types                      # what can be trained, and against which backbones
POST /training/jobs
{
  "head_type_id": "dense-detector",
  "backbone_id": "dinov2-small",
  "dataset_ids": ["<id from step 2>"],
  "epochs": 20,
  "learning_rate": 0.001
}
GET  /training/jobs/{job_id}          # poll until state != "running"
```

**The head type must match the data.** `linear-classifier` needs one class per image;
`dense-detector` needs boxes; `linear-segmenter` needs **masks**, which only a concept
segmenter produces (workflow 5). Training a segmenter on a box-only dataset is refused with
a message saying exactly that.

The finished run reports `head_instance_id`. That is what you run for inference.
"""

FINETUNE = """## 4. Fine-tune a detector — the strong option for boxes

This adapts a whole detector to your classes rather than fitting a head on frozen features.
Slower, and much better: measured in this app at **mAP 0.96** on rail data against
**0.5–0.6** for a DINO detector head on the same images.

```
POST /foundation/finetune
{
  "foundation_id": "rf-detr-nano",
  "dataset_ids": ["<id from step 2>"],
  "name": "Rail detector",
  "epochs": 20,
  "learning_rate": 0.0001,
  "unfreeze_blocks": 0
}
GET  /foundation/finetune/{job_id}    # poll until state != "running"
```

**Preconditions:** `rf-detr-nano` installed (step 1), and a dataset with **boxes**.

**`unfreeze_blocks`** opens the last N backbone blocks to training. Measured here: 4 blocks
cost 19% more time and moved holdout mAP 0.78 → 0.84. Almost all of that is tighter boxes,
not more detections — mAP@50 barely moved while mAP@75 rose 20%. Use it when localisation
matters; skip it otherwise.

The result is a **fine-tuned instance**, listed by `GET /foundation` alongside the base
models, and runnable exactly like one.
"""

GENERATE = """## 5. Generate a dataset with what you have

The flywheel: run a model over unannotated images, keep what is right, and the result is
the training set for the next model.

```
GET  /annotate/folder?path=/abs/path/to/images      # list the images
POST /generate/foundation                            # per image
{
  "image_path": "/abs/path/to/images/frame_001.png",
  "foundation_id": "rf-detr-nano",
  "score_threshold": 0.3
}
PUT  /datasets/{dataset_id}/images                   # save what you keep
{
  "path": "/abs/.../frame_001.png",
  "width": 2464, "height": 1600,
  "boxes": [ { "label": "positive", "provenance": "foundation-model",
               "prompt": "signal", "x": 10, "y": 20, "w": 30, "h": 40 } ]
}
```

**Three traps here, all of which have bitten this project:**

**The class is `prompt`, not `text`.** The UI calls it `text`; the store calls it `prompt`.
Send `text` and pydantic drops it silently — every box lands with a NULL class, and a model
trained on that dataset collapses every class into one. There is no error.

**`label` is a verdict, not a class.** It is `positive`, `negative` or `unclear`. A
`negative` box means "this region is *not* the thing", which is useful supervision, not a
deletion. `unclear` regions are ignored by the loss.

**A `PUT` replaces that image's whole set.** It is not an append. Send everything you want
the image to have, every time.

### Segmentation instead of boxes

Set `foundation_id` to `grounded-sam` and add a `concept` — plain text, what you are looking
for. Each proposal comes back with a `mask` alongside its box, and masks save to
`PUT /datasets/{dataset_id}/images/masks`. A mask-carrying object is stored as a mask **or**
as a box, never both: the COCO exporter emits each table separately, so storing both would
double every object in the export.

### When a head finds nothing on a big image

If a model was trained on tiled images, running it on a full frame finds nothing — and the
call *succeeds*, with an empty list. Add a grid:

```
POST /inference/compose
{ "image_path": "...", "backbone_id": "dinov2-small", "instance_ids": ["..."],
  "tiles": { "columns": 4, "rows": 3, "overlap": 0.2 } }
```

`GET /heads` reports `trained_width` per head. If the image is much wider than that, tile.
"""

EXPORT = """## 6. Get the result out

```
POST /datasets/{dataset_id}/export/coco     # writes annotations.coco.json, returns its path
GET  /datasets/{dataset_id}/folder          # where the dataset lives on disk
```

The export is standard COCO. Masks come out as `segmentation` with a `bbox` derived from
them and an `area` computed from them — so a segmented object is **one** annotation carrying
both, not two.
"""

#: The recipes, in the order someone would actually do them.
WORKFLOWS: tuple[str, ...] = (
    INTRO,
    INSTALL,
    DATASET_IN,
    TRAIN_HEAD,
    FINETUNE,
    GENERATE,
    EXPORT,
)

WORKED_EXAMPLE = """## A worked example, end to end

*"Here is a link to a dataset. Download it, fine-tune RF-DETR on it, then use it to
annotate my own images."*

1. Download and unpack the dataset yourself, to somewhere on this machine. The API does
   not fetch URLs — you have a shell and it does not.
2. `POST /models/rf-detr-nano/download`, then poll `GET /models/jobs/{job_id}`.
3. `POST /datasets/import/coco` with the unpacked directory. Keep `dataset_id`. Check
   `skipped_boxes` is 0, or say so.
4. `POST /foundation/finetune` with that `dataset_id`. Poll `GET /foundation/finetune/{id}`
   until `state` is `complete`, reporting `best_metric` as it moves.
5. `GET /annotate/folder?path=...` over the user's own images, then
   `POST /generate/foundation` per image with the fine-tuned `foundation_id` from step 4,
   and `PUT /datasets/{new_id}/images` for each result.
6. `POST /datasets/{new_id}/export/coco` and tell the user the path.

**Report the numbers, not just success.** `best_metric` after a fine-tune, and how many
boxes were proposed and kept. A run that finished and learned nothing looks exactly like a
run that worked, and only the numbers distinguish them.
"""
