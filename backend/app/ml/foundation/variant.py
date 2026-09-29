"""A fine-tuned backbone and the head trained with it, run as one model (doc 95).

The variant is its own model: its backbone weights differ from the catalogue's, so a head
trained on the base must never run on it, nor this head on the base (doc 55's 0.000 mAP).
Keeping the pair together, listed under the variant's own id, is what makes that
impossible rather than merely unlikely. It predicts through the same pieces as any head:
the preprocessing plan, the decoder and the payload builder.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import torch
from PIL import Image

from app.core.config import Settings, get_settings
from app.ml.backbone import Backbone, extract, read_capabilities
from app.ml.heads.builders import build_head
from app.ml.heads.decode import decode_for
from app.ml.heads.registry import HeadTypeSpec, get_head_type
from app.ml.inference.payloads import build_payload
from app.ml.inference.results import Prediction
from app.ml.preprocess import apply_geometry, plan_preprocessing, to_pixel_values

logger = logging.getLogger(__name__)

BACKBONE_DIR = "backbone"
HEAD_FILE = "head.pt"


class BackboneVariantModel:
    """Loads once, predicts many times; held by `build.py`'s cache like every foundation."""

    def __init__(self, spec: Any, settings: Settings | None = None) -> None:
        self._spec = spec
        self._settings = settings or get_settings()
        self._loaded: tuple[Backbone, torch.nn.Module, HeadTypeSpec] | None = None

    @property
    def spec(self) -> Any:
        return self._spec

    @property
    def device(self) -> str:
        return str(self._settings.resolved_device)

    def _load(self) -> tuple[Backbone, torch.nn.Module, HeadTypeSpec]:
        if self._loaded is not None:
            return self._loaded
        from transformers import AutoImageProcessor, AutoModel

        head_spec = get_head_type(str(self._spec.variant_head_type))
        if head_spec is None:
            raise LookupError(f"Unknown head type {self._spec.variant_head_type}")
        directory = str(self._spec.weights_dir / BACKBONE_DIR)
        processor = AutoImageProcessor.from_pretrained(directory)  # type: ignore[no-untyped-call]
        model = AutoModel.from_pretrained(directory).to(self.device)
        model.eval()
        capabilities = read_capabilities(self._spec.model_id)
        backbone = Backbone(capabilities, self.device, processor, model)
        extra = 1 if head_spec.task == "segmentation" else 0
        head = build_head(head_spec.id, capabilities, len(self._spec.class_names) + extra)
        weights = torch.load(self._spec.weights_dir / HEAD_FILE, map_location=self.device)
        head.load_state_dict(weights)
        head.to(self.device).eval()
        self._loaded = (backbone, head, head_spec)
        logger.info("Loaded backbone variant %s", self._spec.id)
        return self._loaded

    def predict(self, image: Image.Image, score_threshold: float = 0.3) -> Prediction:
        backbone, head, head_spec = self._load()
        started = time.perf_counter()
        plan = plan_preprocessing(backbone.capabilities, head_spec)
        resized, transform = apply_geometry(plan, image.convert("RGB"))
        with torch.no_grad():
            features = extract(backbone, to_pixel_values(plan, [resized]))
            outputs = head(features)
        decoded = decode_for(head_spec)(outputs, plan.patch_size)
        names = tuple(self._spec.class_names)
        if head_spec.task == "segmentation":
            names = ("background", *names)
        return Prediction(
            instance_id=self._spec.id,
            head_name=self._spec.title,
            head_type_id=head_spec.id,
            task=head_spec.task,
            render_hint=head_spec.render_hint,
            class_names=names,
            payload=build_payload(head_spec, decoded, transform, plan.size, score_threshold),
            grid=features.grid,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )


__all__ = ["BACKBONE_DIR", "HEAD_FILE", "BackboneVariantModel"]
