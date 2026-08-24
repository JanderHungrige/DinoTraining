"""The three pretrained default head modules, mirroring DINOv2's published heads.

These exist because the upstream checkpoints do **not** fit the modules in
:mod:`app.ml.heads.modules`: the classifier is twice as wide and pools the patch grid,
the segmenter carries a BatchNorm, and the depth head predicts bins rather than a
scalar. Loading those weights into the built-in modules would succeed and emit
garbage, so each gets a module shaped like the checkpoint it receives.

Adding them touches this file, the registry table and the builder table — and no
training or inference code at all. That is the head-type contract from doc 08 doing
its job.

Attribute names are load-bearing: :mod:`app.ml.heads.convert` remaps upstream keys
onto exactly these names, and the state dict is then loaded ``strict=True``.
"""

from __future__ import annotations

import torch
from torch import Tensor, nn

from app.ml.backbone import BackboneFeatures

#: ImageNet-1k, the label set DINOv2's linear classification heads were trained on.
IMAGENET_CLASSES = 1000

#: ADE20k semantic classes, for the segmentation heads.
ADE20K_CLASSES = 150

#: Bin count used by DINOv2's depth heads (``n_bins=256``).
DEPTH_BINS = 256

#: NYUd depth range in metres, from ``dinov2/hub/depthers.py::_get_depth_range``.
#:
#: Note the upstream inconsistency: ``_make_dinov2_linear_depth_head`` hardcodes
#: ``max_depth=80`` (the KITTI range) while ``_get_depth_range`` returns 10.0 for NYU
#: weights. 10.0 is correct for the checkpoints this app pins.
NYU_DEPTH_RANGE: tuple[float, float] = (0.001, 10.0)


class PretrainedClassifier(nn.Module):
    """DINOv2's linear ImageNet head: ``Linear(2*D -> 1000)``.

    The input is ``cat([cls, mean(patches)])`` with **CLS first** — see
    ``create_linear_input`` in ``dinov2/eval/linear.py``. The depth head below uses the
    opposite order, so neither ordering may be assumed from the other.
    """

    def __init__(self, embed_dim: int, num_classes: int = IMAGENET_CLASSES) -> None:
        super().__init__()
        self.linear = nn.Linear(embed_dim * 2, num_classes)

    def forward(self, features: BackboneFeatures) -> dict[str, Tensor]:
        # Mean over the spatial grid, matching torch.mean(patch_tokens, dim=1) upstream
        # where the tokens are still (B, N, D).
        pooled = features.patches.mean(dim=(2, 3))
        return {"logits": self.linear(torch.cat([features.cls, pooled], dim=-1))}


class PretrainedSegmenter(nn.Module):
    """DINOv2's ADE20k linear head: ``BatchNorm2d(D)`` then ``Conv2d(D -> 150, 1x1)``.

    Concatenates nothing — upstream asserts ``in_channels == channels``, so the CLS
    token is not part of this head's input at all.

    Output stays at patch resolution; callers upsample with
    :func:`app.ml.heads.modules.upsample_logits`, which needs a target size this module
    never sees.
    """

    def __init__(self, embed_dim: int, num_classes: int = ADE20K_CLASSES) -> None:
        super().__init__()
        # SyncBatchNorm upstream; BatchNorm2d is the single-process equivalent and
        # loads the same four buffers. The head only ever runs in eval mode here, so
        # the running statistics from the checkpoint are what matter.
        self.bn = nn.BatchNorm2d(embed_dim)
        self.conv_seg = nn.Conv2d(embed_dim, num_classes, kernel_size=1)

    def forward(self, features: BackboneFeatures) -> dict[str, Tensor]:
        return {"logits": self.conv_seg(self.bn(features.patches))}


class PretrainedDepth(nn.Module):
    """DINOv2's NYUd linear depth head: bin logits decoded to metres.

    Two details are easy to get wrong and both are verified by tests:

    * the input is ``cat([patches, cls.expand], dim=1)`` — **patches first**, the
      opposite of :class:`PretrainedClassifier`;
    * the output is not a depth, it is 256 bin weights that must be normalised and
      dotted with the bin centres (``DepthBaseDecodeHead.depth_pred``).

    Upstream resizes the features 4x *before* this 1x1 convolution. A 1x1 convolution
    is pointwise-linear and bilinear resize is linear, so the two commute; convolving
    first is identical and resizes 256 channels instead of ``2*D``.
    """

    #: Declared for the type checker: nn.Module.__getattr__ widens buffers to
    #: ``Tensor | Module``, which loses the type at every use site.
    bins: Tensor

    def __init__(
        self,
        embed_dim: int,
        n_bins: int = DEPTH_BINS,
        min_depth: float = NYU_DEPTH_RANGE[0],
        max_depth: float = NYU_DEPTH_RANGE[1],
    ) -> None:
        super().__init__()
        self.n_bins = n_bins
        self.min_depth = min_depth
        self.max_depth = max_depth
        self.conv_depth = nn.Conv2d(embed_dim * 2, n_bins, kernel_size=1)
        # A buffer so it follows the module across devices; recomputing linspace on
        # every forward would put it on the CPU during a GPU run.
        #
        # persistent=False keeps it out of state_dict(). The bin centres are derived
        # from (min_depth, max_depth, n_bins), not learned — and if they were
        # persistent, strict=True loading of a converted checkpoint would fail on a
        # missing "bins" key, since upstream ships only conv_depth.*.
        self.register_buffer(
            "bins", torch.linspace(min_depth, max_depth, n_bins), persistent=False
        )

    def forward(self, features: BackboneFeatures) -> dict[str, Tensor]:
        patches = features.patches
        # CLS is broadcast across every spatial position, then concatenated on the
        # channel axis — BNHead._forward_feature does exactly this.
        cls = features.cls[:, :, None, None].expand_as(patches)
        logits = self.conv_depth(torch.cat([patches, cls], dim=1))
        return {"depth": self._decode(logits)}

    def _decode(self, logits: Tensor) -> Tensor:
        """Bin logits to metres, following ``norm_strategy="linear"`` upstream.

        The ``+ eps`` after the ReLU is not cosmetic: without it an all-negative
        prediction normalises 0/0 to NaN.
        """
        weights = torch.relu(logits) + 0.1
        weights = weights / weights.sum(dim=1, keepdim=True)
        depth = torch.einsum("bkhw,k->bhw", weights, self.bins)
        return depth.unsqueeze(1)
