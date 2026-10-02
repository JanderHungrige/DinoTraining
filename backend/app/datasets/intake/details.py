"""A dataset's description, source and import record (doc 136).

The two columns are what lists show; `dataset.json` (the dataset's own record, store.py)
also keeps what the detection saw at import time, so the folder tells its story without
the database.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.store import MANIFEST_NAME, dataset_dir

if TYPE_CHECKING:
    from app.datasets.intake.detect import Detection


def set_details(
    dataset_id: str,
    description: str | None,
    source: str | None,
    detection: Detection | None,
    settings: Settings | None = None,
) -> None:
    description = (description or "").strip() or None
    with transaction(settings) as connection:
        connection.execute(
            "UPDATE datasets SET description = ?, source = ? WHERE id = ?",
            (description, source, dataset_id),
        )
    path = dataset_dir(dataset_id, settings) / MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    manifest["description"] = description
    manifest["source"] = source
    if detection is not None:
        manifest["imported"] = detection.model_dump(exclude={"path", "notes"})
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
