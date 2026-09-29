"""Listing a dataset's images (doc 50), with where each sits in its sequence (doc 73).

Split out of ``datasets.py`` when doc 73 pushed that past 300 lines. The seam is the
reading side: everything here answers "what is in this dataset", nothing here writes.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.datasets.models import Box
from app.datasets.sequences import image_frames
from app.datasets.store import DatasetStore

router = APIRouter()


class DatasetImageInfo(BaseModel):
    """One image in a dataset, with the boxes it already carries.

    The boxes ride along rather than needing a call per image: picking a dataset as a
    source means "carry on working on this", so the review surface needs them the moment
    it opens, and fetching them one image at a time would put a request behind every press
    of the Next key. `image_annotations` has already loaded them to answer this query.
    """

    path: str
    width: int
    height: int
    boxes: list[Box]
    #: Doc 73: the video or folder this image is a frame of, and its frame number there.
    #: Both null for a photo.
    sequence: str | None = None
    frame_index: int | None = None


class DatasetImagesResponse(BaseModel):
    dataset_id: str
    images: list[DatasetImageInfo]


@router.get(
    "/datasets/{dataset_id}/images",
    response_model=DatasetImagesResponse,
    summary="List the images in a dataset",
)
async def list_dataset_images(dataset_id: str) -> DatasetImagesResponse:
    """The images a dataset holds, so it can be used as a source (doc 50).

    Returns **stored paths**, which is what every other image route in this app consumes —
    a dataset created with `copy_images` points inside the store, and one created without
    points at wherever the user's files were. Both are absolute and both open the same way,
    so a caller never has to know which kind it is holding.
    """
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    store = DatasetStore()
    frames = image_frames(dataset_id)
    images = []
    for _, path, width, height, boxes in store.image_annotations(dataset_id):
        frame = frames.get(path)
        images.append(
            DatasetImageInfo(
                path=path,
                width=width,
                height=height,
                boxes=boxes,
                sequence=frame.sequence if frame else None,
                frame_index=frame.frame_index if frame else None,
            )
        )
    return DatasetImagesResponse(dataset_id=dataset_id, images=images)
