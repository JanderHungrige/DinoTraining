"""Playing a frame sequence with its annotations (doc 68).

Four things a player needs: what the source *is*, one frame's pixels, a prepass over a
range, and that prepass's progress. Nothing here streams — a video is served frame by
frame, because the frame on screen and the frame the model analysed have to be the same
one and a `<video>` element cannot promise that.
"""

from __future__ import annotations

import io
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from app.api.v1.inference import PredictionResponse, describe
from app.ml.images import FolderNotFoundError, ImageReadError
from app.ml.inference.engine import DEFAULT_SCORE_THRESHOLD
from app.ml.video.decode import VideoReadError
from app.ml.video.runner import SequenceRun, SequenceRunConfig, get_runner
from app.ml.video.sequence import FrameSequence, frame_image, open_sequence

logger = logging.getLogger(__name__)
router = APIRouter()


class SequenceInfo(BaseModel):
    """What a player needs before it can offer a range."""

    source: str
    kind: str
    frames: int
    #: `null` for a folder, which has no frame rate. Not defaulted to 30: a made-up number
    #: here drives a playback speed nobody chose.
    fps: float | None
    duration: float | None
    width: int
    height: int


class SequenceRunRequest(BaseModel):
    source: str = Field(min_length=1)
    start: int = Field(default=0, ge=0)
    #: Capped, and the cap is a kindness rather than a limitation: at Grounded SAM's ~5 s
    #: per frame, 5000 frames is seven hours. Someone who wants more runs a second range.
    count: int = Field(default=60, ge=1, le=5000)
    backbone_id: str = ""
    instance_ids: list[str] = Field(default_factory=list)
    foundation_ids: list[str] = Field(default_factory=list)
    concept: str = Field(default="", max_length=500)
    score_threshold: float = Field(default=DEFAULT_SCORE_THRESHOLD, ge=0.0, le=1.0)


class FramePredictions(BaseModel):
    index: int
    predictions: list[PredictionResponse]


class SequenceRunResponse(BaseModel):
    job_id: str
    state: str
    done: int
    total: int
    unreadable: int
    message: str
    start: int
    #: Only the frames asked for, so polling does not re-send the whole run every second.
    frames: list[FramePredictions] = Field(default_factory=list)


def _open(source: str) -> FrameSequence:
    """Resolve a source, turning every failure into the status it deserves."""
    try:
        return open_sequence(source)
    except FolderNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except (VideoReadError, ImageReadError) as error:
        raise HTTPException(status_code=415, detail=str(error)) from None


@router.get("/video/probe", response_model=SequenceInfo, summary="Inspect a folder or video")
async def probe_source(path: str = Query(min_length=1)) -> SequenceInfo:
    sequence = _open(path)
    return SequenceInfo(
        source=sequence.source,
        kind=sequence.kind,
        frames=sequence.frames,
        fps=sequence.fps,
        duration=sequence.duration,
        width=sequence.width,
        height=sequence.height,
    )


@router.get("/video/frame", summary="One frame of a folder or video")
async def get_frame(
    path: str = Query(min_length=1), index: int = Query(ge=0)
) -> Response:
    """The webview cannot load file:// URLs, and a video frame has no file at all."""
    sequence = _open(path)
    if not 0 <= index < sequence.frames:
        raise HTTPException(
            status_code=404, detail=f"Frame {index} is outside 0..{sequence.frames - 1}"
        )

    # Frames are immutable for a given (path, index), so let the webview keep them —
    # scrubbing backwards is otherwise a re-fetch, and for a video a re-decode, per frame.
    cacheable = {"Cache-Control": "private, max-age=3600"}

    # **A folder frame is already a file: send it.** Decoding it with PIL and re-encoding
    # it as PNG cost ~120 ms and ~320 KB per frame, which is more than the 100 ms budget a
    # 10 fps playback has — so the `<img>` never finished loading before the next frame was
    # asked for, and the browser kept showing the last one that had. Measured live: the
    # index advanced 1,3,5,7,9,11 while `img.complete` stayed false throughout, which looks
    # exactly like playback not working at all.
    if sequence.kind == "folder":
        return FileResponse(sequence.paths[index], headers=cacheable)

    try:
        image = frame_image(sequence, index)
    except IndexError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except (VideoReadError, ImageReadError, OSError) as error:
        raise HTTPException(status_code=415, detail=str(error)) from None

    buffer = io.BytesIO()
    # JPEG, not PNG: a video frame came from a lossy codec already, so PNG spends two to
    # three times the bytes preserving detail the source never had. The overlays are drawn
    # in the browser and are unaffected.
    image.save(buffer, format="JPEG", quality=88)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/jpeg", headers=cacheable)


def _describe(run: SequenceRun, since: int, until: int) -> SequenceRunResponse:
    """A run's progress, plus whichever finished frames were asked for."""
    wanted = range(since, until) if until > since else range(0)
    frames = [
        FramePredictions(
            index=index,
            predictions=[describe(prediction) for prediction in run.frames[index]],
        )
        for index in wanted
        if index in run.frames
    ]
    return SequenceRunResponse(
        job_id=run.job_id,
        state=run.state,
        done=run.done,
        total=run.total,
        unreadable=run.unreadable,
        message=run.message,
        start=run.config.start,
        frames=frames,
    )


@router.post(
    "/video/runs",
    response_model=SequenceRunResponse,
    status_code=202,
    summary="Run the chosen models over a range of frames",
)
async def start_run(request: SequenceRunRequest) -> SequenceRunResponse:
    """Returns immediately with a job id. A 120-frame range is minutes, not a request."""
    sequence = _open(request.source)
    try:
        config = SequenceRunConfig(
            source=request.source,
            start=request.start,
            count=request.count,
            backbone_id=request.backbone_id,
            instance_ids=tuple(request.instance_ids),
            foundation_ids=tuple(request.foundation_ids),
            concept=request.concept,
            score_threshold=request.score_threshold,
        )
        run = get_runner().submit(sequence, config)
    except ValueError as error:
        # Covers both an empty selection and a start past the end — a malformed request
        # either way, and the message names which.
        raise HTTPException(status_code=422, detail=str(error)) from None

    return _describe(run, 0, 0)


@router.get(
    "/video/runs/{job_id}",
    response_model=SequenceRunResponse,
    summary="Progress, and the frames finished so far",
)
async def get_run(
    job_id: str,
    since: int = Query(default=0, ge=0),
    until: int = Query(default=0, ge=0),
) -> SequenceRunResponse:
    """`since`/`until` bound which frames come back.

    Without them a poll returns every finished frame every second, and a 500-frame run
    with masks re-sends megabytes of PNG the player already has.
    """
    run = get_runner().get(job_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No such run: {job_id}")
    return _describe(run, since, until)


@router.delete("/video/runs/{job_id}", summary="Stop a run, keeping what it finished")
async def cancel_run(job_id: str) -> SequenceRunResponse:
    runner = get_runner()
    run = runner.get(job_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No such run: {job_id}")
    runner.cancel(job_id)
    return _describe(run, 0, 0)


__all__ = ["router"]
