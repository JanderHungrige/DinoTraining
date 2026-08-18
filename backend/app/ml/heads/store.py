"""Persistence for head instances: safetensors on disk, metadata in SQLite.

Weights are written as safetensors even for heads this app trained itself. Consistency
with `15-head-catalog-import` is the point: if every head in the system is safetensors,
the loader has no pickle path at all, so there is no branch for an untrusted file to
reach.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from torch import Tensor

from app.core.config import Settings, get_settings
from app.core.paths import ensure_within
from app.datasets.db import data_root, transaction
from app.ml.heads.instances import HeadInstance, HeadInstanceKind

logger = logging.getLogger(__name__)

_COLUMNS = (
    "id, name, kind, head_type_id, task, backbone_id, backbone_family, embed_dim, "
    "num_classes, class_names, dataset_ids, metrics, primary_metric, "
    "primary_metric_value, config, source_repo, source_digest, epochs_trained, "
    "best_epoch, weights_path, created_at"
)


class HeadInstanceNotFoundError(LookupError):
    """No head instance with that id."""


def heads_root(settings: Settings | None = None) -> Path:
    """Directory holding head weight files."""
    return data_root(settings) / "heads"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row_to_instance(row: object) -> HeadInstance:
    data = dict(row)  # type: ignore[call-overload]
    return HeadInstance(
        id=str(data["id"]),
        name=str(data["name"]),
        kind=str(data["kind"]),  # type: ignore[arg-type]
        head_type_id=str(data["head_type_id"]),
        task=str(data["task"]),
        backbone_id=str(data["backbone_id"]),
        backbone_family=str(data["backbone_family"]),
        embed_dim=int(data["embed_dim"]),
        num_classes=int(data["num_classes"]),
        weights_path=str(data["weights_path"]),
        created_at=str(data["created_at"]),
        class_names=tuple(json.loads(data["class_names"])),
        dataset_ids=tuple(json.loads(data["dataset_ids"])),
        metrics=dict(json.loads(data["metrics"])),
        primary_metric=data["primary_metric"],
        primary_metric_value=data["primary_metric_value"],
        config=dict(json.loads(data["config"])),
        source_repo=data["source_repo"],
        source_digest=data["source_digest"],
        epochs_trained=int(data["epochs_trained"]),
        best_epoch=data["best_epoch"],
    )


class HeadInstanceStore:
    """Reads and writes head instances. The only writer of the head_instances table."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    # --- writing ----------------------------------------------------------------

    def register(
        self,
        *,
        name: str,
        kind: HeadInstanceKind,
        head_type_id: str,
        task: str,
        backbone_id: str,
        backbone_family: str,
        embed_dim: int,
        num_classes: int,
        weights: dict[str, Tensor],
        class_names: tuple[str, ...] = (),
        dataset_ids: tuple[str, ...] = (),
        metrics: dict[str, float] | None = None,
        primary_metric: str | None = None,
        primary_metric_value: float | None = None,
        config: dict[str, object] | None = None,
        source_repo: str | None = None,
        source_digest: str | None = None,
        epochs_trained: int = 0,
        best_epoch: int | None = None,
    ) -> HeadInstance:
        """Persist weights then metadata.

        Order matters and only one way round is recoverable: a weights file with no row
        is garbage a cleanup can find, while a row pointing at a missing file is a head
        that fails at the moment the user selects it.
        """
        if kind == "trained-here" and not class_names:
            raise ValueError("A trained head must record the class order it was trained with")

        instance_id = uuid.uuid4().hex
        root = heads_root(self._settings)
        root.mkdir(parents=True, exist_ok=True)
        path = ensure_within(root, root / f"{instance_id}.safetensors")

        from safetensors.torch import save_file

        # contiguous(): safetensors refuses non-contiguous tensors, and a head's
        # state_dict can hold views after cloning.
        save_file({key: value.contiguous().cpu() for key, value in weights.items()}, str(path))

        with transaction(self._settings) as connection:
            connection.execute(
                f"INSERT INTO head_instances ({_COLUMNS}) VALUES ("  # noqa: S608 - fixed columns
                "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    instance_id,
                    name,
                    kind,
                    head_type_id,
                    task,
                    backbone_id,
                    backbone_family,
                    embed_dim,
                    num_classes,
                    json.dumps(list(class_names)),
                    json.dumps(list(dataset_ids)),
                    json.dumps(metrics or {}),
                    primary_metric,
                    primary_metric_value,
                    json.dumps(config or {}),
                    source_repo,
                    source_digest,
                    epochs_trained,
                    best_epoch,
                    str(path),
                    _now(),
                ),
            )

        logger.info("Registered head instance %s (%s, %s)", instance_id, task, kind)
        return self.get(instance_id)

    # --- reading ----------------------------------------------------------------

    def list_all(
        self, task: str | None = None, backbone_id: str | None = None
    ) -> list[HeadInstance]:
        """Every instance, newest first, optionally filtered.

        ``task`` is what powers same-task comparison in Wave 3; ``backbone_id`` hides
        heads that cannot run against what the user has selected.
        """
        clauses: list[str] = []
        params: list[object] = []
        if task is not None:
            clauses.append("task = ?")
            params.append(task)
        if backbone_id is not None:
            clauses.append("backbone_id = ?")
            params.append(backbone_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        with transaction(self._settings) as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM head_instances{where} ORDER BY created_at DESC, id",  # noqa: S608
                params,
            ).fetchall()
        return [_row_to_instance(row) for row in rows]

    def get(self, instance_id: str) -> HeadInstance:
        with transaction(self._settings) as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM head_instances WHERE id = ?",  # noqa: S608
                (instance_id,),
            ).fetchone()
        if row is None:
            raise HeadInstanceNotFoundError(instance_id)
        return _row_to_instance(row)

    def exists(self, instance_id: str) -> bool:
        try:
            self.get(instance_id)
        except HeadInstanceNotFoundError:
            return False
        return True

    def load_weights(self, instance_id: str) -> dict[str, Tensor]:
        """Read a head's weights. Safetensors only — no code executes on load."""
        instance = self.get(instance_id)
        from safetensors.torch import load_file

        loaded: dict[str, Tensor] = load_file(instance.weights_path)
        return loaded

    # --- deleting ---------------------------------------------------------------

    def delete(self, instance_id: str) -> bool:
        """Remove the row and its weights. Idempotent.

        Deleting the file too: an orphaned safetensors is invisible disk usage the Admin
        tab cannot account for, and the user has no way to find it.
        """
        try:
            instance = self.get(instance_id)
        except HeadInstanceNotFoundError:
            return False

        with transaction(self._settings) as connection:
            connection.execute("DELETE FROM head_instances WHERE id = ?", (instance_id,))

        path = Path(instance.weights_path)
        try:
            confined = ensure_within(heads_root(self._settings), path)
            confined.unlink(missing_ok=True)
        except (ValueError, OSError) as exc:
            # The row is already gone, which is what the user asked for. A stuck file is
            # logged rather than resurrecting a head the user believes they deleted.
            logger.warning("Removed head %s but could not delete %s: %s", instance_id, path, exc)

        logger.info("Deleted head instance %s", instance_id)
        return True
