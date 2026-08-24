"""Fine-tuning RF-DETR on the user's own dataset (doc 44).

**This is the project's founding rule, not an exception to it.** RF-DETR's backbone *is* a
DINOv2, so "freeze the backbone, train what sits on top" applies unchanged — 23.5M frozen
parameters and 8.4M trained. The difference from the Head Trainer is what sits on top: a
projector and a deformable DETR decoder rather than a linear probe, which is why it starts
from COCO-pretrained detection weights and needs far less data to become good.

Two things it deliberately does not share with `training/runner.py`:

* **No feature cache.** That runner's payoff is that a frozen backbone yields identical
  features every epoch, so one pass replaces N. Here the trained part consumes multi-level
  features through a projector, so the whole model runs every step. Training is minutes,
  not seconds, and the UI should say so.
* **No `HeadTypeSpec`.** A fine-tuned RF-DETR is not a head — it has no backbone id to be
  composed against and cannot join `run_heads`' shared pass. It is a *foundation model you
  trained*, and it is stored and listed as one.

Metrics come from `detection_metrics`, the same function the Head Trainer reports, so the
numbers are directly comparable to a trained head's on the same data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import torch
from PIL import Image

from app.core.config import Settings, get_settings
from app.datasets.store import DatasetStore
from app.ml.foundation.build import build_foundation
from app.ml.foundation.detect import RfDetrModel
from app.ml.training.config import split_indices
from app.ml.training.metrics import detection_metrics
from app.ml.training.samples import TrainingSample, build_samples
from app.ml.training.unfreeze import unfreeze_last_blocks

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FinetuneConfig:
    """One fine-tuning run. Immutable, for the same reason `TrainingConfig` is: a config
    that changes mid-run makes the saved provenance a lie."""

    foundation_id: str
    dataset_ids: tuple[str, ...]
    name: str
    #: Far fewer than the Head Trainer's 20. Every epoch is a full forward *and* backward
    #: through 32M parameters, and a COCO-pretrained decoder adapts in a handful.
    epochs: int = 10
    #: An order of magnitude below the head trainer's 1e-3: this is fine-tuning weights
    #: that already work, not fitting a probe from scratch.
    learning_rate: float = 1e-4
    weight_decay: float = 1e-4
    batch_size: int = 2
    val_fraction: float = 0.2
    split_seed: int = 42
    #: How many of the DINOv2 backbone's **last** blocks to train alongside the decoder
    #: (doc 55). 0 keeps doc 44's founding-rule behaviour; -1 trains the whole backbone.
    #:
    #: **Correct here and refused for heads**, and the difference is not policy: this path
    #: saves the *whole model* with `save_pretrained`, so a modified backbone is persisted
    #: with everything else. A head stores only its own weights beside a `backbone_id`, so
    #: the same change there produces a head that scores 0.000 in a fresh process.
    unfreeze_blocks: int = 0
    #: Backbone rate as a fraction of the decoder's. A pretrained ViT nudged, not fitted.
    backbone_lr_scale: float = 0.1

    def __post_init__(self) -> None:
        if not self.dataset_ids:
            raise ValueError("At least one dataset is required")
        if self.epochs < 1:
            raise ValueError(f"epochs must be >= 1, got {self.epochs}")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be > 0, got {self.learning_rate}")
        if not 0.0 <= self.val_fraction < 1.0:
            raise ValueError(f"val_fraction must be in [0, 1), got {self.val_fraction}")
        if not self.name.strip():
            raise ValueError("A fine-tuned model needs a name")
        if self.unfreeze_blocks < -1:
            raise ValueError(
                f"unfreeze_blocks must be -1 (all), 0 (none) or a positive count, "
                f"got {self.unfreeze_blocks}"
            )
        if not 0.0 < self.backbone_lr_scale <= 1.0:
            raise ValueError(
                f"backbone_lr_scale must be in (0, 1], got {self.backbone_lr_scale}"
            )


@dataclass(frozen=True, slots=True)
class FinetuneEpoch:
    epoch: int
    train_loss: float
    metrics: dict[str, float] = field(default_factory=dict)


def freeze_backbone(model: torch.nn.Module, unfreeze_blocks: int = 0) -> tuple[int, int]:
    """Freeze the DINOv2 backbone, optionally leaving its last blocks trainable (doc 55).

    Returns (frozen, trainable) parameter counts. Returned rather than logged only, because
    "did it actually freeze?" is the question this whole feature rests on and a silent
    no-op looks exactly like a slow success.

    `unfreeze_blocks` is safe here in a way it is not for heads: `save_pretrained` writes
    the whole model, so a modified backbone travels with the decoder that was fitted
    against it.
    """
    # torch types every submodule as `Tensor | Module`, so this narrows once rather than
    # scattering ignores. A missing backbone means the model is not what doc 41 registered,
    # and failing here beats "training" 32M parameters that were never frozen.
    backbone = model.get_submodule("model.backbone")
    for parameter in backbone.parameters():
        parameter.requires_grad_(False)

    if unfreeze_blocks != 0:
        # RF-DETR nests its DINOv2 one level deeper, under the C2f projector's encoder.
        # Same `encoder.layer` shape, same addressing rule as a catalogue backbone.
        opened = unfreeze_last_blocks(backbone.get_submodule("backbone"), unfreeze_blocks)
        logger.info("Unfroze %d backbone block(s) for fine-tuning", opened)

    frozen = sum(
        int(p.numel()) for p in backbone.parameters() if not bool(p.requires_grad)
    )
    trainable = sum(int(p.numel()) for p in model.parameters() if bool(p.requires_grad))
    return frozen, trainable


def to_detr_labels(
    sample: TrainingSample, device: str | torch.device
) -> dict[str, torch.Tensor]:
    """One image's boxes in DETR's convention: **normalised cxcywh**.

    The dataset store speaks absolute xywh from the top-left, and DETR wants centre-relative
    fractions of the image. Converting here, once, is what stops a corner reaching a loss
    that reads it as a centre — which trains without complaint and predicts nonsense.
    """
    boxes: list[list[float]] = []
    classes: list[int] = []
    for class_index, x, y, w, h in sample.targets:
        if w <= 0 or h <= 0:
            continue
        boxes.append(
            [
                (x + w / 2) / sample.width,
                (y + h / 2) / sample.height,
                w / sample.width,
                h / sample.height,
            ]
        )
        classes.append(class_index)

    return {
        "class_labels": torch.tensor(classes, dtype=torch.long, device=device),
        "boxes": torch.tensor(boxes, dtype=torch.float32, device=device).reshape(-1, 4),
    }


def load_samples(
    store: DatasetStore, config: FinetuneConfig
) -> tuple[list[TrainingSample], list[TrainingSample], tuple[str, ...]]:
    """Training and validation samples, split **by image** with the configured seed.

    By image, not by box: boxes from one image landing in both splits is leakage that
    inflates validation with no visible symptom — doc 11's rule, and it applies here for
    exactly the same reason.
    """
    sample_set = build_samples(store, config.dataset_ids)
    usable = [s for s in sample_set.samples if s.targets]
    if not usable:
        raise ValueError("No positive boxes found in the selected datasets — nothing to learn")

    split = split_indices(len(usable), config.val_fraction, 0.0, config.split_seed)
    train = [usable[i] for i in split.train]
    validation = [usable[i] for i in split.val]
    return train, validation, sample_set.class_names


def evaluate(model: RfDetrModel, samples: list[TrainingSample]) -> dict[str, float]:
    """mAP over the validation split, through the same metric the Head Trainer reports."""
    outputs: list[dict[str, torch.Tensor]] = []
    targets: list[dict[str, torch.Tensor]] = []

    for sample in samples:
        with Image.open(sample.path) as opened:
            prediction = model.predict(opened.convert("RGB"), score_threshold=0.05)
        payload = prediction.payload
        outputs.append(
            {
                "boxes": torch.tensor(payload["boxes"], dtype=torch.float32).reshape(-1, 4),
                "scores": torch.tensor(payload["scores"], dtype=torch.float32).reshape(-1),
                "classes": torch.tensor(payload["classes"], dtype=torch.long).reshape(-1),
            }
        )
        targets.append(
            {
                "boxes": torch.tensor(
                    [[x, y, w, h] for _, x, y, w, h in sample.targets], dtype=torch.float32
                ).reshape(-1, 4),
                "classes": torch.tensor(
                    [c for c, *_ in sample.targets], dtype=torch.long
                ).reshape(-1),
            }
        )

    return detection_metrics(outputs, targets)


def prepared_model(
    foundation_id: str,
    num_classes: int,
    class_names: tuple[str, ...] = (),
    settings: Settings | None = None,
) -> RfDetrModel:
    """Load the detector and re-open its classifier for the user's own classes."""
    settings = settings or get_settings()
    # `fresh`: this retargets the classifier and then rewrites the weights, and doing that
    # to the cached instance would make every later request for the base model return the
    # fine-tune instead — with its classes and its scores, which looks like a result.
    model = build_foundation(foundation_id, settings, fresh=True)
    if not isinstance(model, RfDetrModel):
        raise ValueError(f"{foundation_id} is not a detector and cannot be fine-tuned")
    model.retarget(num_classes, class_names)
    return model


__all__ = [
    "FinetuneConfig",
    "FinetuneEpoch",
    "evaluate",
    "freeze_backbone",
    "load_samples",
    "prepared_model",
    "to_detr_labels",
]
