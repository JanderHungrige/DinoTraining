"""MLflow's REST API (doc 123), verified against a real server. The only place its paths live.

Plain `httpx`, not the `mlflow` package: the few calls needed are HTTP, and the package's
dependency tree is not worth shipping for them. Credentials go out as HTTP auth and are
never logged.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings

TIMEOUT_S = 10.0
#: runs/log-batch limits: 100 params and 1000 metrics per call; param values ≤ 500 chars
#: on older servers (6000 on newer) — 500 is safe everywhere.
MAX_PARAMS, MAX_METRICS, MAX_VALUE = 100, 1000, 500


class MlflowError(RuntimeError):
    """An MLflow call that failed, with MLflow's own reason."""


def _now_ms() -> int:
    return int(time.time() * 1000)


class MlflowClient:
    def __init__(self, settings: Settings | None = None, http: httpx.Client | None = None) -> None:
        settings = settings or get_settings()
        if not settings.mlflow_uri:
            raise MlflowError("MLflow is not set up: no tracking URI.")
        self.uri = settings.mlflow_uri.rstrip("/")
        auth: httpx.Auth | None = None
        headers: dict[str, str] = {}
        if settings.mlflow_token is not None:
            headers["Authorization"] = f"Bearer {settings.mlflow_token.get_secret_value()}"
        elif settings.mlflow_username and settings.mlflow_password is not None:
            auth = httpx.BasicAuth(
                settings.mlflow_username, settings.mlflow_password.get_secret_value()
            )
        self._http = http or httpx.Client(timeout=TIMEOUT_S, auth=auth, headers=headers)

    # --- plumbing ----------------------------------------------------------------

    def _call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._http.request(method, f"{self.uri}/api/2.0/{path}", **kwargs)
        except httpx.HTTPError as error:
            raise MlflowError(f"MLflow at {self.uri} is not reachable: {error}") from error
        if response.status_code >= 400:
            try:
                failure = response.json()
                code = failure.get("error_code")
                message = failure.get("message") or response.text
                reason = f"{code}: {message}" if code else message
            except ValueError:
                reason = response.text[:200]
            raise MlflowError(f"MLflow answered {response.status_code}: {reason}")
        if not response.content:
            return {}
        body: dict[str, Any] = response.json()
        return body

    # --- experiments and runs ------------------------------------------------------

    def experiment_id(self, name: str) -> str:
        """The experiment's id, creating it when it does not exist yet."""
        try:
            found = self._call(
                "GET", "mlflow/experiments/get-by-name", params={"experiment_name": name}
            )
            return str(found["experiment"]["experiment_id"])
        except MlflowError as error:
            if "RESOURCE_DOES_NOT_EXIST" not in str(error) and "404" not in str(error):
                raise
        return str(
            self._call("POST", "mlflow/experiments/create", json={"name": name})["experiment_id"]
        )

    def create_run(self, experiment_id: str, name: str, tags: dict[str, str]) -> tuple[str, str]:
        """(run id, artifact URI)."""
        body = {
            "experiment_id": experiment_id,
            "run_name": name,
            "start_time": _now_ms(),
            "tags": [{"key": k, "value": v[:MAX_VALUE]} for k, v in tags.items()],
        }
        info = self._call("POST", "mlflow/runs/create", json=body)["run"]["info"]
        return str(info["run_id"]), str(info["artifact_uri"])

    def log_params(self, run_id: str, params: dict[str, str]) -> None:
        items = [{"key": k[:250], "value": str(v)[:MAX_VALUE]} for k, v in params.items()]
        for start in range(0, len(items), MAX_PARAMS):
            self._call(
                "POST",
                "mlflow/runs/log-batch",
                json={"run_id": run_id, "params": items[start : start + MAX_PARAMS]},
            )

    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int) -> None:
        stamp = _now_ms()
        items = [
            {"key": k, "value": float(v), "timestamp": stamp, "step": step}
            for k, v in metrics.items()
        ]
        for start in range(0, len(items), MAX_METRICS):
            self._call(
                "POST",
                "mlflow/runs/log-batch",
                json={"run_id": run_id, "metrics": items[start : start + MAX_METRICS]},
            )

    def set_tag(self, run_id: str, key: str, value: str) -> None:
        self._call(
            "POST",
            "mlflow/runs/set-tag",
            json={"run_id": run_id, "key": key, "value": value[:MAX_VALUE]},
        )

    def end_run(self, run_id: str, status: str) -> None:
        self._call(
            "POST",
            "mlflow/runs/update",
            json={"run_id": run_id, "status": status, "end_time": _now_ms()},
        )

    def upload(self, artifact_uri: str, path: str, data: bytes) -> None:
        """Through the server's artifact proxy (`mlflow server` serves artifacts by default)."""
        prefix = "mlflow-artifacts:/"
        if not artifact_uri.startswith(prefix):
            raise MlflowError(
                f"This server stores artifacts at {artifact_uri}, which the app cannot reach; "
                "start it with --serve-artifacts (the default since MLflow 2)."
            )
        location = artifact_uri[len(prefix) :].strip("/")
        self._call("PUT", f"mlflow-artifacts/artifacts/{location}/{path}", content=data)

    # --- registry -------------------------------------------------------------------

    def register(self, name: str, run_id: str, path: str = "model") -> str:
        """A new version of registered model `name` from the run's `path`; returns it."""
        try:
            self._call("POST", "mlflow/registered-models/create", json={"name": name})
        except MlflowError as error:
            if "RESOURCE_ALREADY_EXISTS" not in str(error) and "already exists" not in str(error):
                raise
        body = {"name": name, "source": f"runs:/{run_id}/{path}", "run_id": run_id}
        return str(
            self._call("POST", "mlflow/model-versions/create", json=body)["model_version"][
                "version"
            ]
        )

    def search_runs(self, experiment_id: str, tag: str, value: str) -> list[str]:
        """Run ids in the experiment whose tag has this value (doc 124's idempotency)."""
        body = {
            "experiment_ids": [experiment_id],
            "filter": f"tags.`{tag}` = '{value}'",
            "max_results": 10,
        }
        return [
            str(r["info"]["run_id"])
            for r in self._call("POST", "mlflow/runs/search", json=body).get("runs", [])
        ]


__all__ = ["MlflowClient", "MlflowError"]
