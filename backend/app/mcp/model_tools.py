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
