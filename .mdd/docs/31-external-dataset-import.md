---
id: 31-external-dataset-import
title: External Dataset Import — A Third-Party COCO Dataset, Honestly Labelled
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [03-dataset-store, 22-mask-dataset-store]
relates: [11-training-job-runner, 25-expert-annotator, 29-generated-dataset-writer]
source_files:
  - backend/app/datasets/coco_import.py
  - backend/app/datasets/schema.py
  - backend/app/datasets/migrations.py
  - backend/app/datasets/models.py
  - backend/app/api/v1/datasets.py
  - backend/app/ml/heads/decode.py
  - apps/frontend/src/types/annotation.ts
  - apps/frontend/src/api/datasets.ts
routes:
  - POST /api/v1/datasets/import/coco
models:
  - datasets
  - images
  - boxes
test_files:
  - backend/tests/test_coco_import.py
  - backend/tests/test_migrations_v6.py
  - backend/tests/test_migrations_v6_fixtures.py
  - backend/tests/test_datasets_import_api.py
  - backend/tests/test_head_decode.py
  - apps/frontend/src/api/datasets.save.test.ts
data_flow: .mdd/audits/flow-external-dataset-import-2026-08-20.md
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [coco-import, external-dataset, provenance, migrations, roboflow, detection, dataset-store]
path: Dataset Store/Import
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - backend/app/datasets/coco_import.py (user-supplied import directory)
known_issues:
  - "Author splits are discarded. All splits import into one dataset and the trainer re-splits by image with seed 42, so metrics here are **not** comparable to published RF100 numbers."
  - "Import is API-only — no frontend surface. The Annotation Studio has no \"import a dataset\" control yet."
  - "`iscrowd` is ignored; a crowd box imports as an ordinary positive. COCO `segmentation` polygons are ignored too, so an imported dataset trains detection only."
  - "`POST /training/jobs` accepts an unknown `dataset_id` and fails **asynchronously** with \"No positive boxes found in the selected datasets\" instead of rejecting it at submit. Honest and non-destructive — no head is created — but a typo costs a round trip through the job runner rather than a 422."
  - "Training is not reproducible run to run. `split_seed` fixes the *split*, but nothing seeds weight init or shuffling: two runs of an identical config on the blood dataset gave map 0.4042 and 0.3872. Fine for a demo, wrong for comparing two configurations, which is exactly what the Head Trainer invites. **Backlogged 2026-08-20** — see `.mdd/BACKLOG.md`, \"Reproducible training runs\"."
  - "The Dataset Generator\'s default score threshold of 0.30 is tuned for Grounding DINO, not for a freshly trained head. At 0.30 the thermal detector proposes ~20 boxes over two people; the top two are correct and the rest are low-confidence false positives. A per-head default, or a threshold seeded from the head\'s own metrics, would make the first run read far better."
sister_projects: []
---

# 31 — External Dataset Import

## Purpose

Bring a third-party object-detection dataset — the COCO directory that HuggingFace and
Roboflow exports unpack to — into the dataset store as an ordinary dataset, so it can train
a head through Wave 2 without a human drawing a single box.

This exists because the project had no way to answer "can I train on a dataset I did not
annotate here?", and because the honest answer required a new `provenance` value: the five
existing ones each name a **producer** (a person, Grounding DINO, a head, an annotator), and
none of them is true of a dataset someone else published.

## Architecture

```
<import dir>/                     POST /api/v1/datasets/import/coco
  train/                                    │
    _annotations.coco.json  ──┐             ▼
    *.jpg                     │      coco_import.read_coco_dirs()
  valid/                      │             │  category_id → name
    _annotations.coco.json  ──┼──────▶      │  bbox → Box(provenance="imported")
    *.jpg                     │             ▼
  test/                       │      DatasetStore.replace_image_boxes()  (doc 03)
    _annotations.coco.json  ──┘             │
                                            ▼
                                    an ordinary dataset — trains, exports, reviews
```

The importer produces `ImageAnnotation` values and hands them to the **existing** write
path. It does not touch SQLite itself. That is the whole point: an imported dataset must be
indistinguishable from a hand-annotated one everywhere except its provenance, so every
downstream feature — the trainer, the COCO exporter, the counters — works with no change.

**Directory scan is one level deep**, matching `list_images` (doc 17): the root itself, then
its immediate subdirectories. A recursive walk pointed at `/` would enumerate the disk.

## Data Model

No new table. One new value in an existing constraint:

| Change | Where | Kind |
|---|---|---|
| `"imported"` added to `PROVENANCE_VALUES` | `datasets/schema.py` | widened CHECK — needs a table rebuild |
| `LATEST_VERSION` 5 → 6 | `datasets/migrations.py` | version stamp |
| `"imported"` added to `Provenance` | `datasets/models.py` | pydantic Literal |
| `'imported'` added to `Provenance` | `frontend/src/types/annotation.ts` | hand-mirrored union |

**The version bump is not bookkeeping.** `run_migrations` returns early when
`PRAGMA user_version >= LATEST_VERSION`. The live database is at 5. Widening
`PROVENANCE_VALUES` without moving `LATEST_VERSION` to 6 rebuilds the CHECK on *fresh*
databases only — so the whole suite passes and the real install raises `IntegrityError` on
the first import. Doc 22 documented exactly this failure; the migration runner is generic
enough that the rebuild itself costs no new code, but the gate still has to be opened.

## API Endpoints

### `POST /api/v1/datasets/import/coco`

Creates a dataset and fills it from a COCO directory tree in one call.

**Request**
```json
{ "name": "Thermal dogs and people", "directory": "/path/to/export", "copy_images": false }
```

**Response** — `ImportResult`
```json
{
  "dataset_id": "…", "name": "…",
  "images": 203, "boxes": 449,
  "class_names": ["dog", "person"],
  "sources": ["train", "valid", "test"],
  "skipped_images": 0, "skipped_boxes": 0
}
```

**Errors**

| Case | Status |
|---|---|
| `directory` is not a folder | 422 |
| no `_annotations.coco.json` found at depth ≤ 1 | 422 |
| a COCO file is unreadable or missing `images`/`annotations`/`categories` | 422 |
| dataset name already taken | *allowed* — names are not unique in doc 03 |

Validation failures surface as 422, never 500, per the project's API rule.

## Business Rules

1. **Class identity is the category *name*, never its id.** Each annotation's `category_id`
   is resolved through the file's own `categories` list and the **name** is written to
   `Box.prompt`. The trainer derives class indices from sorted distinct prompts
   (`build_class_vocabulary`), so a COCO id never reaches the store and cannot be
   misinterpreted.

2. **No category is filtered by id.** Roboflow exports carry a placeholder category at id 0
   that no annotation references — but *only sometimes*. Of the three reference datasets,
   `thermal` and `chess` have a placeholder at 0, while `blood`'s id 0 is the real class
   `platelets`. Skipping id 0 would silently delete every platelet annotation and still
   report success. Resolving by name makes an unreferenced category cost nothing.

3. **Every imported box is `positive`.** A published detection dataset asserts presence.
   There is no third-party equivalent of Wave 1's `negative`/`unclear` verdicts, and
   inventing one would put a judgement in the store that nobody made.

4. **Images with no annotations are imported anyway.** `samples_for_task` treats a
   background image as real supervision for a detector. Dropping them would quietly change
   the dataset.

5. **A box that does not fit its image is skipped, not clamped, and counted.** Clamping
   invents a coordinate the author did not publish. The count is returned so a silently
   lossy import is visible. (All three reference datasets skip zero.)

6. **Zero-area boxes are skipped and counted.** `Box` requires `w > 0`, `h > 0`.

7. **Image dimensions come from the COCO file, not from opening the image.** The file is the
   authority the boxes were written against; if it disagrees with the pixels, the boxes are
   what is wrong, and rule 5 catches it.

8. **Splits are not preserved.** All splits import into one dataset and `TrainingConfig`
   re-splits deterministically by image. Recorded as a known issue below.

## Data Flow

See `.mdd/audits/flow-external-dataset-import-2026-08-20.md`. In short: COCO `bbox`
(`[x,y,w,h]`, absolute px, top-left) is copied verbatim into `Box` — the conventions are
identical, so there is no conversion to get wrong. `provenance` flows schema → pydantic →
API → the hand-mirrored frontend union, which Wave 4 recorded as drifting silently twice.

## Dependencies

- **03-dataset-store** — `DatasetStore.create` / `replace_image_boxes`, the `Box` model.
- **22-mask-dataset-store** — the migration runner that makes widening a CHECK affordable.

## Security

**Untrusted input:** `directory` is a user-supplied filesystem path, and the COCO JSON found
under it is third-party data.

- The path is accepted as given — this is a desktop app whose Annotation Studio already
  reads any folder the user picks (doc 17). Confinement to a sandbox would break the
  feature's only use. What is *not* permitted is unbounded traversal: the scan is one level
  deep, so pointing it at `/` enumerates a handful of directories rather than the disk.
- Image paths are taken from `file_name` and **resolved relative to the directory holding
  the COCO file**, then required to stay inside it via `ensure_within`. A crafted
  `"file_name": "../../.ssh/id_rsa"` is rejected rather than copied into the dataset when
  `copy_images` is on.
- The JSON is parsed with `json.load` — no `eval`, no pickle. Malformed structure raises
  `ValueError`, which the API maps to 422.
- Nothing from the file is logged verbatim beyond counts and class names.

## What running it found

Three datasets, three trained heads, and two bugs that no unit test could have caught —
both in code this feature only *uses*.

**1. `dense-detector` never had NMS** (recorded in doc 16). The head type has advertised
"NMS at inference" since Wave 2; the phrase existed only in its description string. One
thermal image of two people returned 32 overlapping `person` boxes. Every duplicate past
the first scores as a false positive, so it depressed `map` as much as it cluttered review:

| dataset | map before | map after | map_50 before | map_50 after |
|---|---|---|---|---|
| thermal (2 classes, 203 images) | 0.263 | **0.404** | 0.351 | **0.590** |
| blood (3 classes, 364 images) | 0.207 | **0.387** | 0.306 | **0.610** |
| chess (13 classes, 289 images) | 0.425 | **0.525** | 0.592 | **0.748** |

Same data, same training, same epochs. The existing unit test asserted *one entry per
cell* — it had encoded the bug as the contract, which is why the suite was green.

**2. Generated boxes lost their class** (recorded in doc 29). The canvas calls a box's
class `text`; the store calls it `prompt`; nothing renamed it on save, and pydantic drops
unknown fields without complaint. Wave 1 was rescued by accident — the Studio also sends an
image-level `prompt` that the backend falls back to. The Dataset Generator sends none,
because it ran a head rather than a phrase. So every generated box stored `prompt = NULL`,
and since `build_class_vocabulary` derives the vocabulary from `prompt`, re-training on a
generated dataset would have collapsed every class into the `object` fallback — the
flywheel this wave exists to close, broken in silence.

Both were found the same way: by looking at what the app actually put on screen and in the
database, not at whether the call succeeded.

## Known Issues

- **Author splits are discarded.** All splits land in one dataset and the trainer re-splits
  by image with seed 42. Metrics are therefore not comparable to published RF100 numbers.
- **No frontend surface.** Import is API-only in this feature; the Annotation Studio has no
  "import a dataset" control yet.
- **`iscrowd` is ignored.** The store has no crowd concept; a crowd box imports as an
  ordinary positive.
- **Segmentation is ignored.** COCO `segmentation` polygons are not converted to the mask
  table, so an imported dataset trains detection only.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
