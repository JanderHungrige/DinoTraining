"""Tests for how a decoder's output is shaped for the renderer.

The dense maps travel as base64 PNG rather than nested JSON lists. That is a transport
change with a measured reason — 18.5 MB against 17 KB for a 3000x2000 segmentation — so
the tests assert the *decoded* map, not the encoding, and one of them asserts the size
win directly so a regression to lists cannot pass quietly.
"""

from __future__ import annotations

import base64
import io
import json

import numpy as np
import pytest
import torch
from PIL import Image

from app.ml.heads.registry import get_head_type
from app.ml.inference.payloads import (
    MAX_PNG_CLASSES,
    depth_payload,
    encode_png,
    masks_payload,
    to_numpy,
)
from app.ml.preprocess import GeometryTransform


def identity_transform(size: int) -> GeometryTransform:
    """No letterbox, no scaling — the map comes back exactly as it went in."""
    return GeometryTransform(
        scale=1.0, pad_x=0.0, pad_y=0.0, out_w=size, out_h=size, source_size=(size, size)
    )


def decode(encoded: object) -> np.ndarray:
    assert isinstance(encoded, str)
    return np.array(Image.open(io.BytesIO(base64.b64decode(encoded))))


def logits_for(classes: int, size: int, winner: int) -> dict[str, torch.Tensor]:
    logits = torch.zeros(1, classes, size, size)
    logits[0, winner] = 10.0
    return {"logits": logits}


class TestToNumpy:
    """Regression tests for a bug the CPU-only suite could not see.

    On this machine the backbone runs on MPS, so the decoded map is an MPS tensor and
    `.numpy()` raises. Every unit test builds tensors on the CPU, so the whole suite
    passed while the real endpoint 500'd. The MPS case cannot be asserted portably —
    but "not a plain CPU leaf" can, via `requires_grad`, and it fails in exactly the
    same place for the same reason.
    """

    def test_a_graph_attached_tensor_converts(self) -> None:
        attached = torch.zeros(4, 4, requires_grad=True) + 1.0

        assert to_numpy(attached).shape == (4, 4)

    def test_masks_payload_accepts_a_graph_attached_map(self) -> None:
        logits = torch.zeros(1, 3, 16, 16, requires_grad=True) + 1.0

        payload = masks_payload({"logits": logits}, identity_transform(16), 16)

        assert decode(payload["mask_png"]).shape == (16, 16)

    def test_depth_payload_accepts_a_graph_attached_map(self) -> None:
        depth = torch.rand(1, 1, 16, 16, requires_grad=True) + 1.0

        payload = depth_payload({"depth": depth}, identity_transform(16), 16)

        assert decode(payload["depth_png"]).shape == (16, 16)

    @pytest.mark.skipif(
        not torch.backends.mps.is_available(), reason="MPS only exists on Apple silicon"
    )
    def test_an_mps_tensor_converts(self) -> None:
        """The actual bug, on the machine where it actually happened."""
        assert to_numpy(torch.zeros(4, 4, device="mps")).shape == (4, 4)


class TestEncodePng:
    def test_round_trips_the_exact_values(self) -> None:
        array = np.array([[0, 1, 200], [255, 7, 42]], dtype=np.uint8)

        assert np.array_equal(decode(encode_png(array)), array)

    def test_is_dramatically_smaller_than_a_json_list(self) -> None:
        """The reason this transport exists. A regression to lists must not pass."""
        # A realistic map: large flat regions, upsampled from a coarse patch grid.
        array = np.zeros((2000, 3000), dtype=np.uint8)
        array[400:1600, 900:2400] = 12

        as_png = len(encode_png(array))
        as_json = len(json.dumps(array.tolist()))

        assert as_json / as_png > 100, f"{as_json} vs {as_png}"


class TestMasksPayload:
    def test_carries_a_png_and_not_a_nested_list(self) -> None:
        payload = masks_payload(logits_for(4, 32, winner=2), identity_transform(32), 32)

        assert "mask_png" in payload
        assert "mask" not in payload, "the nested-list transport is gone on purpose"

    def test_pixel_values_are_class_indices_times_the_stride(self) -> None:
        """No palette in the payload — the client owns colour, once it divides.

        The stride exists because adjacent class indices are terrible pixel values: a
        webview that colour-manages the PNG on the way in dithers the low bits, and with
        classes 0 and 1 that turns background into the other class. `present_classes` stays
        in *index* space, because that is what the number means.
        """
        payload = masks_payload(logits_for(4, 32, winner=3), identity_transform(32), 32)

        stride = int(payload["class_stride"])  # type: ignore[arg-type]
        decoded = decode(payload["mask_png"])
        assert set(np.unique(decoded).tolist()) == {3 * stride}
        assert payload["present_classes"] == [3]

    def test_a_two_class_map_puts_its_classes_at_opposite_ends_of_the_byte(self) -> None:
        """The case that was actually broken. One phrase means classes 0 and 1, and one
        level of dither is the whole difference between background and the object."""
        logits = torch.zeros(1, 2, 8, 8)
        logits[0, 1, :4] = 10.0
        logits[0, 0, 4:] = 10.0

        payload = masks_payload({"logits": logits}, identity_transform(8), 8)

        assert payload["class_stride"] == 255
        assert set(np.unique(decode(payload["mask_png"])).tolist()) == {0, 255}

    def test_a_full_byte_of_classes_falls_back_to_plain_indices(self) -> None:
        """ADE20k's 150 classes leave no room to spread, and need none: its class 0 is
        `wall`, a real class that gets painted anyway."""
        logits = torch.zeros(1, 200, 8, 8)
        logits[0, 199] = 10.0

        payload = masks_payload({"logits": logits}, identity_transform(8), 8)

        assert payload["class_stride"] == 1
        assert set(np.unique(decode(payload["mask_png"])).tolist()) == {199}

    def test_the_map_is_at_source_resolution(self) -> None:
        payload = masks_payload(logits_for(4, 64, winner=1), identity_transform(64), 64)

        assert decode(payload["mask_png"]).shape == (64, 64)
        assert payload["height"] == 64
        assert payload["width"] == 64

    def test_a_class_index_beyond_a_byte_is_refused(self) -> None:
        """Silently wrapping class 300 round to 44 would be a wrong answer, not an error."""
        logits = torch.zeros(1, 300, 16, 16)
        logits[0, 299] = 10.0

        with pytest.raises(ValueError, match=str(MAX_PNG_CLASSES)):
            masks_payload({"logits": logits}, identity_transform(16), 16)


class TestDepthPayload:
    def test_carries_a_png_plus_the_range_to_read_it_back(self) -> None:
        depth = torch.rand(1, 1, 16, 16) * 4.0 + 1.0
        payload = depth_payload({"depth": depth}, identity_transform(16), 16)

        assert "depth_png" in payload
        assert "depth" not in payload
        assert payload["min"] < payload["max"]

    def test_the_extremes_map_to_the_ends_of_the_range(self) -> None:
        depth = torch.zeros(1, 1, 8, 8)
        depth[0, 0, 0, 0] = 1.0
        depth[0, 0, 7, 7] = 9.0
        payload = depth_payload({"depth": depth}, identity_transform(8), 8)

        decoded = decode(payload["depth_png"])
        assert decoded.min() == 0
        assert decoded.max() == 255
        assert payload["min"] == pytest.approx(0.0)
        assert payload["max"] == pytest.approx(9.0)

    def test_a_flat_depth_map_does_not_divide_by_zero(self) -> None:
        """A constant scene is degenerate but real — an all-sky frame, or a stub head."""
        depth = torch.full((1, 1, 8, 8), 3.0)

        payload = depth_payload({"depth": depth}, identity_transform(8), 8)

        assert payload["min"] == payload["max"] == pytest.approx(3.0)
        assert decode(payload["depth_png"]).max() == 0

    def test_a_pixel_can_be_read_back_to_metres(self) -> None:
        """`min`/`max` are carried precisely so the 0..255 encoding is invertible."""
        depth = torch.linspace(2.0, 10.0, 64).reshape(1, 1, 8, 8)
        payload = depth_payload({"depth": depth}, identity_transform(8), 8)

        decoded = decode(payload["depth_png"]).astype(float)
        low, high = float(payload["min"]), float(payload["max"])
        recovered = low + decoded / 255.0 * (high - low)

        assert recovered.min() == pytest.approx(2.0, abs=0.05)
        assert recovered.max() == pytest.approx(10.0, abs=0.05)


class TestRegistryDispatch:
    def test_every_registered_head_type_has_a_payload_shape(self) -> None:
        """Adding a head type later must not leave build_payload with nothing to do."""
        from app.ml.heads.registry import all_head_types

        hints = {spec.render_hint for spec in all_head_types()}
        assert hints == {"labels", "boxes", "masks", "depth-map"}

    def test_the_segmenter_spec_still_asks_for_masks(self) -> None:
        spec = get_head_type("linear-segmenter")
        assert spec is not None and spec.render_hint == "masks"
