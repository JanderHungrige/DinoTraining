"""The current schema — the shape a *fresh* database is created at.

Split out of ``db.py`` so the connection module stays about connections. Editing this file
alone is not enough to change an existing install: SQLite's ``CREATE TABLE IF NOT EXISTS``
is a no-op against a table that already exists, so any change to an existing table must also
be added as a step in ``migrations.py``. See `22-mask-dataset-store`.
"""

from __future__ import annotations

#: Every provenance an annotation can carry. Grows as new annotators arrive; each addition
#: needs a migration, because it lives in a CHECK constraint.
PROVENANCE_VALUES = (
    "grounding-dino",
    "hand-drawn",
    "expert-head",
    "sam3",
    # The ungated Grounding DINO + SAM 2.1 path. Recording one of its masks as `sam3`
    # would be false, and "which masks came from the ungated annotator" is a real
    # question when comparing the two. See `23-mask-annotator-registry`.
    "grounded-sam",
    # A dataset someone else published, imported wholesale. The five values above each
    # name a *producer* that ran here — a person, a detector, a head, an annotator — and
    # none of them is true of a third-party dataset. Recording one would make the
    # producer snapshot a fiction. See `31-external-dataset-import`.
    "imported",
)

#: Tables carrying a provenance CHECK. The migration runner rebuilds any of them whose
#: stored DDL is missing a current value, so adding an annotator costs one entry above
#: and no migration code.
PROVENANCE_TABLES = ("boxes", "masks")

#: Nullable columns the runner adds with ALTER TABLE when they are missing. Unlike a
#: CHECK constraint, SQLite *can* add a column in place, so these need no rebuild —
#: a different kind of change, and cheaper.
ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "boxes": {"producer": "TEXT"},
    "masks": {"producer": "TEXT"},
}

_PROVENANCE_CHECK = ", ".join(f"'{value}'" for value in PROVENANCE_VALUES)

BOXES_TABLE = f"""
CREATE TABLE IF NOT EXISTS boxes (
    id         INTEGER PRIMARY KEY,
    image_id   INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    label      TEXT NOT NULL CHECK (label IN ('positive', 'negative', 'unclear')),
    provenance TEXT NOT NULL CHECK (provenance IN ({_PROVENANCE_CHECK})),
    prompt     TEXT,
    score      REAL,
    -- JSON snapshot of what produced this annotation: the head instance or the mask
    -- annotator, with a human label captured at write time. A snapshot rather than a
    -- foreign key, because the head may be deleted and the provenance must outlive it.
    -- NULL for anything a person drew or Wave 1 produced. See `29-generated-dataset-writer`.
    producer   TEXT,
    x          REAL NOT NULL,
    y          REAL NOT NULL,
    w          REAL NOT NULL CHECK (w > 0),
    h          REAL NOT NULL CHECK (h > 0)
);
"""

# Wave 4: segmentation targets. Mirrors `boxes` wherever the concept is the same, so one
# review surface and one export path serve both. The mask itself is COCO RLE; x/y/w/h are
# derived on write so a listing never decodes one.
MASKS_TABLE = f"""
CREATE TABLE IF NOT EXISTS masks (
    id         INTEGER PRIMARY KEY,
    image_id   INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    label      TEXT NOT NULL CHECK (label IN ('positive', 'negative', 'unclear')),
    provenance TEXT NOT NULL CHECK (provenance IN ({_PROVENANCE_CHECK})),
    prompt     TEXT,
    score      REAL,
    -- JSON snapshot of what produced this annotation: the head instance or the mask
    -- annotator, with a human label captured at write time. A snapshot rather than a
    -- foreign key, because the head may be deleted and the provenance must outlive it.
    -- NULL for anything a person drew or Wave 1 produced. See `29-generated-dataset-writer`.
    producer   TEXT,
    rle_counts TEXT NOT NULL,
    rle_height INTEGER NOT NULL CHECK (rle_height > 0),
    rle_width  INTEGER NOT NULL CHECK (rle_width > 0),
    x          REAL NOT NULL,
    y          REAL NOT NULL,
    w          REAL NOT NULL CHECK (w > 0),
    h          REAL NOT NULL CHECK (h > 0)
);
"""

BOX_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_boxes_image ON boxes(image_id);
CREATE INDEX IF NOT EXISTS idx_boxes_label ON boxes(label);
"""

MASK_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_masks_image ON masks(image_id);
CREATE INDEX IF NOT EXISTS idx_masks_label ON masks(label);
"""

SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS datasets (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    prompt      TEXT,
    copy_images INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS images (
    id           INTEGER PRIMARY KEY,
    dataset_id   TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    path         TEXT NOT NULL,
    width        INTEGER NOT NULL,
    height       INTEGER NOT NULL,
    annotated_at TEXT NOT NULL,
    UNIQUE (dataset_id, path)
);

{BOXES_TABLE}
{MASKS_TABLE}

-- Schema v2: trained, imported and default heads. Metadata here, weights on disk --
-- the same split datasets use, so "which heads do this task on this backbone" is a
-- SQL query rather than a directory walk that opens every weight file.
CREATE TABLE IF NOT EXISTS head_instances (
    id                   TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    kind                 TEXT NOT NULL CHECK (
                             kind IN ('pretrained-default', 'community', 'trained-here')),
    head_type_id         TEXT NOT NULL,
    task                 TEXT NOT NULL,
    backbone_id          TEXT NOT NULL,
    backbone_family      TEXT NOT NULL,
    embed_dim            INTEGER NOT NULL,
    num_classes          INTEGER NOT NULL,
    -- JSON array. Order is load-bearing: index 3 in the weights means whatever index 3
    -- meant at training time, and nothing inside a tensor file records that.
    class_names          TEXT NOT NULL DEFAULT '[]',
    dataset_ids          TEXT NOT NULL DEFAULT '[]',
    metrics              TEXT NOT NULL DEFAULT '{{}}',
    primary_metric       TEXT,
    primary_metric_value REAL,
    config               TEXT NOT NULL DEFAULT '{{}}',
    source_repo          TEXT,
    source_digest        TEXT,
    epochs_trained       INTEGER NOT NULL DEFAULT 0,
    best_epoch           INTEGER,
    weights_path         TEXT NOT NULL,
    created_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_images_dataset ON images(dataset_id);
{BOX_INDEXES}
{MASK_INDEXES}
CREATE INDEX IF NOT EXISTS idx_heads_task     ON head_instances(task);
CREATE INDEX IF NOT EXISTS idx_heads_backbone ON head_instances(backbone_id);
"""
