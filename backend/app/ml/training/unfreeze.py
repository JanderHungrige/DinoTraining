"""Training some of the backbone, not just the head (doc 55).

**The project's founding rule is that the backbone stays frozen, and this does not repeal
it — it makes the rule a choice.** Freezing is what buys the feature cache: a frozen
backbone yields identical features every epoch, so one pass replaces N and a head trains in
seconds. That trade is right when seconds matter.

It stops being right when quality matters more, which is what doc 49 measured: on far-field
rail objects a trained head reached 0.339 mAP where a fine-tuned RF-DETR reached 0.857 —
and the gap was in *finding*, not placing (mAP@50 0.399 against 0.979). DINOv2's frozen
patch features simply do not separate a 10 px signal from vegetation. Nothing a head does on
top of those features recovers that; the features have to change.

Unfreezing the **last N blocks** rather than all of them is the useful middle: a ViT's later
blocks carry the most task-specific representation, and the early ones carry general
structure that a few hundred images cannot improve and can easily damage.
"""

from __future__ import annotations

import logging

import torch
from torch import nn

from app.ml.backbone import Backbone

logger = logging.getLogger(__name__)

#: Backbone learning rate as a fraction of the head's. A backbone that already works is
#: being nudged, not fitted; at the head's rate a few hundred images destroy it in one epoch.
DEFAULT_BACKBONE_LR_SCALE = 0.1

#: `unfreeze_blocks` value meaning "the whole backbone".
ALL_BLOCKS = -1


class BackboneNotUnfreezableError(ValueError):
    """The backbone has no block list this module knows how to address.

    Raised rather than silently training nothing. A backbone whose blocks cannot be found
    would otherwise report a successful unfreeze of zero parameters, which looks exactly
    like a slow run — the same failure `freeze_backbone` was written to make impossible.
    """


def blocks_in(module: nn.Module) -> nn.ModuleList:
    """The transformer blocks of any DINOv2-shaped module, innermost-last.

    Takes a module rather than a `Backbone` because RF-DETR carries its own DINOv2 at
    `model.backbone.backbone`, with the same `encoder.layer` shape. One addressing rule for
    both is what stops the head path and the fine-tune path disagreeing about what "the
    last four blocks" means.

    Looked up rather than assumed, so a differently shaped backbone fails here, loudly,
    instead of at the first backward pass.
    """
    encoder = getattr(module, "encoder", None)
    layers = getattr(encoder, "layer", None) if encoder is not None else None
    if not isinstance(layers, nn.ModuleList) or len(layers) == 0:
        raise BackboneNotUnfreezableError(
            f"{type(module).__name__} has no addressable transformer blocks; "
            "this backbone can only be trained frozen."
        )
    return layers


def blocks_of(backbone: Backbone) -> nn.ModuleList:
    """The blocks of a catalogue backbone."""
    return blocks_in(backbone.model)


def apply_unfreeze(backbone: Backbone, unfreeze_blocks: int) -> tuple[int, int]:
    """Set `requires_grad` across the backbone. Returns `(frozen, trainable)` counts.

    **Returned, not merely logged**, for the reason doc 44 gives: "did it actually unfreeze?"
    is the question the whole feature rests on, and a silent no-op looks exactly like a slow
    success. The API reports both numbers and the panel shows them.

    `unfreeze_blocks` of 0 leaves everything frozen, which is the default and the path that
    still uses the feature cache.
    """
    for parameter in backbone.model.parameters():
        parameter.requires_grad_(False)

    if unfreeze_blocks != 0:
        layers = blocks_in(backbone.model)
        count = len(layers) if unfreeze_blocks == ALL_BLOCKS else min(unfreeze_blocks, len(layers))
        if unfreeze_blocks == ALL_BLOCKS:
            # The embeddings and the final layernorm are outside `encoder.layer`, so "all"
            # has to say so explicitly or it would quietly mean "all the blocks".
            for parameter in backbone.model.parameters():
                parameter.requires_grad_(True)
        else:
            for layer in layers[-count:]:
                for parameter in layer.parameters():
                    parameter.requires_grad_(True)
        logger.info("Unfroze %d of %d backbone block(s)", count, len(layers))

    trainable = sum(int(p.numel()) for p in backbone.model.parameters() if bool(p.requires_grad))
    frozen = sum(int(p.numel()) for p in backbone.model.parameters()) - trainable
    return frozen, trainable


def optimiser_for(
    head: nn.Module,
    backbone: Backbone,
    learning_rate: float,
    weight_decay: float,
    backbone_lr_scale: float = DEFAULT_BACKBONE_LR_SCALE,
) -> torch.optim.Optimizer:
    """AdamW over the head, plus whatever of the backbone is trainable, at a lower rate.

    Two param groups rather than one, because the head is being fitted from scratch and the
    backbone is being nudged. One shared rate is the setting that makes unfreezing look like
    a bad idea: at 1e-3 a pretrained ViT is destroyed by the first few hundred images, and
    the run reports a worse number than the frozen one it was meant to beat.

    A backbone with nothing trainable contributes no group at all — an empty param group
    makes AdamW raise, and the caller may legitimately be on the frozen path.
    """
    groups: list[dict[str, object]] = [{"params": list(head.parameters()), "lr": learning_rate}]
    unfrozen = [p for p in backbone.model.parameters() if bool(p.requires_grad)]
    if unfrozen:
        groups.append({"params": unfrozen, "lr": learning_rate * backbone_lr_scale})
    return torch.optim.AdamW(groups, lr=learning_rate, weight_decay=weight_decay)


def caching_is_valid(unfreeze_blocks: int) -> bool:
    """Whether the feature cache may be used.

    **The single most important line in this module.** A cached run holds features computed
    once, before training; if the backbone is also being trained, those features are stale
    from epoch two onwards *and the backbone is not in the graph at all*, so its parameters
    receive no gradients. The run completes, reports plausible losses, and has trained
    exactly the head — while telling the user it unfroze six million parameters.
    """
    return unfreeze_blocks == 0


def unfreeze_last_blocks(module: nn.Module, unfreeze_blocks: int) -> int:
    """Mark the last `unfreeze_blocks` blocks of `module` trainable. Returns how many.

    The half of `apply_unfreeze` that does not need a `Backbone`, so the fine-tune path —
    whose backbone is nested inside a detector — can reuse the same rule.
    """
    if unfreeze_blocks == 0:
        return 0
    layers = blocks_in(module)
    if unfreeze_blocks == ALL_BLOCKS:
        for parameter in module.parameters():
            parameter.requires_grad_(True)
        return len(layers)
    count = min(unfreeze_blocks, len(layers))
    for layer in layers[-count:]:
        for parameter in layer.parameters():
            parameter.requires_grad_(True)
    return count


__all__ = [
    "ALL_BLOCKS",
    "DEFAULT_BACKBONE_LR_SCALE",
    "BackboneNotUnfreezableError",
    "apply_unfreeze",
    "blocks_in",
    "blocks_of",
    "caching_is_valid",
    "optimiser_for",
    "unfreeze_last_blocks",
]
