"""The exported runtime is the app's own code (doc 121): same inputs, same answers.

If a change to inference is not reflected in the generated `dino_runtime.py`, an exported
model would give different answers from the app — confidently. These tests fail first.
"""

from __future__ import annotations

import types
from typing import Any

import numpy as np
import pytest
import torch
from PIL import Image

from app.ml.backbone import BackboneCapabilities, BackboneFeatures, _split_tokens
from app.ml.heads.builders import build_head
from app.ml.heads.decode import DECODERS
from app.ml.heads.registry import get_head_type
from app.ml.inference.payloads import build_payload
from app.ml.preprocess import PreprocessPlan, apply_geometry, to_pixel_values
from app.mlops.runtime_source import SUPPORTED, runtime_source

CAPS = BackboneCapabilities("dinov2-small", "dinov2", 14, 32, 1, 12, 518)


@pytest.fixture(scope="module")
def runtime() -> types.ModuleType:
    import sys

    # Registered like an imported file would be: dataclasses resolve annotations through it.
    module = types.ModuleType("dino_runtime")
    sys.modules["dino_runtime"] = module
    exec(compile(runtime_source(), "dino_runtime.py", "exec"), module.__dict__)  # noqa: S102
    return module


def _picture() -> Image.Image:
    rng = np.random.default_rng(0)
    return Image.fromarray(rng.integers(0, 255, (90, 130, 3), dtype=np.uint8))


@pytest.mark.parametrize("geometry", ["aspect-preserve", "center-crop"])
def test_preprocessing_is_identical(runtime: types.ModuleType, geometry: str) -> None:
    mean, std = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
    ours = PreprocessPlan(size=112, geometry=geometry, patch_size=14, mean=mean, std=std)  # type: ignore[arg-type]
    theirs = runtime.PreprocessPlan(size=112, geometry=geometry, patch_size=14, mean=mean, std=std)
    a, ta = apply_geometry(ours, _picture())
    b, tb = runtime.apply_geometry(theirs, _picture())
    assert torch.equal(to_pixel_values(ours, [a]), runtime.to_pixel_values(theirs, [b]))
    assert (ta.scale, ta.pad_x, ta.pad_y) == (tb.scale, tb.pad_x, tb.pad_y)


def test_token_split_is_identical(runtime: types.ModuleType) -> None:
    hidden = torch.randn(1, 1 + 8 * 8, 32)
    for mine, theirs in zip(
        _split_tokens(hidden, 1, (8, 8)), runtime._split_tokens(hidden, 1, (8, 8)), strict=True
    ):
        assert torch.equal(mine, theirs)


def _features() -> BackboneFeatures:
    torch.manual_seed(0)
    return BackboneFeatures(cls=torch.randn(1, 32), patches=torch.randn(1, 32, 8, 8), grid=(8, 8))


@pytest.mark.parametrize("head_type", sorted(SUPPORTED))
def test_head_decode_and_payload_are_identical(runtime: types.ModuleType, head_type: str) -> None:
    spec = get_head_type(head_type)
    assert spec is not None
    classes = None if head_type == "linear-depth" else 3
    app_head = build_head(head_type, CAPS, classes).eval()
    builder, decoder = runtime.HEADS[head_type]
    rt_head = builder(types.SimpleNamespace(embed_dim=32, patch_size=14), classes).eval()
    rt_head.load_state_dict(app_head.state_dict())
    features = _features()
    rt_features = runtime.BackboneFeatures(
        cls=features.cls, patches=features.patches, grid=features.grid
    )
    with torch.no_grad():
        mine, theirs = app_head(features), rt_head(rt_features)
    for key in mine:
        assert torch.allclose(mine[key], theirs[key]), key
    plan = PreprocessPlan(112, spec.geometry, 14, (0.5,) * 3, (0.5,) * 3)
    _, transform = apply_geometry(plan, _picture())
    rt_plan = runtime.PreprocessPlan(112, spec.geometry, 14, (0.5,) * 3, (0.5,) * 3)
    _, rt_transform = runtime.apply_geometry(rt_plan, _picture())
    ours: dict[str, Any] = build_payload(spec, DECODERS[head_type](mine, 14), transform, 112, 0.0)
    rt_spec = types.SimpleNamespace(id=head_type, render_hint=spec.render_hint)
    assert runtime.build_payload(rt_spec, decoder(theirs, 14), rt_transform, 112, 0.0) == ours


def test_every_trainable_head_type_is_covered() -> None:
    from app.ml.heads.registry import HEAD_TYPES

    trainable = {spec.id for spec in HEAD_TYPES.values() if spec.trainable}
    assert trainable <= set(SUPPORTED)
