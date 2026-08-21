"""What every auto-annotator shares when it turns a prediction into a proposal.

Two rules live here rather than in each annotator, because each is the kind of thing that
is easy to get subtly and silently wrong a second time.
"""

from __future__ import annotations

#: Proposals arrive unreviewed. `unclear` would claim the model expressed doubt, and
#: `negative` would assert the object is absent; both are the reviewer's verdict to give,
#: not the model's. `positive` is what a detection means, and the reviewer demotes it.
PROPOSED_LABEL = "positive"


def clamp_to_frame(
    box: tuple[float, float, float, float], width: int, height: int
) -> tuple[float, float, float, float] | None:
    """Trim a proposed box to the image, or return None if nothing is left inside it.

    **Detectors predict boxes that leave the frame**, and legitimately so: an object
    touching an edge continues past it, and the model has no reason to stop at the border.
    Measured on RF-DETR (doc 41) — a `couch` box began at x=0.9 and ran 1.5 px past the
    right edge of a 640×480 image. A head can do it too: `decode_ltrb_to_boxes` regresses
    unbounded distances from a cell centre, so nothing constrains the result to the image.

    `Box` requires `x >= 0` and `fits_within(width, height)`, so an unclamped proposal
    raises on the way into the store — after the user has reviewed it, which is the worst
    moment to lose work.

    **Clamped, not dropped.** An object at the edge of the frame is real, and the visible
    part of it is exactly what a reviewer can judge. Dropping it would quietly lose true
    detections at every border.
    """
    x, y, w, h = box
    left = max(0.0, x)
    top = max(0.0, y)
    right = min(float(width), x + w)
    bottom = min(float(height), y + h)

    # A box entirely outside the frame, or reduced to a line by clamping, describes no
    # pixels the reviewer can look at. `Box` would reject it anyway (`w > 0`, `h > 0`).
    if right <= left or bottom <= top:
        return None
    return (left, top, right - left, bottom - top)


__all__ = ["PROPOSED_LABEL", "clamp_to_frame"]
