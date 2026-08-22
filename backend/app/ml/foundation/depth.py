"""Depth Anything V2 — monocular depth from a single image.

Depth Anything **V2**, not V3, and the reason is worth keeping next to the code. V3 has no
`transformers` integration: its `config.json` carries no `architectures` and no
`model_type`, only a bespoke `__object__` block naming `depth_anything_3.model.da3`, so
`AutoModel` cannot open it. Its pip package additionally pins `numpy<2` against this
environment's 2.5.2, and pulls in `open3d`, `evo`, `e3nn` and a second `fastapi`. That is
the SAM 3 / SAM 3.1 decision again and it resolves the same way. See `.mdd/BACKLOG.md`.

The model returns depth at the **source** resolution through its own processor, so none of
this project's letterbox geometry applies — there is no `GeometryTransform` to invert. The
payload is still built by `encode_depth_map`, which is exactly why that was split out: the
overlay renderer must not be able to tell a foundation model's depth map from a trained
head's.
"""

from __future__ import annotations

import logging
import time

import torch
from PIL import Image

from app.core.config import Settings, get_settings
from app.core.paths import is_installed, resolve_model_dir
from app.ml.errors import ModelNotInstalledError
from app.ml.foundation.registry import FoundationSpec
from app.ml.inference.payloads import encode_depth_map
from app.ml.inference.results import Prediction

logger = logging.getLogger(__name__)


class DepthAnythingModel:
    """Loads once, predicts many times. Held by the process-wide cache in `build.py`."""

    def __init__(self, spec: FoundationSpec, settings: Settings | None = None) -> None:
        self._spec = spec
        self._settings = settings or get_settings()
        self._model: torch.nn.Module | None = None
        self._processor: object | None = None

    @property
    def device(self) -> str:
        """The *resolved* device, never the raw setting.

        `Settings.device` defaults to the string ``"auto"``, which torch rejects outright.
        Every other loader goes through `resolved_device`; using the raw field here meant
        the model loaded fine and then failed at `.to("auto")` — reachable only with real
        weights on disk, which is why no unit test saw it.
        """
        return str(self._settings.resolved_device)

    def _load(self) -> tuple[object, torch.nn.Module]:
        if self._processor is not None and self._model is not None:
            return self._processor, self._model

        directory = resolve_model_dir(self._spec.model_id, self._settings)
        if not is_installed(directory):
            # LookupError subclass — the API maps it to 404 with a download hint. Checked
            # before `from_pretrained`, which would otherwise try the network.
            raise ModelNotInstalledError(self._spec.model_id)

        from transformers import AutoImageProcessor, AutoModelForDepthEstimation

        logger.info("Loading %s from %s", self._spec.id, directory)
        # transformers ships no stubs for the Auto* factories.
        processor = AutoImageProcessor.from_pretrained(str(directory))  # type: ignore[no-untyped-call]
        model = AutoModelForDepthEstimation.from_pretrained(str(directory))
        model = model.to(self.device).eval()
        self._processor, self._model = processor, model
        return processor, model

    def predict(self, image: Image.Image) -> Prediction:
        """Depth for one image, in that image's own pixel coordinates."""
        processor, model = self._load()
        started = time.perf_counter()

        inputs = processor(images=image, return_tensors="pt")  # type: ignore[operator]
        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.inference_mode():
            outputs = model(**inputs)

        # The processor maps back to the source size itself, which is why this path needs
        # none of `inference/geometry.py`. `target_sizes` is (height, width) — COCO's
        # order, and the reverse of the (width, height) PIL reports.
        post = processor.post_process_depth_estimation(  # type: ignore[attr-defined]
            outputs, target_sizes=[(image.height, image.width)]
        )
        depth = post[0]["predicted_depth"]

        payload = encode_depth_map(depth.float())
        elapsed = (time.perf_counter() - started) * 1000.0
        logger.info("%s on %s in %.0f ms", self._spec.id, self.device, elapsed)

        return Prediction(
            instance_id=self._spec.id,
            head_name=self._spec.title,
            head_type_id=self._spec.id,
            task=self._spec.task,
            render_hint=self._spec.render_hint,
            # A depth map has no classes. Empty rather than a placeholder, so
            # `Prediction.class_name` never invents one.
            class_names=(),
            payload=payload,
            elapsed_ms=elapsed,
        )


__all__ = ["DepthAnythingModel"]
