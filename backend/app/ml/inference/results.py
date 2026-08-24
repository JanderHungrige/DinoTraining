"""What one head predicted for one image, in the original image's coordinates.

The cross-feature contract for Wave 3. `20-inference-overlay-render` dispatches off
``render_hint`` and never re-derives what to draw from the task string;
`21-same-task-head-compare` groups these by task; the API serialises one shape.

Payloads are plain Python — lists and floats, no tensors — because every consumer is
either JSON or a renderer. Keeping torch out of this type is what stops a tensor with a
live device reference leaking into a response.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ml.heads.registry import RenderHint

#: xywh in absolute source-image pixels, top-left origin — the dataset store's
#: convention, so a prediction can become an annotation in Wave 4 without conversion.
Box = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class Prediction:
    """One head's output for one image. Immutable; built once by the engine."""

    instance_id: str
    head_name: str
    head_type_id: str
    task: str
    render_hint: RenderHint
    #: Training class order. Index N here is index N in the payload's class indices.
    class_names: tuple[str, ...]
    #: Shape depends on render_hint — see the properties below for the readers.
    payload: dict[str, object] = field(default_factory=dict)
    #: Patch grid the head actually ran at, for diagnostics.
    grid: tuple[int, int] = (0, 0)
    elapsed_ms: float = 0.0

    @property
    def summary(self) -> str:
        """One line describing what was predicted, for logs and the compare panel.

        Built from the payload rather than the head, so two heads on the same image
        produce comparable lines.
        """
        if self.render_hint == "labels":
            top = self.top_labels(1)
            if top:
                name, score = top[0]
                return f"{name} ({score:.2f})"
            return "no prediction"
        if self.render_hint == "boxes":
            count = len(self.boxes)
            return f"{count} object{'' if count == 1 else 's'}"
        if self.render_hint == "masks":
            return f"{len(self.mask_classes)} classes present"
        return "depth map"

    # --- typed readers ------------------------------------------------------------
    #
    # The payload is a dict so it can be serialised directly, but every consumer
    # reading it by raw key is how the shapes drift. These are the sanctioned readers.

    def top_labels(self, count: int = 5) -> list[tuple[str, float]]:
        """Highest-scoring classes, as (name, score). Empty for non-label heads."""
        scores = self.payload.get("scores")
        if not isinstance(scores, list):
            return []
        ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
        return [(self.class_name(index), float(score)) for index, score in ranked[:count]]

    @property
    def boxes(self) -> list[Box]:
        raw = self.payload.get("boxes")
        if not isinstance(raw, list):
            return []
        return [(float(b[0]), float(b[1]), float(b[2]), float(b[3])) for b in raw]

    def detections(self) -> list[tuple[Box, float, str]]:
        """Boxes with their score and class name, as ``(box, score, name)``.

        The three payload arrays are read positionally and are only meaningful together —
        ``boxes_payload`` drops a zero-area box from all three at once precisely so they
        stay aligned. Zipping them here, once, is what stops a consumer pairing box *i*
        with score *j*. Wave 4's annotator needs all three; the viewer needs only the box,
        which is why :attr:`boxes` still exists.
        """
        boxes = self.boxes
        raw_scores = self.payload.get("scores")
        raw_classes = self.payload.get("classes")
        scores = raw_scores if isinstance(raw_scores, list) else []
        classes = raw_classes if isinstance(raw_classes, list) else []
        if len(scores) != len(boxes) or len(classes) != len(boxes):
            # Not a recoverable state: it means the payload was built by something other
            # than boxes_payload, and guessing an alignment would silently mislabel.
            return []
        return [
            (box, float(score), self.class_name(int(index)))
            for box, score, index in zip(boxes, scores, classes, strict=True)
        ]

    @property
    def mask_classes(self) -> set[int]:
        """Distinct class indices present in a predicted mask."""
        raw = self.payload.get("present_classes")
        return set(raw) if isinstance(raw, list) else set()

    def class_name(self, index: int) -> str:
        """Name for a class index, or a stable placeholder.

        A pretrained default carries 1000 ImageNet ids with no names attached, and the
        viewer must still render something rather than crashing on an index error.
        """
        if 0 <= index < len(self.class_names):
            return self.class_names[index]
        return f"class {index}"
