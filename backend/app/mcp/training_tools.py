"""Training settings and default recipes for an assistant (doc 102).

The same catalogue the Training tab renders (doc 99) and the same one-click default recipe
(doc 101): what the user is told, the assistant is told.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from app.mcp import client


def register(mcp: MCPServer) -> None:
    """Attach the training-settings tools. Called by `server.build`."""

    @mcp.tool()
    async def get_training_parameters(model_id: str) -> Any:
        """Every setting a model's training honours, explained.

        `model_id` is `head` (a DINO head, see `train_head`) or a fine-tune id such as
        `rf-detr-nano`, `sam2.1-hiera-small`, `sam3` or `dinov2-small-segmentation` (see
        `get_finetune_requirements`). Each parameter has a plain `label`, the technical
        `term`, `help`, the `default` and `why` it is the default, its range and `level`
        (basic or advanced).

        Keep the defaults unless the user asks for something: they are the values this app
        measured its results with. When you send a non-default value, tell the user which
        and why. Parameters marked `recipe_overrides` are replaced by a chosen recipe.
        """
        return await client.call("GET", f"/training/parameters/{model_id}")

    @mcp.tool()
    async def create_default_recipe(
        dataset_id: str,
        model_id: str,
        head_type_id: str | None = None,
        backbone_id: str | None = None,
    ) -> Any:
        """Make the model's default preparation recipe for a dataset. Returns a job id —
        poll `get_job` with kind `default-recipe`; the finished job carries `recipe.id`.

        The same as the Prepare data steps with every recommendation taken: an audit, a
        leak-free split (one the user already made, or that came with the data, is kept),
        the recommended class balance and changed copies. Saved as "Default for <model>";
        asking again returns the same recipe while the data is unchanged.

        `model_id` is `head` — then give `head_type_id` and `backbone_id` — or a fine-tune
        id. SAM and DINO-backbone fine-tunes require a recipe; a head without one trains on
        a random split, which makes near-identical pictures score too well. Tell the user
        the audit's `problem` findings still apply: the recipe prepares the data, it does
        not fix what the audit found.
        """
        body: dict[str, Any] = {"model_id": model_id}
        if head_type_id:
            body["head_type_id"] = head_type_id
        if backbone_id:
            body["backbone_id"] = backbone_id
        return await client.call("POST", f"/datasets/{dataset_id}/recipes/default", json=body)


__all__ = ["register"]
