"""MLflow's REST API (doc 123), against a simulated server: paths, auth, and reasons."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.mlops.mlflow_client import MlflowClient, MlflowError


def _server(
    calls: list[tuple[str, str, Any]], *, experiment_exists: bool = False
) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content and request.method == "POST" else None
        calls.append(
            (request.method, request.url.path, body or request.headers.get("authorization"))
        )
        path = request.url.path
        if path.endswith("experiments/get-by-name"):
            if experiment_exists:
                return httpx.Response(200, json={"experiment": {"experiment_id": "7"}})
            return httpx.Response(
                404, json={"error_code": "RESOURCE_DOES_NOT_EXIST", "message": "nope"}
            )
        if path.endswith("experiments/create"):
            return httpx.Response(200, json={"experiment_id": "8"})
        if path.endswith("runs/create"):
            return httpx.Response(
                200,
                json={
                    "run": {
                        "info": {"run_id": "r1", "artifact_uri": "mlflow-artifacts:/8/r1/artifacts"}
                    }
                },
            )
        if path.endswith("registered-models/create"):
            return httpx.Response(
                400, json={"error_code": "RESOURCE_ALREADY_EXISTS", "message": "exists"}
            )
        if path.endswith("model-versions/create"):
            return httpx.Response(200, json={"model_version": {"version": "3"}})
        return httpx.Response(200, json={})

    return httpx.MockTransport(handle)


def _client(calls: list[tuple[str, str, Any]], **settings: Any) -> MlflowClient:
    config = Settings(MLFLOW_TRACKING_URI="http://mlflow.test/", **settings)
    transport = _server(
        calls, experiment_exists=settings.pop("exists", False) if "exists" in settings else False
    )
    client = MlflowClient(config)
    client._http = httpx.Client(
        transport=transport, auth=client._http.auth, headers=client._http.headers
    )
    return client


def test_creates_the_experiment_and_a_run_and_logs_in_batches() -> None:
    calls: list[tuple[str, str, Any]] = []
    client = _client(calls)
    assert client.experiment_id("DinoTraining") == "8"
    run_id, artifacts = client.create_run("8", "screws", {"dinotraining.kind": "head"})
    assert (run_id, artifacts) == ("r1", "mlflow-artifacts:/8/r1/artifacts")
    client.log_params(run_id, {f"p{i}": str(i) for i in range(150)})
    batches = [body for method, path, body in calls if path.endswith("log-batch")]
    assert [len(b["params"]) for b in batches] == [100, 50]


def test_uploads_through_the_artifact_proxy_and_registers_an_existing_model() -> None:
    calls: list[tuple[str, str, Any]] = []
    client = _client(calls)
    client.upload("mlflow-artifacts:/8/r1/artifacts", "model/model.json", b"{}")
    assert ("PUT", "/api/2.0/mlflow-artifacts/artifacts/8/r1/artifacts/model/model.json") == calls[
        -1
    ][:2]
    assert client.register("screws", "r1") == "3"
    assert calls[-1][2]["source"] == "runs:/r1/model"


def test_a_local_artifact_store_is_refused_with_the_fix() -> None:
    client = _client([])
    with pytest.raises(MlflowError, match="--serve-artifacts"):
        client.upload("file:///tmp/mlruns/1/r1/artifacts", "model.json", b"{}")


def test_basic_auth_or_a_token_goes_out_as_http_auth() -> None:
    calls: list[tuple[str, str, Any]] = []
    _client(calls, MLFLOW_TRACKING_TOKEN=SecretStr("t0k3n")).experiment_id("x")
    assert calls[0][2] == "Bearer t0k3n"
    basic: list[tuple[str, str, Any]] = []
    _client(
        basic, MLFLOW_TRACKING_USERNAME="jan", MLFLOW_TRACKING_PASSWORD=SecretStr("pw")
    ).experiment_id("x")
    assert basic[0][2].startswith("Basic ")


def test_an_unreachable_server_says_where() -> None:
    client = MlflowClient(Settings(MLFLOW_TRACKING_URI="http://127.0.0.1:1"))
    with pytest.raises(MlflowError, match="not reachable"):
        client.experiment_id("x")


def test_no_uri_means_not_set_up() -> None:
    with pytest.raises(MlflowError, match="not set up"):
        MlflowClient(Settings())
