"""Fine-tuning tools for an assistant (doc 98): the same requirements the user sees.

Wave 12's point was that the user *and the assistant* are told exactly what training data
each model needs. So the requirements are a tool, the check is a tool, and starting a
fine-tune refuses, in the same words, a dataset that breaks a rule.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from app.mcp import client


def register(mcp: MCPServer) -> None:
    """Attach the fine-tuning tools. Called by `server.build`."""

    @mcp.tool()
    async def get_finetune_requirements(finetune_id: str | None = None) -> Any:
        """What each fine-tunable model needs its training data to look like.

        Without `finetune_id`, every model: RF-DETR (boxes), SAM 2.1 (one outline per
        object), SAM 3 (outlines named by a noun phrase), and DINO backbones (one class per
        image, or outlines). Each entry says the annotation kind, the minimum images and
        instances per class **and why**, whether a recipe is required, the gates (licence,
        memory), and `data_format`: a paragraph to relay to the user as it is.
        """
        path = "/finetune/requirements" + (f"/{finetune_id}" if finetune_id else "")
        return await client.call("GET", path)

    @mcp.tool()
    async def check_dataset_for(
        finetune_id: str, dataset_id: str, recipe_id: str | None = None
    ) -> Any:
        """Check a dataset (and recipe) against a model's requirements before training.

        Returns every rule with `passed`, what was found, and the `fix`. Relay failed
        rules with their fix; do not start a fine-tune until `ready` is true.
        """
        return await client.call(
            "POST",
            "/finetune/check",
            json={"finetune_id": finetune_id, "dataset_id": dataset_id, "recipe_id": recipe_id},
        )

    @mcp.tool()
    async def start_finetune(
        finetune_id: str,
        dataset_ids: list[str],
        name: str,
        recipe_id: str | None = None,
        epochs: int = 6,
        learning_rate: float | None = None,
        unfreeze_blocks: int | None = None,
    ) -> Any:
        """Fine-tune a foundation model. Returns a job id — poll `get_job` with kind
        `foundation-finetune`.

        Refused with the failed rules named when the data does not meet the requirements
        (run `check_dataset_for` first). The finished job reports `baseline_metrics` and
        `final_metrics` on the same held-out pictures: **report both**. When no round beat
        the base model, nothing is saved and `notes` says so; say that too.

        `unfreeze_blocks` is for DINO backbones (default 4). The default learning rate is
        1e-3 for DINO backbones and 1e-4 otherwise.
        """
        backbone = finetune_id.startswith("dinov")
        body: dict[str, Any] = {
            "finetune_id": finetune_id,
            "dataset_ids": dataset_ids,
            "name": name,
            "epochs": epochs,
            "learning_rate": learning_rate or (1e-3 if backbone else 1e-4),
        }
        if recipe_id:
            body["recipe_id"] = recipe_id
        if backbone:
            body["options"] = {"unfreeze_blocks": unfreeze_blocks or 4}
        return await client.call("POST", "/finetune/jobs", json=body)


__all__ = ["register"]
