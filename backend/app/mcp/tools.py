"""The tools a local assistant gets (doc 64).

**Task-shaped, not endpoint-shaped.** The API has 61 operations; exposing one tool each
would flood the model's context and leave it doing the orchestration anyway, which is the
problem doc 63's guide exists to solve. These are the fifteen things someone actually asks
for, and each hides whichever route serves it.

**Every docstring is the prompt.** An MCP client shows the model the tool name, the
docstring and the parameter types, and that is *all* it sees before deciding. So the
preconditions, the traps and the units live here rather than in prose somewhere else —
this file is documentation that happens to execute.

Long work is never awaited. A download, a training run and a fine-tune each return a job
id, and `get_job` polls it. Blocking a tool call for four minutes hits a client timeout and
loses the run.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from app.mcp import client

#: Which poll route a job id belongs to. Three different endpoints, one tool, because the
#: assistant should not have to remember which kind of job it started.
JobKind = Literal["download", "training", "finetune"]

_JOB_PATHS: dict[str, str] = {
    "download": "/models/jobs/{job_id}",
    "training": "/training/jobs/{job_id}",
    "finetune": "/foundation/finetune/{job_id}",
}


def register(mcp: MCPServer) -> None:
    """Attach every tool to the server. Called once, by `server.build`."""

    # --- what exists ------------------------------------------------------------

    @mcp.tool()
    async def list_models() -> Any:
        """List the model catalogue and whether each is installed.

        Nothing is bundled — weights download on demand. Check `installed` before trying
        to run or fine-tune anything. `rf-detr-nano` is the general detector and the one
        to fine-tune; `dinov2-small` is the backbone trained heads run on.
        """
        return await client.call("GET", "/models")

    @mcp.tool()
    async def list_datasets() -> Any:
        """List datasets, with per-dataset counts of images, boxes and masks."""
        return await client.call("GET", "/datasets")

    @mcp.tool()
    async def list_heads() -> Any:
        """List trained heads and imported ones.

        `trained_width` is the median width of the images a head trained on. If you are
        running it on something much wider, pass `tiles` to `run_inference` or it will
        find nothing — and the call will still succeed.
        """
        return await client.call("GET", "/heads")

    @mcp.tool()
    async def get_guide() -> Any:
        """The full API guide: every workflow, in order, with the traps named.

        Read this first when a request needs several steps. It documents things no tool
        schema can, such as which field means what and why a call succeeded but did
        nothing.
        """
        return await client.call("GET", "/docs/agent-guide")

    # --- long-running work ------------------------------------------------------

    @mcp.tool()
    async def install_model(model_id: str) -> Any:
        """Start downloading a model. Returns a job id — poll it with `get_job`.

        Gated models (`sam3`, the DINOv3 backbones) need a HuggingFace token, and SAM 3
        also needs an access request Meta approves by hand. Those fail with a 409 that
        says so; do not retry, it will not become approved.
        """
        return await client.call("POST", f"/models/{model_id}/download")

    @mcp.tool()
    async def get_job(job_id: str, kind: JobKind) -> Any:
        """Check a download, training run or fine-tune. Poll until `state` is not
        `running`.

        `kind` says which of the three started it. Report the metrics as they move —
        `best_metric` for training, progress for a download — because a run that finished
        and learned nothing looks exactly like one that worked.
        """
        return await client.call("GET", _JOB_PATHS[kind].format(job_id=job_id))

    @mcp.tool()
    async def train_head(
        head_type_id: str,
        backbone_id: str,
        dataset_ids: list[str],
        epochs: int = 20,
        learning_rate: float = 0.001,
    ) -> Any:
        """Train a head on a frozen backbone. Returns a job id — poll with `get_job`.

        The head type must match the data: `linear-classifier` needs one class per image,
        `dense-detector` needs boxes, `linear-segmenter` needs masks. A mismatch is refused
        with a message saying which.

        For boxes, `finetune_model` is usually the better answer — measured here at mAP
        0.96 against 0.5-0.6 for a detector head on the same data.
        """
        return await client.call(
            "POST",
            "/training/jobs",
            json={
                "head_type_id": head_type_id,
                "backbone_id": backbone_id,
                "dataset_ids": dataset_ids,
                "epochs": epochs,
                "learning_rate": learning_rate,
            },
        )

    @mcp.tool()
    async def finetune_model(
        foundation_id: str,
        dataset_ids: list[str],
        name: str,
        epochs: int = 20,
        learning_rate: float = 0.0001,
        unfreeze_blocks: int = 0,
    ) -> Any:
        """Fine-tune a whole detector on your classes. Returns a job id — poll with
        `get_job`.

        Needs the model installed (`install_model`) and a dataset with boxes. This is the
        strong option for detection.

        `unfreeze_blocks` opens the last N backbone blocks. Measured here: 4 blocks cost
        19% more time and moved holdout mAP 0.78 to 0.84 — almost all of it tighter boxes
        rather than more detections. Use it when localisation matters.
        """
        return await client.call(
            "POST",
            "/foundation/finetune",
            json={
                "foundation_id": foundation_id,
                "dataset_ids": dataset_ids,
                "name": name,
                "epochs": epochs,
                "learning_rate": learning_rate,
                "unfreeze_blocks": unfreeze_blocks,
            },
        )

    # --- getting data in and out ------------------------------------------------

    @mcp.tool()
    async def import_coco_dataset(
        name: str, directory: str, copy_images: bool = False
    ) -> Any:
        """Import a COCO or Roboflow export as a new dataset.

        `directory` is an absolute path **on the machine running this app** — the backend
        opens the files itself, there is no upload. A Roboflow COCO export works as
        downloaded.

        Read `skipped_images` and `skipped_boxes` in the response and report them. An
        import that silently dropped half its boxes looks identical to a clean one.
        """
        return await client.call(
            "POST",
            "/datasets/import/coco",
            json={"name": name, "directory": directory, "copy_images": copy_images},
        )

    @mcp.tool()
    async def create_dataset(name: str, copy_images: bool = False) -> Any:
        """Create an empty dataset to save annotations into."""
        return await client.call(
            "POST", "/datasets", json={"name": name, "copy_images": copy_images}
        )

    @mcp.tool()
    async def list_folder_images(path: str) -> Any:
        """List image files directly inside a folder. Absolute path, not recursive."""
        return await client.call("GET", "/annotate/folder", params={"path": path})

    @mcp.tool()
    async def export_dataset(dataset_id: str) -> Any:
        """Write `annotations.coco.json` for a dataset and return its path.

        Standard COCO. A segmented object comes out as one annotation carrying both
        `segmentation` and a `bbox` derived from it — never two.
        """
        return await client.call("POST", f"/datasets/{dataset_id}/export/coco")

    # --- annotating -------------------------------------------------------------

    @mcp.tool()
    async def propose_annotations(
        image_path: str,
        foundation_id: str,
        score_threshold: float = 0.3,
        concept: str = "",
    ) -> Any:
        """Run a model over one image and get proposed boxes back.

        `image_path` is absolute, on this machine. `foundation_id` is a catalogue id or a
        fine-tuned instance id — `list_models` and `list_datasets` will not show the
        latter, `GET /foundation` does.

        `concept` is required for a concept segmenter such as `grounded-sam` (plain text,
        what to look for) and ignored by a plain detector. A concept segmenter also
        returns a `mask` per box.
        """
        payload: dict[str, Any] = {
            "image_path": image_path,
            "foundation_id": foundation_id,
            "score_threshold": score_threshold,
        }
        if concept:
            payload["concept"] = concept
        return await client.call("POST", "/generate/foundation", json=payload)

    @mcp.tool()
    async def save_annotations(
        dataset_id: str,
        path: str,
        width: int,
        height: int,
        boxes: list[dict[str, Any]],
    ) -> Any:
        """Save one image's boxes into a dataset. **Replaces** that image's whole set.

        Each box needs `label`, `provenance`, `x`, `y`, `w`, `h` and — for the class —
        **`prompt`**. The class field is `prompt`, not `text`: send `text` and it is
        silently dropped, every box lands with no class, and a model trained on the result
        collapses every class into one. There is no error.

        `label` is a verdict, not a class: `positive`, `negative` or `unclear`. A
        `negative` box means the region is *not* the thing, which is useful supervision
        rather than a deletion.
        """
        return await client.call(
            "PUT",
            f"/datasets/{dataset_id}/images",
            json={"path": path, "width": width, "height": height, "boxes": boxes},
        )

    @mcp.tool()
    async def run_inference(
        image_path: str,
        backbone_id: str,
        instance_ids: list[str],
        score_threshold: float = 0.3,
        tile_columns: int = 1,
        tile_rows: int = 1,
    ) -> Any:
        """Run trained heads over one image, sharing one backbone pass.

        Set `tile_columns` and `tile_rows` above 1 when the image is much wider than the
        head's `trained_width` (see `list_heads`). Without it a tile-trained head finds
        nothing on a full frame **and the call still succeeds** with an empty list — which
        is indistinguishable from an empty image. Divide the image width by
        `trained_width` for a starting grid.
        """
        payload: dict[str, Any] = {
            "image_path": image_path,
            "backbone_id": backbone_id,
            "instance_ids": instance_ids,
            "score_threshold": score_threshold,
        }
        if tile_columns > 1 or tile_rows > 1:
            payload["tiles"] = {"columns": tile_columns, "rows": tile_rows, "overlap": 0.2}
        return await client.call("POST", "/inference/compose", json=payload)


__all__ = ["JobKind", "register"]
