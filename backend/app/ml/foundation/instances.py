"""Fine-tuned foundation models, on disk and in the catalogue (doc 44).

Mirrors `heads/instances.py` in what it records and why — a name, what it was trained on,
its metrics, and when — because the question asked of a saved model is the same either way:
*what is this, and what was it made from?*

**Not a `HeadInstance`.** That type carries a `backbone_id` and is composed against one
through `run_heads`' shared pass. A fine-tuned RF-DETR has no separate backbone to name; it
*is* backbone and decoder together, so it is stored beside the built-in foundation models
and appears in the same picker.

Weights are written with `save_pretrained` — the whole model, ~116 MB per fine-tune. Saving
only the 8.4M trained parameters would be a quarter the size and would need a bespoke
loader that reassembles them onto a base checkpoint; `from_pretrained` on a complete
directory is the path transformers supports and the one that will still work in a year.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.paths import default_data_dir, ensure_within

logger = logging.getLogger(__name__)

#: One JSON file per instance, beside its weights. A directory listing is the index, so
#: there is no second source of truth to fall out of step with what is on disk.
MANIFEST = "instance.json"


@dataclass(frozen=True, slots=True)
class FoundationInstance:
    """One fine-tuned model, as the app offers it."""

    id: str
    name: str
    #: The catalogue entry it was fine-tuned from, so provenance survives the file move.
    base_model_id: str
    dataset_ids: tuple[str, ...]
    class_names: tuple[str, ...]
    metrics: dict[str, float]
    epochs_trained: int
    created_at: str

    @property
    def summary(self) -> str:
        """One line, composed here so every tab reads it identically — doc 12's rule."""
        classes = f"{len(self.class_names)} class{'' if len(self.class_names) == 1 else 'es'}"
        score = self.metrics.get("map")
        trained = f"fine-tuned from {self.base_model_id} · {classes}"
        return trained if score is None else f"{trained} · map {score:.3f}"


def instances_root(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    root = settings.data_dir if settings.data_dir else default_data_dir()
    return (root / "foundation-instances").resolve()


class FoundationInstanceStore:
    """Reads and writes fine-tuned models under one directory."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._root = instances_root(self._settings)

    def directory(self, instance_id: str) -> Path:
        """The one sanctioned way to build an instance path — confined, like doc 02's."""
        return ensure_within(self._root, self._root / instance_id)

    def list_all(self) -> list[FoundationInstance]:
        if not self._root.is_dir():
            return []
        found: list[FoundationInstance] = []
        for entry in sorted(self._root.iterdir()):
            manifest = entry / MANIFEST
            if not manifest.is_file():
                continue
            try:
                found.append(_read(manifest))
            except (ValueError, KeyError, json.JSONDecodeError):
                # A half-written manifest must not take the whole listing down with it.
                logger.warning("Ignoring unreadable foundation instance at %s", entry)
        return found

    def get(self, instance_id: str) -> FoundationInstance | None:
        manifest = self.directory(instance_id) / MANIFEST
        return _read(manifest) if manifest.is_file() else None

    def save(
        self,
        *,
        existing_id: str | None,
        name: str,
        base_model_id: str,
        dataset_ids: tuple[str, ...],
        class_names: tuple[str, ...],
        metrics: dict[str, float],
        epochs_trained: int,
        save: Callable[[Path], None],
    ) -> FoundationInstance:
        """Write weights and manifest, replacing an earlier best from the same run.

        `existing_id` is what lets a run overwrite its own previous best rather than
        leaving a directory per epoch — the caller saves on every improvement so that a
        cancelled run still keeps the best model it reached.
        """
        instance_id = existing_id or uuid.uuid4().hex
        directory = self.directory(instance_id)
        # Created here, not by the caller: every caller creating its own is one caller
        # away from a half-written instance with no directory and a manifest that says
        # otherwise.
        directory.mkdir(parents=True, exist_ok=True)
        save(directory)

        instance = FoundationInstance(
            id=instance_id,
            name=name,
            base_model_id=base_model_id,
            dataset_ids=dataset_ids,
            class_names=class_names,
            metrics=metrics,
            epochs_trained=epochs_trained,
            created_at=datetime.now(UTC).isoformat(),
        )
        (directory / MANIFEST).write_text(json.dumps(_as_dict(instance), indent=2))
        logger.info("Saved fine-tuned model %s (%s)", instance_id, name)
        return instance

    def delete(self, instance_id: str) -> bool:
        directory = self.directory(instance_id)
        if not directory.is_dir():
            return False
        for entry in sorted(directory.rglob("*"), reverse=True):
            entry.unlink() if entry.is_file() else entry.rmdir()
        directory.rmdir()
        logger.info("Deleted fine-tuned model %s", instance_id)
        return True


def _as_dict(instance: FoundationInstance) -> dict[str, object]:
    return {
        "id": instance.id,
        "name": instance.name,
        "base_model_id": instance.base_model_id,
        "dataset_ids": list(instance.dataset_ids),
        "class_names": list(instance.class_names),
        "metrics": instance.metrics,
        "epochs_trained": instance.epochs_trained,
        "created_at": instance.created_at,
    }


def _read(manifest: Path) -> FoundationInstance:
    raw = json.loads(manifest.read_text())
    return FoundationInstance(
        id=str(raw["id"]),
        name=str(raw["name"]),
        base_model_id=str(raw["base_model_id"]),
        dataset_ids=tuple(str(v) for v in raw.get("dataset_ids", [])),
        class_names=tuple(str(v) for v in raw.get("class_names", [])),
        metrics={str(k): float(v) for k, v in (raw.get("metrics") or {}).items()},
        epochs_trained=int(raw.get("epochs_trained", 0)),
        created_at=str(raw.get("created_at", "")),
    )


__all__ = ["FoundationInstance", "FoundationInstanceStore", "instances_root"]
