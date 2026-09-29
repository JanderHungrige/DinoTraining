"""The data-preparation tools an assistant gets (docs 81–91).

Same rules as `tools.py`: task-shaped, and the docstring is the prompt. Preparation is
where an assistant is most likely to do harm by being helpful: it can split video frames
at random, train on 2-pixel objects, or merge classes it should have asked about. So each
docstring says what the step protects against, what to report, and when to ask the user
instead of deciding.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from app.datasets.bbox_conventions import Convention
from app.mcp import client

FixAction = Literal["exclude", "include", "exclude-copies", "exclude-unreadable", "set-class-map"]
Strategy = Literal["none", "weighted-loss", "balanced-sampling"]


async def _recommended(dataset_id: str, target: str) -> tuple[str, str]:
    """The Balance and Augment steps' recommendations, as the Prepare tab preselects them."""
    params = {"target": target}
    balance = await client.call("GET", f"/datasets/{dataset_id}/balance", params=params)
    augmentation = await client.call("GET", f"/datasets/{dataset_id}/augmentation", params=params)
    return str(balance["recommended"]), str(augmentation["recommended"])


def register(mcp: MCPServer) -> None:
    """Attach the preparation tools. Called by `server.build`, after `tools.register`."""

    @mcp.tool()
    async def inspect_coco_export(directory: str) -> Any:
        """Check a COCO or Roboflow export **before** importing it. Writes nothing.

        Reports how the export writes its boxes (`convention`: `xywh`, `xyxy` or
        `xywh-normalized`), whether every referenced image exists at the size it claims, class
        names that look like one class spelled twice (`proposed_class_map`), and whether
        it ships its own train/valid/test split. Pass what it found to
        `import_coco_dataset`. If `convention` is null the evidence is mixed: ask the user.

        Measured here: importing an xyxy export as xywh silently dropped 162 of 273 boxes.
        """
        return await client.call(
            "POST", "/datasets/import/coco/inspect", json={"directory": directory}
        )

    @mcp.tool()
    async def import_coco_dataset(
        name: str,
        directory: str,
        copy_images: bool = False,
        box_convention: Convention = "xywh",
        class_map: dict[str, str] | None = None,
        keep_source_split: bool = False,
    ) -> Any:
        """Import a COCO or Roboflow export as a new dataset. Run `inspect_coco_export`
        first and pass its `convention` as `box_convention`, and `proposed_class_map` as
        `class_map` once the user agrees the names are one class.

        `directory` is an absolute path **on the machine running this app** — the backend
        opens the files itself, there is no upload. `keep_source_split` keeps the export's
        train/valid/test folders as the split.

        Read `skipped_images` and `skipped_boxes` in the response and report them. An
        import that silently dropped half its boxes looks identical to a clean one.
        """
        return await client.call(
            "POST",
            "/datasets/import/coco",
            json={
                "name": name,
                "directory": directory,
                "copy_images": copy_images,
                "box_convention": box_convention,
                "class_map": class_map or {},
                "keep_source_split": keep_source_split,
            },
        )

    @mcp.tool()
    async def audit_dataset(dataset_id: str, target: str) -> Any:
        """Check a dataset before training on it. Returns a job id — poll `get_job` with
        kind `audit`; the finished job carries the audit.

        `target` is the model it will train (see `plan_preparation` for the ids, e.g.
        `head-detection-dinov2`, `rf-detr-nano`): object sizes are judged at that model's
        input, so an audit for another model says little about this one.

        Report every `problem` finding to the user in its own words (`what`, `why`,
        `action`). Findings about blur, lighting or wrong labels need a person: list the
        `examples` paths and ask them to look, do not decide for them.
        """
        return await client.call("POST", f"/datasets/{dataset_id}/audit", json={"target": target})

    @mcp.tool()
    async def fix_dataset(
        dataset_id: str,
        action: FixAction,
        paths: list[str] | None = None,
        class_map: dict[str, str | None] | None = None,
    ) -> Any:
        """Apply a safe, reversible fix. Nothing is ever deleted.

        `exclude-copies` keeps one picture of each copy group; `exclude-unreadable` drops
        files that will not open; `exclude`/`include` take `paths`. `set-class-map` maps a
        class name to another (merge, rename) or to null (leave it out of training; its
        objects are then ignored, not taught as background).

        **Ask before merging or dropping classes** — which classes mean the same thing is
        the user's knowledge, not yours. After any fix, run `audit_dataset` again: a recipe
        refuses data that changed since its audit.
        """
        body: dict[str, Any] = {"action": action}
        if paths:
            body["paths"] = paths
        if class_map is not None:
            body["class_map"] = class_map
        return await client.call("POST", f"/datasets/{dataset_id}/fixes", json=body)

    @mcp.tool()
    async def split_dataset(
        dataset_id: str,
        mode: Literal["auto", "keep-source"] = "auto",
        val_fraction: float = 0.2,
        test_fraction: float = 0.1,
        seed: int = 42,
    ) -> Any:
        """Split into train/validation/test so that no scene or stretch of video is on two
        sides. Run it after the audit: the audit's scene groups are what it keeps together.

        Never split video frames at random yourself — neighbouring frames are near-copies
        and the test score then measures memory (measured here: +42% mAP that was not
        there). Report the `warnings`: a class missing from test cannot be scored.
        """
        return await client.call(
            "POST",
            f"/datasets/{dataset_id}/split",
            json={
                "mode": mode,
                "val_fraction": val_fraction,
                "test_fraction": test_fraction,
                "seed": seed,
            },
        )

    @mcp.tool()
    async def plan_preparation(dataset_id: str, target: str, grid: int | None = None) -> Any:
        """What the model will see, and the recommended handling, in one call: the input
        plan (size, fit, object sizes, whether to cut into tiles), the class-imbalance
        recommendation, and the augmentation recommendation.

        If `input.tiling.recommended` is true, objects are too small at the whole-picture
        scale and training without tiles will not learn them — say so. `grid` overrides
        the tiling (tiles along the long edge; 1 is off). `targets` lists valid `target`s.
        """
        params: dict[str, Any] = {"target": target}
        if grid:
            params["grid"] = grid
        path = f"/datasets/{dataset_id}"
        return {
            "targets": await client.call("GET", "/prep/targets"),
            "input": await client.call("GET", f"{path}/input-plan", params=params),
            "balance": await client.call("GET", f"{path}/balance", params={"target": target}),
            "augmentation": await client.call(
                "GET", f"{path}/augmentation", params={"target": target}
            ),
        }

    @mcp.tool()
    async def save_recipe(
        dataset_id: str,
        name: str,
        target: str,
        imbalance: Strategy | None = None,
        augmentation: str | None = None,
        grid: int | None = None,
    ) -> Any:
        """Save the preparation as a recipe, then pass its id as `recipe_id` to
        `train_head` or `start_finetune`.

        Left out, `imbalance` and `augmentation` take the recommendations. Refused (409)
        with the missing step named when there is no audit, the data changed since it, or
        there is no split. A recipe that goes out of date later is refused by training
        with what changed; save it again.
        """
        if imbalance is None or augmentation is None:
            recommended_balance, recommended_augmentation = await _recommended(dataset_id, target)
            imbalance = imbalance or recommended_balance  # type: ignore[assignment]
            augmentation = augmentation or recommended_augmentation
        return await client.call(
            "POST",
            f"/datasets/{dataset_id}/recipes",
            json={
                "name": name,
                "target": target,
                "imbalance": imbalance,
                "augmentation": augmentation,
                "grid": grid,
            },
        )

    @mcp.tool()
    async def list_recipes(dataset_id: str) -> Any:
        """A dataset's recipes, oldest first. `out_of_date` says why one no longer
        describes the data; only an up-to-date recipe can be trained from."""
        return await client.call("GET", f"/datasets/{dataset_id}/recipes")


__all__ = ["register"]
