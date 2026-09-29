"""Listing a dataset's images (doc 50), with where each sits in its sequence (doc 73).

Split out of ``datasets.py`` when doc 73 pushed that past 300 lines. The seam is the
reading side: everything here answers "what is in this dataset", nothing here writes.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.datasets.models import Box
from app.datasets.sequences import SequenceFrame, dataset_sequences, image_frames
from app.datasets.store import DatasetStore, dataset_dir

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


class SequenceFrameInfo(BaseModel):
    index: int
    path: str
    #: False for a frame that exists on disk but was never saved (nothing found there).
    annotated: bool
    #: Classes with a positive box or mask on this frame. What the timeline draws.
    classes: list[str]


class SequenceInfo(BaseModel):
    source: str
    kind: str
    frames: list[SequenceFrameInfo]


class DatasetSequencesResponse(BaseModel):
    dataset_id: str
    #: Every class that appears anywhere, sorted: one index per class, so a colour means
    #: the same class in every sequence of the dataset.
    class_names: list[str]
    sequences: list[SequenceInfo]
    #: Images that are not frames of anything, in the order they were saved.
    loose: list[SequenceFrameInfo]


@router.get(
    "/datasets/{dataset_id}/sequences",
    response_model=DatasetSequencesResponse,
    summary="A dataset's videos and folders, each complete and in order (docs 74, 75)",
)
async def list_dataset_sequences(dataset_id: str) -> DatasetSequencesResponse:
    """Frames per sequence with the classes annotated on each.

    Complete, not only the annotated frames: autoplay saves nothing where nothing was
    found, and playing the saved frames alone would cut every empty stretch out of the
    video. The rest are merged back from disk, unannotated.
    """
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    sequences, loose = dataset_sequences(dataset_id, dataset_dir(dataset_id))

    def frame_info(frame: SequenceFrame) -> SequenceFrameInfo:
        return SequenceFrameInfo(
            index=frame.index, path=frame.path, annotated=frame.annotated, classes=frame.classes
        )

    names = sorted(
        {name for sequence in sequences for frame in sequence.frames for name in frame.classes}
        | {name for frame in loose for name in frame.classes}
    )
    return DatasetSequencesResponse(
        dataset_id=dataset_id,
        class_names=names,
        sequences=[
            SequenceInfo(
                source=sequence.source,
                kind=sequence.kind,
                frames=[frame_info(frame) for frame in sequence.frames],
            )
            for sequence in sequences
        ],
        loose=[frame_info(frame) for frame in loose],
    )
