"""RF-DETR — general object detection with no prompt and no training (doc 41).

A DINOv2 backbone, a C2f projector and a shallow 2-layer deformable DETR decoder. The
backbone being a DINOv2 is the reason this belongs here rather than being an odd fit: the
project's rule is "freeze the backbone, train what sits on top", and RF-DETR is that rule
with a much stronger head than a linear probe. Doc 44 fine-tunes exactly that way.

Chosen over the alternatives on 2026-08-20: the DINOv2+ViTDet checkpoint ships a bare
detectron2 `.pth` (a pickle, which this project refuses) and both YOLO routes are AGPL-3.0,
parked for Wave 8. See the Wave 7.5 doc.

Like Depth Anything (doc 36), the processor maps predictions back to **source** resolution
itself, so none of `inference/geometry.py` applies. The payload is still assembled by
`source_boxes_payload`, which is why that was split out.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import torch
from PIL import Image

from app.core.config import Settings, get_settings
from app.core.paths import is_installed, resolve_model_dir
from app.ml.errors import ModelNotInstalledError
from app.ml.foundation.registry import FoundationSpec
from app.ml.inference.payloads import source_boxes_payload
from app.ml.inference.results import Prediction

logger = logging.getLogger(__name__)

#: Below this a detection is noise. RF-DETR emits 300 queries per image and most are
#: near-zero; without a floor the payload is 300 boxes of which a handful are real.
DEFAULT_SCORE_THRESHOLD = 0.3


class RfDetrModel:
    """Loads once, predicts many times. Held by the process-wide cache in `build.py`."""

    def __init__(self, spec: FoundationSpec, settings: Settings | None = None) -> None:
        self._spec = spec
        self._settings = settings or get_settings()
        self._model: torch.nn.Module | None = None
        self._processor: object | None = None
        self._class_names: tuple[str, ...] = ()

    @property
    def device(self) -> str:
        """The *resolved* device. `Settings.device` defaults to "auto", which torch rejects."""
        return str(self._settings.resolved_device)

    def _weights_dir(self) -> Path:
        """A fine-tuned model carries its own directory; a catalogue entry resolves one.

        `resolve_model_dir` is still the only way a *catalogue* path is built — doc 02's
        rule — and a fine-tuned instance's directory came from the instance store, which
        confines it the same way.
        """
        if self._spec.weights_dir is not None:
            return self._spec.weights_dir
        return resolve_model_dir(self._spec.model_id, self._settings)

    def _load(self) -> tuple[object, torch.nn.Module]:
        if self._processor is not None and self._model is not None:
            return self._processor, self._model

        directory = self._weights_dir()
        if not is_installed(directory):
            raise ModelNotInstalledError(self._spec.model_id)

        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        logger.info("Loading %s from %s", self._spec.id, directory)
        # transformers ships no stubs for the Auto* factories.
        processor = AutoImageProcessor.from_pretrained(str(directory))  # type: ignore[no-untyped-call]
        model = AutoModelForObjectDetection.from_pretrained(str(directory))
        model = model.to(self.device).eval()

        # Read the class names off the checkpoint rather than shipping a parallel list.
        # Wave 3 left the ImageNet classifier rendering "class 416" instead of a name
        # precisely because its names lived somewhere the loader did not look.
        # A fine-tuned model's classes are the user's, recorded at save time; a catalogue
        # model's are COCO's, recorded in its config.
        if self._spec.class_names:
            self._class_names = self._spec.class_names
        id2label = getattr(model.config, "id2label", None) or {}
        if id2label and not self._class_names:
            self._class_names = tuple(
                str(id2label.get(index, f"class {index}"))
                for index in range(max(int(k) for k in id2label) + 1)
            )

        self._processor, self._model = processor, model
        return processor, model

    def retarget(self, num_classes: int, class_names: tuple[str, ...] = ()) -> None:
        """Re-open the classifier for a different set of classes (doc 44).

        Reloaded through `from_pretrained(..., ignore_mismatched_sizes=True)` rather than by
        swapping the final layer by hand: that is the sanctioned path, it keeps every other
        weight exactly as it was, and it fails loudly if the checkpoint and the requested
        shape disagree in a way that is *not* just the class count.

        The COCO head is discarded on purpose. Its 91 classes are not the user's, and
        keeping them would mean a detector that answers `cake` on a chessboard even after
        being shown what a chess piece is.
        """
        directory = self._weights_dir()
        if not is_installed(directory):
            raise ModelNotInstalledError(self._spec.model_id)

        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        self._processor = AutoImageProcessor.from_pretrained(str(directory))  # type: ignore[no-untyped-call]
        model = AutoModelForObjectDetection.from_pretrained(
            str(directory), num_labels=num_classes, ignore_mismatched_sizes=True
        )
        self._model = model.to(self.device)
        self._class_names = class_names or tuple(f"class {i}" for i in range(num_classes))

    @property
    def model(self) -> torch.nn.Module:
        """The loaded module. Loads on first access, as `predict` does."""
        _, model = self._load()
        return model

    @property
    def processor(self) -> object:
        processor, _ = self._load()
        return processor

    @property
    def class_names(self) -> tuple[str, ...]:
        """Available after the first load; empty before it."""
        return self._class_names

    def predict(
        self, image: Image.Image, score_threshold: float = DEFAULT_SCORE_THRESHOLD
    ) -> Prediction:
        """Boxes for one image, in that image's own pixel coordinates."""
        processor, model = self._load()
        started = time.perf_counter()

        inputs = processor(images=image, return_tensors="pt")  # type: ignore[operator]
        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.inference_mode():
            outputs = model(**inputs)

        # `target_sizes` is (height, width) — the reverse of the (width, height) PIL reports.
        results = processor.post_process_object_detection(  # type: ignore[attr-defined]
            outputs, threshold=score_threshold, target_sizes=[(image.height, image.width)]
        )[0]

        payload = source_boxes_payload(*_as_xywh(results))
        elapsed = (time.perf_counter() - started) * 1000.0
        logger.info(
            "%s found %d object(s) on %s in %.0f ms",
            self._spec.id,
            len(payload["boxes"]),  # type: ignore[arg-type]
            self.device,
            elapsed,
        )

        return Prediction(
            instance_id=self._spec.id,
            head_name=self._spec.title,
            head_type_id=self._spec.id,
            task=self._spec.task,
            render_hint=self._spec.render_hint,
            class_names=self._class_names,
            payload=payload,
            elapsed_ms=elapsed,
        )


def _as_xywh(
    results: dict[str, torch.Tensor],
) -> tuple[list[tuple[float, float, float, float]], list[float], list[int]]:
    """Convert the processor's corner boxes to this project's xywh convention.

    `post_process_object_detection` returns **xyxy**; the dataset store, the overlay
    renderer and `Prediction.boxes` all speak **xywh** with a top-left origin. Converting
    here, once, is what stops a corner pair reaching a consumer that reads it as a size.
    """
    boxes: list[tuple[float, float, float, float]] = []
    for corner in results["boxes"].detach().cpu().tolist():
        x_min, y_min, x_max, y_max = (float(value) for value in corner)
        boxes.append((x_min, y_min, x_max - x_min, y_max - y_min))

    scores = [float(value) for value in results["scores"].detach().cpu().tolist()]
    classes = [int(value) for value in results["labels"].detach().cpu().tolist()]
    return boxes, scores, classes


__all__ = ["DEFAULT_SCORE_THRESHOLD", "RfDetrModel"]
