"""Training configuration and deterministic dataset splitting.

Defaults are chosen so a user can press Train without deciding anything, per the wave's
demo-state. ``augment`` defaults to off because that is what lets the runner cache
backbone features — see :mod:`app.ml.training.runner`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """One training run. Immutable: a config that changes mid-run makes the saved
    provenance a lie."""

    head_type_id: str
    backbone_id: str
    dataset_ids: tuple[str, ...]

    epochs: int = 20
    batch_size: int = 16
    # A linear head on frozen features tolerates a far higher lr than end-to-end
    # fine-tuning would; 1e-3 converges in a handful of epochs on small datasets.
    learning_rate: float = 1e-3
    weight_decay: float = 0.01

    val_fraction: float = 0.2
    test_fraction: float = 0.1
    split_seed: int = 42

    save_best_only: bool = True
    early_stopping_patience: int = 5
    augment: bool = False
    #: How many of the backbone's **last** transformer blocks to train alongside the head
    #: (doc 55). 0 keeps the founding rule and the feature cache; -1 means the whole
    #: backbone. A ViT's later blocks carry the most task-specific representation, and the
    #: early ones carry general structure a few hundred images cannot improve.
    unfreeze_blocks: int = 0
    #: Backbone learning rate as a fraction of the head's. A backbone that already works is
    #: being nudged; at the head's own rate a few hundred images destroy it in one epoch and
    #: the run reports a worse number than the frozen one it was meant to beat.
    backbone_lr_scale: float = 0.1

    def __post_init__(self) -> None:
        if not self.dataset_ids:
            raise ValueError("At least one dataset is required")
        if self.epochs < 1:
            raise ValueError(f"epochs must be >= 1, got {self.epochs}")
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be > 0, got {self.learning_rate}")
        if not 0.0 <= self.val_fraction < 1.0:
            raise ValueError(f"val_fraction must be in [0, 1), got {self.val_fraction}")
        if not 0.0 <= self.test_fraction < 1.0:
            raise ValueError(f"test_fraction must be in [0, 1), got {self.test_fraction}")
        if self.val_fraction + self.test_fraction >= 1.0:
            # Otherwise the training split is empty and the run fails several minutes
            # later with a confusing "no samples" error instead of here.
            raise ValueError(
                f"val_fraction + test_fraction must leave a training split, got "
                f"{self.val_fraction} + {self.test_fraction}"
            )
        if self.early_stopping_patience < 1:
            raise ValueError("early_stopping_patience must be >= 1")
        if self.unfreeze_blocks != 0:
            # Refused, not merely warned about. Measured on 2026-08-21: a head trained
            # against an unfrozen backbone scored **0.000 mAP** in a fresh process, because
            # a `HeadInstance` stores head weights plus a `backbone_id` — there is nowhere
            # to put a modified backbone, so the weights the head was fitted against are
            # discarded when the process ends. The run reports a plausible validation
            # number and produces a head that cannot work.
            #
            # See doc 55: this is not a missing flag, it is what "head" means here. A head
            # that carries its own backbone cannot join `run_heads`' shared pass and is a
            # foundation model — which is exactly why RF-DETR is not a head. Unfreezing
            # lives on the fine-tune path, where the whole model is saved.
            raise ValueError(
                "Training the backbone is not supported for heads: a head stores only its "
                "own weights, so a modified backbone would be discarded and the head would "
                "predict nothing. Fine-tune a detector instead — see the Head Trainer's "
                "fine-tuning panel."
            )
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
class Split:
    """Index sets for one dataset split."""

    train: tuple[int, ...] = field(default=())
    val: tuple[int, ...] = field(default=())
    test: tuple[int, ...] = field(default=())


def split_indices(
    count: int, val_fraction: float, test_fraction: float, seed: int
) -> Split:
    """Deterministically split ``count`` **images** into train/val/test.

    Splitting by image rather than by box is not a detail: boxes from one image landing
    in both train and val is leakage that inflates validation metrics with no visible
    symptom, so the run looks better than the model is.

    Validation and test are guaranteed at least one sample when their fraction is
    non-zero and the dataset is large enough — a rounded-to-zero val split silently
    disables both early stopping and best-model selection.
    """
    if count <= 0:
        return Split()

    indices = list(range(count))
    random.Random(seed).shuffle(indices)

    val_size = int(round(count * val_fraction))
    test_size = int(round(count * test_fraction))
    if val_fraction > 0:
        val_size = max(1, val_size)
    if test_fraction > 0:
        test_size = max(1, test_size)

    # Training always keeps at least one sample; trimming comes off test first, since
    # test is only reported at the end while val drives stopping decisions.
    while count - val_size - test_size < 1 and (test_size > 0 or val_size > 0):
        if test_size > 0:
            test_size -= 1
        else:
            val_size -= 1

    val = tuple(indices[:val_size])
    test = tuple(indices[val_size : val_size + test_size])
    train = tuple(indices[val_size + test_size :])
    return Split(train=train, val=val, test=test)
