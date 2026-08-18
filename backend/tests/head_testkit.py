"""Shared builders for the head catalogue and import tests.

The ``upstream_*`` functions reproduce the **exact** key names and tensor shapes of
DINOv2's published checkpoints, read from the real files during doc 15's research. They
live here rather than in one test module so the conversion tests and the install tests
cannot drift into asserting against two different ideas of the upstream layout.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch

from app.core.config import Settings
from app.ml.heads.pretrained import ADE20K_CLASSES, DEPTH_BINS, IMAGENET_CLASSES


def install_fake_backbone(settings: Settings, model_id: str, embed_dim: int) -> Path:
    """Write just enough of a model directory for ``read_capabilities`` to succeed.

    ``is_installed`` requires a real weight file, not merely a config — writing only
    config.json reproduces the Wave 1 bug where a mid-download model reported installed.
    """
    from app.core.paths import resolve_model_dir

    directory = resolve_model_dir(model_id, settings)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "config.json").write_text(
        json.dumps(
            {
                "patch_size": 14,
                "hidden_size": embed_dim,
                "num_hidden_layers": 12,
                "image_size": 518,
            }
        )
    )
    (directory / "model.safetensors").write_bytes(b"\x00")
    return directory


def upstream_classifier(embed_dim: int) -> dict[str, torch.Tensor]:
    """Keys and shapes of ``dinov2_<m>_linear_head.pth``."""
    return {
        "weight": torch.randn(IMAGENET_CLASSES, embed_dim * 2),
        "bias": torch.randn(IMAGENET_CLASSES),
    }


def upstream_segmenter(embed_dim: int) -> dict[str, torch.Tensor]:
    """Keys and shapes of ``dinov2_<m>_ade20k_linear_head.pth``."""
    return {
        "decode_head.conv_seg.weight": torch.randn(ADE20K_CLASSES, embed_dim, 1, 1),
        "decode_head.conv_seg.bias": torch.randn(ADE20K_CLASSES),
        "decode_head.bn.weight": torch.randn(embed_dim),
        "decode_head.bn.bias": torch.randn(embed_dim),
        "decode_head.bn.running_mean": torch.randn(embed_dim),
        "decode_head.bn.running_var": torch.rand(embed_dim) + 1.0,
        "decode_head.bn.num_batches_tracked": torch.tensor(0),
    }


def upstream_depth(embed_dim: int) -> dict[str, torch.Tensor]:
    """Keys and shapes of ``dinov2_<m>_nyu_linear_head.pth``."""
    return {
        "decode_head.conv_depth.weight": torch.randn(DEPTH_BINS, embed_dim * 2, 1, 1),
        "decode_head.conv_depth.bias": torch.randn(DEPTH_BINS),
    }
