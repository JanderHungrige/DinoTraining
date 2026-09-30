"""Trained models for an assistant (Wave 15.6): their cards, export and MLflow."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from app.mcp import client


def register(mcp: MCPServer) -> None:
    """Attach the model tools. Called by `server.build`."""

    @mcp.tool()
    async def get_model_card(kind: Literal["heads", "finetuned"], instance_id: str) -> Any:
        """A trained model's card (doc 120): the base model (repo, patch size, licence),
        head type, classes in output order, the exact preprocessing (geometry, size, mean,
        std), how to decode its outputs, metrics, datasets, recipe and per-epoch history.
        Everything an application needs to run the model outside this app. `kind` is
        `heads` for a head trained on a frozen backbone, `finetuned` for a fine-tuned model.
        """
        return await client.call("GET", f"/cards/{kind}/{instance_id}")

    @mcp.tool()
    async def export_model(
        kind: Literal["heads", "finetuned"], instance_id: str, destination: str
    ) -> Any:
        """Write a trained model's export bundle (doc 121) as `<name>.zip` into the folder
        `destination` (absolute, existing). For a head it holds the card (`model.json`),
        the weights, `dino_runtime.py` (the app's own preprocessing, head and decoding
        code), `predict.py` and `requirements.txt`; `python predict.py picture.jpg` prints
        what the app would. Returns the zip's path."""
        body = {"kind": kind, "instance_id": instance_id, "destination": destination}
        return await client.call("POST", "/exports", json=body)

    @mcp.tool()
    async def get_mlflow_status() -> Any:
        """Whether training runs go to MLflow (doc 123): the tracking URI, experiment, whether
        models are registered, and which kind of credentials is set (never the values).
        When set up, every head training and fine-tune appears there as a run with params,
        per-epoch metrics, the model card and export bundle, and a registered version."""
        return await client.call("GET", "/mlops/status")

    @mcp.tool()
    async def send_models_to_mlflow() -> Any:
        """Send every model trained before MLflow was set up (doc 124): one run per trained
        head and fine-tuned model, with its settings, metrics (every epoch when recorded),
        card, export bundle and a registry version. Models already in MLflow are skipped.
        Starts a job; read its progress with GET /api/v1/mlops/backfill/{job_id}."""
        return await client.call("POST", "/mlops/backfill")
