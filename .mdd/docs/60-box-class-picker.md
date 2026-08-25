---
id: 60-box-class-picker
title: A Class Picker for Boxes — Choose One, or Make One
edition: MDD
initiative: dinotraining
wave: unassigned
wave_status: in_progress
depends_on: [47-box-review-list, 03-dataset-store, 50-dataset-as-source]
relates: [05-annotation-canvas, 06-annotation-workflow, 31-external-dataset-import]
source_files:
  - backend/app/datasets/classes.py
  - backend/app/datasets/schema.py
  - backend/app/api/v1/dataset_classes.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/datasetClasses.ts
  - apps/frontend/src/hooks/useDatasetClasses.ts
  - apps/frontend/src/components/ClassPicker.tsx
  - apps/frontend/src/components/BoxReviewList.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/datasets/{dataset_id}/classes
  - POST /api/v1/datasets/{dataset_id}/classes
  - DELETE /api/v1/datasets/{dataset_id}/classes/{name}
models:
  - dataset_classes
test_files:
  - backend/tests/test_dataset_classes.py
  - backend/tests/test_dataset_classes_api.py
  - apps/frontend/src/components/ClassPicker.test.tsx
  - apps/frontend/src/components/BoxReviewList.test.tsx
  - apps/frontend/src/hooks/useDatasetClasses.test.ts
data_flow: .mdd/audits/flow-box-class-picker-2026-08-25.md
last_synced: 2026-08-25
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, class-vocabulary, review, dataset-store, accessibility, react, sqlite]
path: Annotation Studio/Review
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 60 — A Class Picker for Boxes

## Purpose

Give a box a class by **choosing** one, and let a class be **created** so there is
something to choose. Today the only way to name a box is to type its class into a free-text
field, once per box, with no memory of what you typed on the last one.

## The report

> "Adding a manual bounding box and choosing a label (also creating a new label to then
> choose from) does not work."

Two failures in one sentence. The first — the box could not be drawn at all — was a canvas
hit-target bug and is fixed separately. This doc is the second: there is no
*choosing*, because there is no list. There is only a text field per row, and a class that
exists only as a string typed onto a box.

Doc 47 already knew: *"Renaming is per box, not per class. Thirty boxes proposed as
`person` need thirty edits to become `pedestrian`."* That known issue is closed here.

## Why a class needs a table

A class in this project is `boxes.prompt` — a string on an annotation. That has three
consequences, all of which this feature has to answer:

1. **A class cannot exist before a box uses it.** So "create a new label to then choose
   from" is literally unrepresentable: the moment you have somewhere to put the name, you
   have already labelled something with it.
2. **`coco_import.py:227` already computes the distinct classes in a dataset** and throws
   the result away into a one-shot `ImportSummary`. Nothing persists it; nothing can query
   it.
3. Deriving the list from the boxes currently loaded would work — the dataset listing
   already carries every image's boxes — but it makes a created class **vanish on reload**
   until something is labelled with it, which is the same unrepresentable state in a
   friendlier costume.

So: a real table, and the vocabulary is the union of what is stored there and what is
already on a box.

## Data Model

```sql
CREATE TABLE IF NOT EXISTS dataset_classes (
    id         INTEGER PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (dataset_id, name)
);

CREATE INDEX IF NOT EXISTS idx_dataset_classes_dataset ON dataset_classes(dataset_id);
```

**No migration step is needed, and that is a deliberate reading rather than an oversight.**
`migrations.py` exists because `CREATE TABLE IF NOT EXISTS` is a no-op against a table that
*already exists* — it cannot widen a CHECK or add a column. A brand-new table is the one
case plain schema application handles correctly, and `get_connection` applies `schema.py`
before consulting the runner. `head_instances` (Wave 2) migrated existing installs by
exactly this route. `LATEST_VERSION` is therefore **not** bumped: it gates CHECK rebuilds,
and moving it without a corresponding step is noise that makes the next reader look for
work that was never there.

`ON DELETE CASCADE` matches every other dataset-scoped table, so deleting a dataset takes
its vocabulary with it.

## API Endpoints

All three live in a **new** router module. `api/v1/datasets.py` is at 291 lines against
the project's 300-line gate, and `datasets/store.py` at 284 — the same split
`generate_foundation.py` made from `generate.py`, for the same reason.

### `GET /api/v1/datasets/{dataset_id}/classes`

The dataset's vocabulary: every stored class, **unioned with every distinct non-null
`boxes.prompt` in that dataset**, sorted case-insensitively.

The union is what makes the feature work on a dataset that predates it. A COCO import
brings 13 chess classes in as box prompts and nothing else; without the union the picker
would open empty on a dataset visibly full of named boxes.

```json
{ "classes": [ { "name": "pedestrian", "boxes": 42, "stored": true } ] }
```

`boxes` is how many annotations currently carry the class; `stored` says whether it is in
the table or was inferred from a box. Both are for the UI's benefit — a class with 0 boxes
is one you created and have not used yet, and it should read as such rather than as an
error.

* `404` — unknown dataset.

### `POST /api/v1/datasets/{dataset_id}/classes`

```json
{ "name": "pedestrian" }
```

* `201` — created, returns the full vocabulary so the caller never has to merge.
* `200` — already present (stored *or* inferred). Idempotent by decision: two reviewers
  creating the same class is not an error, and a 409 would make the UI handle a case whose
  correct resolution is "you already have it".
* `404` — unknown dataset.
* `422` — empty, whitespace-only, or over 100 characters.

### `DELETE /api/v1/datasets/{dataset_id}/classes/{name}`

Removes a class from the vocabulary. **Never touches a box.** Deleting a class that 42
annotations carry would either orphan them or silently rewrite 42 annotations, and neither
is something a listbox's delete affordance should be able to do.

* `200` — removed from the table. If boxes still carry the name it stays in the `GET`
  response as `stored: false`, which is the honest answer.
* `404` — unknown dataset, or a name that was only ever inferred.

## Business Rules

1. **A class is created, not typed into existence.** The picker's `New class…` option opens
   a field with an explicit Add. Blur-to-commit would create a class every time a reviewer
   tabbed past the control.
2. **Names are trimmed and compared case-insensitively for uniqueness, but stored as
   typed.** `Pedestrian` and `pedestrian` are the same class; whichever arrived first keeps
   its capitalisation. Two entries differing only in case is a data-entry accident, never
   an intent.
3. **The vocabulary is the union of stored and in-use.** A dataset annotated before this
   feature existed has a full picker on first open. See `GET` above.
4. **The current image's boxes contribute too, before any save.** Run Grounding DINO with
   `a bolt. a nut.` and both are pickable immediately — they are on screen, so a picker that
   cannot offer them is visibly wrong. They are *offered*, not *stored*: nothing is written
   to the table until the boxes are saved or the class is explicitly created.
5. **Renaming a class rewrites every box on the current image that carries it.** A
   proposal run names thirty boxes the same thing and the correction is one decision, not
   thirty. The scope is the image, not the session: only the current image is saved on
   navigate, so a session-wide rewrite would edit images that are not on screen and would
   not be persisted for any of them.
6. **A rename is a local edit until Save, like every other box edit.** It marks the session
   dirty and goes out with the next `PUT`. It does **not** call the classes API — the new
   name reaches the table by being on a saved box, and the old name stays in the vocabulary
   until explicitly deleted.
7. **An unnamed box stays representable.** The picker's first option is `— unnamed —` and
   selecting it clears the class. `text` is optional on `CanvasBox` and a hand-drawn box
   starts with none; a picker with no empty option would make "no class yet" unreachable
   after the first choice.
8. **A folder source has no dataset to read a vocabulary from — until it does.** The Studio
   always writes to a `datasetId` even when reading images from a folder, so the picker
   reads that dataset's vocabulary. It is empty on a brand-new dataset, which is correct:
   the first class is one you create.
9. **The picker is a `<select>`, not a combobox.** Native keyboard behaviour, native mobile
   behaviour, and an accessible name per row for free. `New class…` is a sentinel option
   value that can never collide with a class name, because a class name is trimmed and
   non-empty and the sentinel is not a valid one.

## Data Flow

Full trace in `.mdd/audits/flow-box-class-picker-2026-08-25.md`. In brief, and unchanged by
this feature:

```
store  boxes.prompt
  → GET /datasets/{id}/images  boxes[].prompt
  → storedToCanvasBoxes        CanvasBox.text
  → BoxReviewList row          (was <input>, now <ClassPicker>)
  → saveImageBoxes             boxes[].prompt
  → store  boxes.prompt
```

New, alongside it:

```
store  dataset_classes.name  ∪  DISTINCT boxes.prompt
  → GET /datasets/{id}/classes  classes[].name
  → useDatasetClasses           vocabulary  ∪  classes on the current image's boxes
  → ClassPicker <option>s
```

The two meet only in the picker. Nothing about how a class is stored on a box changes,
which is what keeps this feature off the save path entirely.

## Dependencies

* `47-box-review-list` — the row this replaces a field in, and the `onRename` prop it
  replaces.
* `03-dataset-store` — the schema, the connection module, the transaction helper.
* `50-dataset-as-source` — the Studio always has a `datasetId`, which is what makes rule 8
  true.

## Security

The dataset id is a key into a closed set and is never used to build a path — the route
resolves it through `DatasetStore`, which 404s on an unknown id. The class name is stored
and echoed, never used in a path, a filename, or a query built by concatenation; every
statement is parameterised, as everywhere else in the store.

The `DELETE` route takes a name in the **path**, so it is URL-decoded before use. It is
matched against a `WHERE name = ?` and nothing else; there is no glob, no `LIKE`, and no
filesystem call anywhere on this route.

Length is capped at 100 characters at the schema layer so a caller cannot store an
unbounded string.

## Verified

**In the running app on 2026-08-25**, against the imported Chess pieces dataset — 289
images, 13 classes, none of which this feature put there:

```
GET /datasets/077e.../classes
  bishop 1 · black-bishop 140 · black-king 147 · black-knight 196 · black-pawn 659
  black-queen 87 · black-rook 201 · white-bishop 172 · white-king 149
  white-knight 184 · white-pawn 639 · white-queen 111 · white-rook 200
  every one  stored: false
```

That is rule 3 doing its whole job: a dataset that predates the table opens with a full
picker. Then, in the Studio on one 32-box image:

* **Created** `dark-bishop` from the `New class…` option on box 1. It was selected on that
  box and appeared in the other 31 dropdowns immediately; `GET` reports it
  `stored: true, boxes: 0` — created, not yet used.
* **Renamed** `black-pawn` to `dark-pawn`. All **8** boxes carrying it changed in one
  action, and the session went dirty. Doc 47's first known issue, closed.
* A box drawn by hand opened at `— unnamed —` with every class offered.

## Corrections

**2026-08-25 — the naming field shipped 12px wide.** Reported as "adding a new label does
not allow to write something in", and that is exactly how it looked: the field was
rendered, focused and enabled, and you could type into it, but you could not see anything.

The review row is `1.6rem minmax(0,1fr) 2.6rem auto`. In a 256px panel that leaves the
class column **19px**, and a text field plus Add (41px) plus Cancel (58px) does not fit in
19px — `min-width: 0` obediently squeezed the field to nothing. The picker's `<select>` had
been fine there because a select shrinks to its box; a three-control form does not.

The naming form is now absolutely positioned over the whole row. The score and the verdict
buttons have nothing to say while a class is being named, so covering them costs nothing,
and it needs neither `:has()` nor extra React state to express. Measured after: 106px in
the same 256px panel, ~290px at a normal width.

The lesson for the next control that lives in that column: **measure the cell, not the
component.** A component that lays out correctly in isolation can still be unusable in a
19px grid track, and no test that renders it standalone will notice.

## Known Issues

- "**A rename leaves the old class in the vocabulary.** Renaming `black-pawn` to
  `dark-pawn` rewrites the boxes but does not touch `dataset_classes`, so `black-pawn`
  keeps appearing in the dropdown until it is deleted. Deliberate — a rename is a local box
  edit that rides out with the next save, and rewriting the table from an unsaved edit
  would leave the two disagreeing if the save never happened — but it is a papercut."
- "**Rename is scoped to the current image.** A dataset whose 312 images all carry
  `black-pawn` needs the rename on each. Session-wide rewriting was considered and rejected
  (business rule 5): only the current image is saved on navigate."
- "**Two pickers can be in create/rename mode at once.** Harmless — each commits its own
  row — but the accessible names had to be made row-unique for it, and no design intends it.
- "**The Dataset Generator still has the free-text field.** It does not use
  `BoxReviewList` (doc 47 known issue 3), so it is untouched by this change."
- "**`DELETE` is not reachable from the UI.** The route exists and is tested; nothing in the
  Studio calls it yet, so a class created by mistake can only be removed via the API." 

## Bugs

(none yet — populated by /mdd bug when issues are reported)
