"""Importing any dataset folder or video, for an assistant (doc 136).

Same rules as `tools.py`: task-shaped, and the docstring is the prompt.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.mcpserver import MCPServer

from app.mcp import client

#: An import of tens of thousands of pictures takes minutes; the tool waits that long.
_WAIT_SECONDS = 1800
_POLL_SECONDS = 2.0


def register(mcp: MCPServer) -> None:
    """Attach the import tools. Called by `server.build`."""

    @mcp.tool()
    async def detect_dataset(path: str) -> Any:
        """What a folder (or a video file) holds, **before** importing it. Writes nothing.

        Recognises COCO (any JSON with images/annotations/categories, with train/valid/test
        folders as splits), YOLO (`labels/*.txt` plus `data.yaml` or `classes.txt`; polygon
        lines become masks), Pascal VOC (`Annotations/*.xml`), OpenLABEL (OSDaR23), plain
        pictures, and video. Reports pictures, annotated pictures, objects, classes,
        annotation types and anything doubtful in `notes`; show those to the user.

        `path` is an absolute path **on the machine running this app**; there is no upload.
        """
        return await client.call("POST", "/datasets/import/detect", json={"path": path})

    @mcp.tool()
    async def import_dataset(
        path: str, name: str = "", description: str | None = None, copy_images: bool = False
    ) -> Any:
        """Import a folder or video as a new dataset, and wait until it is done. Run
        `detect_dataset` first and tell the user what it found.

        `name` defaults to the folder's name; `description` is stored with the dataset.
        `copy_images` copies the pictures into the app's data folder (otherwise they are
        referenced where they are, and must stay there).

        Pictures without annotations (and video frames) arrive *unannotated*: they are not
        used for training until someone saves them in the Studio. Report `skipped_pictures`
        and `skipped_objects`; a lossy import looks like a clean one otherwise.
        """
        job = await client.call(
            "POST",
            "/datasets/import",
            json={
                "path": path,
                "name": name,
                "description": description,
                "copy_images": copy_images,
            },
        )
        waited = 0.0
        while job["state"] == "running" and waited < _WAIT_SECONDS:
            await asyncio.sleep(_POLL_SECONDS)
            waited += _POLL_SECONDS
            job = await client.call("GET", f"/datasets/import/jobs/{job['job_id']}")
        return job

    @mcp.tool()
    async def get_dataset_profile(dataset_id: str) -> Any:
        """A dataset's parameters: created, images or video, pictures, annotated pictures,
        sequences, classes, annotation types, description and where it was imported from."""
        return await client.call("GET", f"/datasets/{dataset_id}/profile")
