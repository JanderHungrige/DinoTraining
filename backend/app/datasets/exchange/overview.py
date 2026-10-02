"""What would be lost by uninstalling now (doc 146): work without an export, or newer than it."""

from __future__ import annotations

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.datasets.db import transaction
from app.datasets.exchange.auto import changed_since_export, datasets_with_work
from app.ml.foundation.instances import FoundationInstanceStore


class ExportOverview(BaseModel):
    #: Datasets with at least one saved picture.
    datasets: int
    no_target: list[str]
    unexported: list[str]
    models: int
    #: Doc 145: where trained models export by themselves; None when off.
    model_folder: str | None


def export_overview(settings: Settings | None = None) -> ExportOverview:
    no_target: list[str] = []
    unexported: list[str] = []
    entries = datasets_with_work(settings)
    for dataset_id, name, target, exported in entries:
        if target is None:
            no_target.append(name)
        elif changed_since_export(dataset_id, exported, settings):
            unexported.append(name)
    with transaction(settings) as connection:
        heads = connection.execute(
            "SELECT COUNT(*) AS n FROM head_instances WHERE kind = 'trained-here'"
        ).fetchone()["n"]
    finetuned = len(FoundationInstanceStore(settings).list_all())
    return ExportOverview(
        datasets=len(entries),
        no_target=no_target,
        unexported=unexported,
        models=int(heads) + finetuned,
        model_folder=(settings or get_settings()).model_export_folder,
    )
