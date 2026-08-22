---
id: 29-generated-dataset-writer
title: Generated Dataset Writer — Reviewed Annotations, Traceable to What Made Them
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [22-mask-dataset-store, 26-generator-review-ui, 28-mask-review-ui]
relates: [03-dataset-store, 25-expert-annotator, 27-grounded-sam-annotator]
source_files:
  - backend/app/datasets/producers.py
  - backend/app/datasets/schema.py
  - backend/app/datasets/migrations.py
  - backend/app/datasets/models.py
  - backend/app/datasets/store.py
  - backend/app/datasets/masks.py
  - backend/app/ml/annotators/expert.py
  - backend/app/api/v1/generate.py
  - apps/frontend/src/api/datasets.ts
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/components/CounterBar.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
routes:
  - PUT /api/v1/datasets/{dataset_id}/images
  - PUT /api/v1/datasets/{dataset_id}/images/masks
models:
  - boxes
  - masks
test_files:
  - backend/tests/test_migrations_v5.py
  - backend/tests/test_migrations_v5_fixtures.py
  - apps/frontend/src/tabs/DatasetGeneratorTab.test.tsx
  - apps/frontend/src/components/GeneratorSetup.test.tsx
data_flow: writes-existing
last_synced: 2026-08-19
status: complete
phase: all
mdd_version: 11
tags: [provenance, traceability, dataset-writer, flywheel, migrations, coco]
path: Dataset Generator/Save
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "**Fixed 2026-08-20 (doc 31).** `saveImageBoxes` spread a `CanvasBox` straight into the request body, so a box's class went out as `text` — the canvas's name for it — while the store calls it `prompt`. Pydantic drops unknown fields silently, so the save succeeded, the counters were right, and the class name was simply gone. Wave 1 never noticed: the Studio also sends an image-level `prompt` that `replace_image_boxes` falls back to. The Dataset Generator sends none — it ran a head, not a phrase — so **every generated box lost its class**, and since the trainer derives its vocabulary from `prompt`, re-training on a generated dataset would have collapsed all classes into the `object` fallback. That is the flywheel this wave exists to close, silently broken. Pinned by `src/api/datasets.save.test.ts`."
  - "Dataset lineage — a parent-dataset link and generation timestamp — was considered and not built. Per-annotation provenance answers 'which model made this'; lineage answers 'which dataset was this generated from', which only becomes useful once datasets are routinely generated from other datasets. Revisit when that happens."
security_read_sites: []
---

# 29 — Generated Dataset Writer

## Purpose

Reviewed proposals are written back into a dataset, tagged with what produced them. This
closes the annotate → train → infer → generate loop the initiative is built around: the
output of this feature is the input to Wave 2's trainer.

## The decision the wave doc deferred

Wave 4's Open Research said the lineage question *"affects the manifest `version: 2` schema,
so settle it during feature 1 rather than after"*. **It was not settled during feature 1** —
that feature shipped with the manifest still at `version: 1` — so the debt came due here.

Settled: **per-annotation provenance**, not per-dataset lineage.

A `producer` column on `boxes` and `masks` holds a JSON snapshot:

```json
{"id": "grounded-sam", "label": "Grounded SAM (Grounding DINO + SAM 2.1)", "concept": "a red circle"}
{"id": "08ab5460…", "label": "Bolt finder · Object detection · 2 classes"}
```

Three properties made this the right unit:

- **A dataset can mix producers.** Two heads run into one dataset collapse to an unusable
  list under per-dataset lineage; per annotation, each row says which one made it.
- **It is a snapshot, not a foreign key.** A head can be deleted, and "which model made this
  annotation" is exactly the question asked of an *old* dataset. A reference would dangle
  precisely when it mattered.
- **`provenance` and `producer` are different questions.** `provenance` is the *kind*
  (`expert-head`, `grounded-sam`); `producer` is *which*. Neither is derivable from the
  other.

Dataset lineage was not built — see `known_issues`.

## Migration v5 is a different shape

v3 and v4 changed a CHECK constraint, which SQLite cannot alter, so both rebuilt the table.
v5 **adds a nullable column**, which SQLite *can* do in place — so it is an `ALTER TABLE`,
and much cheaper. The runner now handles both kinds, each driven by what is actually on
disk: `sqlite_master.sql` for the constraint, `PRAGMA table_info` for the columns.

One trap this exposed. `_rebuild_table` copies a fixed column list, and that list now
includes `producer` — so a rebuild running on a *pre-v5* database would fail with
`no such column`, **in the middle of a migration**, which is the worst place to fail. The
carried columns are now intersected with what the source table actually has.

Verified against a copy of the real database, WAL included: `user_version` 4 → 5, `producer`
present on both tables, every row preserved, `foreign_key_check` clean, re-run idempotent.

## Saving masks without putting the RLE in the UI

The review type deliberately carries the **PNG preview**, not the RLE: one is for drawing,
the other for storing, and a component holding both is a component tempted to decode one to
render the other.

So `saveImageMasks` takes the original proposal response *and* the reviewed masks, pairing
them **by index** — `toReviewMasks` maps one-to-one, so the orders match by construction. The
verdict is the reviewer's; everything else is returned to the server exactly as it was sent.
A length mismatch rejects rather than saving, because pairing a verdict to the wrong mask is
a silent mislabel, which is worse than refusing.

## Two frontend types had drifted

Both are hand-maintained mirrors of backend shapes, and neither failed until something
assigned to it:

- **`DatasetCounts` had no `masks`** — added by the backend in feature 1, never mirrored.
  The counter bar now shows it, and only when non-zero so a box-only session is unchanged.
- **`Provenance`** was fixed in feature 5 for the same reason.

Worth noting as a class: every hand-mirrored literal type is a silent drift waiting to
happen, and `tsc` only catches it at the assignment.

## Verified end to end

Through the browser, against real Grounding DINO + SAM 2.1 on MPS, writing to the **real**
database:

1. Created a new dataset from the setup form
2. Proposed masks for `"a red circle. a blue square."`
3. Rejected the second mask
4. Saved

What landed:

```
positive  grounded-sam  'a red circle'   score=0.880  181x181
    producer: id='grounded-sam' label='Grounded SAM (Grounding DINO + SAM 2.1)' concept='a red circle'
negative  grounded-sam  'a blue square'  score=0.820  161x161
    producer: id='grounded-sam' label='Grounded SAM (Grounding DINO + SAM 2.1)' concept='a blue square'
```

Counters read `images=1 masks=2 positive=1 negative=1`, and the COCO export emitted **one**
annotation — the rejected mask excluded, as the positives-only rule requires.

## A test that lied, and why

`saves the reviewer verdict, not the proposed one` failed while the feature worked. The
cause was **test pollution**, not the product: `afterEach` called `vi.restoreAllMocks()`,
which undoes spies but leaves the call history of `vi.fn()` mocks intact — so
`mock.calls[0]` belonged to an *earlier* test, where the verdict was still positive.

Both `clearAllMocks` and `restoreAllMocks` now run. The failure was worth chasing: it
looked exactly like the bug it was named for.

## Known Issues

See frontmatter: dataset lineage was considered and deliberately not built.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
