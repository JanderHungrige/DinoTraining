"""Training runs in MLflow (doc 123) — never at the cost of training.

`start_run` returns a tracker for one job: `NullTracker` when MLflow is not set up, else
`MlflowTracker`. The run is created on the first event, in the training thread, so starting
a job never waits on MLflow. Every MLflow call is caught; the first failure turns the
tracker off for the rest of the job and becomes one note ("MLflow: …") that the job shows.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from app import __version__
from app.core.config import Settings, get_settings
from app.mlops.mlflow_client import MlflowClient, MlflowError

logger = logging.getLogger(__name__)

STATUS = {"complete": "FINISHED", "failed": "FAILED", "cancelled": "KILLED"}

Begin = tuple[str, dict[str, Any], dict[str, str]]


def flatten(values: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Nested settings as MLflow params: `a.b = value`."""
    flat: dict[str, str] = {}
    for key, value in values.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, f"{name}."))
        else:
            flat[name] = str(value)
    return flat


class NullTracker:
    """MLflow is not set up: nothing happens."""

    def epoch(self, epoch: int, metrics: dict[str, float]) -> None: ...

    def saved(self, kind: str, instance_id: str) -> None: ...

    def finished(self, state: str) -> None: ...


class MlflowTracker:
    def __init__(
        self,
        client: MlflowClient,
        settings: Settings,
        note: Callable[[str], None],
        begin: Begin,
    ) -> None:
        self._client, self._settings, self._note = client, settings, note
        self.run_id: str | None = None
        self._artifacts = ""
        self._done = False
        self._ended = False
        self._pending: Begin | None = begin

    def _guard(self, action: Callable[[], None]) -> None:
        if self._done:
            return
        try:
            action()
        except (MlflowError, KeyError, ValueError, OSError) as error:
            # Off for the rest of the job: one note, not one per epoch.
            logger.warning("MLflow tracking stopped for run %s: %s", self.run_id, error)
            self._note(f"MLflow: {error}")
            self._done = True

    def _ensure(self) -> None:
        if self._pending is None:
            return
        name, params, tags = self._pending
        self._pending = None

        def go() -> None:
            experiment = self._client.experiment_id(self._settings.mlflow_experiment)
            all_tags = {"dinotraining.app_version": __version__, **tags}
            self.run_id, self._artifacts = self._client.create_run(experiment, name, all_tags)
            self._client.log_params(self.run_id, flatten(params))

        self._guard(go)

    def epoch(self, epoch: int, metrics: dict[str, float]) -> None:
        self._ensure()
        run_id = self.run_id
        if run_id is not None:
            self._guard(lambda: self._client.log_metrics(run_id, metrics, epoch))

    def saved(self, kind: str, instance_id: str) -> None:
        """The model is saved: card and bundle as artifacts, a registry version, finished."""
        self._ensure()
        run_id = self.run_id
        if run_id is None:
            return
        artifacts = self._artifacts
        self._guard(
            lambda: log_model(self._client, self._settings, run_id, artifacts, kind, instance_id)
        )
        self.finished("complete")

    def finished(self, state: str) -> None:
        """End the run with the job's outcome. A job that never reached an epoch has none.

        Tried even after an earlier failure turned tracking off (found live: a refused
        registry name left the run RUNNING forever). Best effort, and no second note.
        """
        run_id = self.run_id
        if run_id is not None and not self._ended:
            self._ended = True
            try:
                self._client.end_run(run_id, STATUS.get(state, "FAILED"))
            except MlflowError as error:
                logger.warning("MLflow run %s could not be ended: %s", run_id, error)
        self._done = True


def registry_name(name: str) -> str:
    """MLflow refuses '/' and ':' in a registered model's name (found live); the app's
    names have them ("Object detection: m8 +1 more")."""
    cleaned = re.sub(r"\s*[:/]\s*", " - ", name).strip(" -")
    return cleaned or "model"


def log_model(
    client: MlflowClient,
    settings: Settings,
    run_id: str,
    artifacts: str,
    kind: str,
    instance_id: str,
) -> None:
    """Card and bundle into the run's `model/`, the model tag, and a registry version."""
    import json

    from app.mlops.card import card_for
    from app.mlops.export import bundle_files, zip_bytes

    card = card_for(kind, instance_id)
    zip_name, files = bundle_files(kind, instance_id, onnx=False)
    client.upload(artifacts, "model/model.json", json.dumps(card, indent=2).encode())
    client.upload(artifacts, f"model/{zip_name}", zip_bytes(files))
    client.set_tag(run_id, "dinotraining.model", f"{kind}:{instance_id}")
    if settings.mlflow_register:
        version = client.register(registry_name(str(card["model"]["name"])), run_id)
        client.set_tag(run_id, "dinotraining.registered_version", version)


def start_run(
    name: str, params: dict[str, Any], tags: dict[str, str], note: Callable[[str], None]
) -> NullTracker | MlflowTracker:
    settings = get_settings()
    if not settings.mlflow_uri:
        return NullTracker()
    try:
        return MlflowTracker(MlflowClient(settings), settings, note, (name, params, tags))
    except MlflowError as error:
        note(f"MLflow: {error}")
        return NullTracker()


__all__ = ["MlflowTracker", "NullTracker", "flatten", "log_model", "start_run"]
